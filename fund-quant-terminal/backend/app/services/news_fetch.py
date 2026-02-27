# =====================================================
# 新闻抓取服务
# 使用 feedparser 获取东方财富、新浪财经等 RSS，写入 news_raw
# =====================================================

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import feedparser

from app.config import settings
from app.utils.logger import logger

NEWS_COLLECTION = "news_raw"

# 东方财富、新浪等来源标识
SOURCE_EASTMONEY = "eastmoney"
SOURCE_SINA = "sina"


def _parse_pub_date(entry: Dict[str, Any]) -> Optional[datetime]:
    """解析 RSS 条目的发布时间"""
    for key in ("published_parsed", "updated_parsed"):
        val = entry.get(key)
        if val:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(val))
            except (TypeError, ValueError, OverflowError):
                pass
    published = entry.get("published") or entry.get("updated")
    if published:
        s = str(published).strip()
        for fmt, max_len in (
            ("%a, %d %b %Y %H:%M:%S", 24),
            ("%Y-%m-%dT%H:%M:%S", 19),
            ("%Y-%m-%d %H:%M:%S", 19),
        ):
            try:
                return datetime.strptime(s[:max_len], fmt)
            except ValueError:
                continue
    return None


def _extract_summary(entry: Dict[str, Any]) -> str:
    """提取摘要"""
    summary = entry.get("summary") or entry.get("description") or ""
    if hasattr(summary, "value"):
        summary = summary.value if summary else ""
    return (str(summary) or "")[:500]


def _extract_link(entry: Dict[str, Any]) -> str:
    """提取链接"""
    link = entry.get("link") or ""
    if hasattr(link, "strip"):
        return str(link).strip()
    return str(link)


def _extract_title(entry: Dict[str, Any]) -> str:
    """提取标题"""
    title = entry.get("title") or ""
    return (str(title) or "").strip()


def _infer_source(url: str, feed_title: str) -> str:
    """根据 URL 或 feed 标题推断来源"""
    url_lower = (url or "").lower()
    title_lower = (feed_title or "").lower()
    if "eastmoney" in url_lower or "东方财富" in title_lower or "eastmoney" in title_lower:
        return SOURCE_EASTMONEY
    if "sina" in url_lower or "新浪" in title_lower or "sina" in title_lower:
        return SOURCE_SINA
    return "rss"


async def _fetch_feed_sync(url: str) -> Dict[str, Any]:
    """同步 fetch RSS（在线程池中执行，避免阻塞）"""
    def _fetch():
        try:
            return feedparser.parse(url)
        except Exception as e:
            logger.warning("feedparser parse 失败 %s: %s", url, e)
            return {}

    return await asyncio.to_thread(_fetch)


class NewsFetchService:
    """新闻 RSS 抓取服务"""

    def __init__(self) -> None:
        self._feed_urls = [
            u.strip() for u in (settings.NEWS_FEED_URLS or "").split(",") if u.strip()
        ]

    def _get_feed_urls(self, fund_code: Optional[str] = None) -> List[str]:
        """获取要抓取的 feed URL 列表，支持 {fund_code} 占位符"""
        urls = []
        for u in self._feed_urls:
            if "{fund_code}" in u and fund_code:
                urls.append(u.replace("{fund_code}", fund_code.strip()))
            elif "{fund_code}" not in u:
                urls.append(u)
        return urls if urls else self._feed_urls

    async def fetch_and_save(
        self,
        db,
        fund_code: Optional[str] = None,
        days: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        抓取 RSS 并保存到 news_raw
        fund_code: 可选，筛选或标记的基金代码
        days: 仅保留最近 N 天的新闻（按 pub_date 过滤）
        """
        urls = self._get_feed_urls(fund_code)
        if not urls:
            logger.warning("未配置 NEWS_FEED_URLS，跳过抓取")
            return []

        cutoff = datetime.utcnow() - timedelta(days=max(1, days))
        all_news: List[Dict[str, Any]] = []

        for url in urls:
            try:
                feed = await _fetch_feed_sync(url)
                if not feed or "entries" not in feed:
                    continue

                feed_title = feed.get("feed", {}).get("title", "") or url
                source = _infer_source(url, feed_title)

                for entry in feed.get("entries", []):
                    pub_dt = _parse_pub_date(entry)
                    if pub_dt and pub_dt.replace(tzinfo=None) < cutoff:
                        continue

                    title = _extract_title(entry)
                    link = _extract_link(entry)
                    if not title and not link:
                        continue

                    doc = {
                        "title": title,
                        "link": link,
                        "pub_date": pub_dt,
                        "source": source,
                        "content_summary": _extract_summary(entry),
                        "fund_code": (fund_code or "").strip() or None,
                        "created_at": datetime.utcnow(),
                    }

                    all_news.append(doc)

                    try:
                        await db[NEWS_COLLECTION].update_one(
                            {"link": link},
                            {"$set": doc},
                            upsert=True,
                        )
                    except Exception as e:
                        logger.debug("news_raw insert 跳过 %s: %s", link[:80], e)

            except Exception as e:
                logger.warning("抓取 RSS 失败 %s: %s", url, e)

        return all_news

    async def get_news(
        self,
        db,
        fund_code: Optional[str] = None,
        days: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        从 news_raw 查询新闻，按时间倒序
        若 fund_code 为空则返回通用财经新闻
        """
        cutoff = datetime.utcnow() - timedelta(days=max(1, days))
        query: Dict[str, Any] = {"pub_date": {"$gte": cutoff}}

        if fund_code and fund_code.strip():
            fc = fund_code.strip()
            query["$or"] = [
                {"fund_code": fc},
                {"fund_code": {"$in": [None, ""]}},
                {"fund_code": {"$exists": False}},
            ]

        cursor = db[NEWS_COLLECTION].find(query).sort("pub_date", -1).limit(500)
        docs = await cursor.to_list(length=500)

        out = []
        for d in docs:
            d.pop("_id", None)
            if d.get("pub_date"):
                d["pub_date"] = d["pub_date"].isoformat()
            if d.get("created_at"):
                d["created_at"] = d["created_at"].isoformat()
            out.append(d)
        return out
