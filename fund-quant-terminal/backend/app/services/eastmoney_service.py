# =====================================================
# 东方财富 7*24 全球直播服务
# 支持鬼鬼API（国内可用）和 RSSHub（需代理），输出统一格式
# =====================================================

from datetime import datetime
from typing import Any, Dict, List

import feedparser
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import llm_settings, settings
from app.utils.logger import logger

# 情绪分析关键词（与 wallstreetcn_service 一致）
POSITIVE_KEYWORDS = ["利好", "上涨", "买入", "大涨", "看涨", "反弹", "增长", "突破", "增持", "推荐"]
NEGATIVE_KEYWORDS = ["利空", "下跌", "卖出", "大跌", "看跌", "回落", "跌破", "亏损", "减持", "预警"]
DECISION_LOGS_COLLECTION = "decision_logs"
SOURCE_EASTMONEY = "eastmoney"
# 鬼鬼API type=102 为 7*24小时全球直播
GUIGUI_TYPE_7X24 = 102


def _compute_sentiment(text: str) -> float:
    """基于正负向关键词计算情绪得分，范围 -1 ~ 1"""
    if not text or not isinstance(text, str):
        return 0.0
    t = text.strip()
    pos = sum(1 for k in POSITIVE_KEYWORDS if k in t)
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k in t)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / max(total, 1), 2)


def _parse_rss_entry(entry: Any) -> Dict[str, Any]:
    """解析 feedparser 单条为统一格式：title, published_time, summary, url, sentiment"""
    title = str(entry.get("title") or "").strip()
    summary = ""
    if hasattr(entry, "summary"):
        summary = str(entry.summary or "").strip()
    elif hasattr(entry, "description"):
        summary = str(entry.description or "").strip()
    summary = summary[:500] if summary else ""
    display_title = title or (summary[:80] + "..." if len(summary) > 80 else summary) or "(无标题)"
    url = str(entry.get("link") or "").strip()

    published_time = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            from time import struct_time
            st: struct_time = entry.published_parsed
            published_time = datetime(st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour, st.tm_min, st.tm_sec)
        except (TypeError, ValueError):
            pass
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            from time import struct_time
            st = entry.updated_parsed
            published_time = datetime(st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour, st.tm_min, st.tm_sec)
        except (TypeError, ValueError):
            pass

    text_for_sentiment = f"{title} {summary}"
    sentiment = _compute_sentiment(text_for_sentiment)

    return {
        "title": display_title,
        "published_time": published_time.isoformat() if published_time else None,
        "summary": summary,
        "url": url or None,
        "sentiment": sentiment,
    }


def _parse_guigui_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """解析鬼鬼API单条为统一格式。time 为北京时间 YYYY-MM-DD HH:mm:ss"""
    title = str(item.get("title") or "").strip()
    content = str(item.get("content") or "").strip()[:500]
    url = str(item.get("url") or "").strip()
    time_str = str(item.get("time") or "").strip()
    # 将时间转为 ISO 格式（北京时区），便于前端解析
    published_time = None
    if time_str:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(time_str[:19], fmt[: len(time_str[:19])] if len(time_str) < 19 else fmt)
                published_time = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                break
            except (ValueError, TypeError):
                continue
        if published_time is None:
            published_time = time_str
    text_for_sentiment = f"{title} {content}"
    sentiment = _compute_sentiment(text_for_sentiment)
    return {
        "title": title or "(无标题)",
        "published_time": published_time,
        "summary": content,
        "url": url or None,
        "sentiment": sentiment,
    }


class EastMoneyService:
    """东方财富 7*24 全球直播服务：支持鬼鬼API / RSSHub，解析、可选保存"""

    async def _fetch_guigui(self, limit: int) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """从鬼鬼API拉取 7*24 直播"""
        url = f"{settings.EASTMONEY_GUIGUI_URL}?type={GUIGUI_TYPE_7X24}&limit={min(limit, 50)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        if not data.get("success") or "data" not in data:
            raise ValueError(data.get("msg", "鬼鬼API 返回异常"))
        items = data.get("data") or []
        parsed: List[Dict[str, Any]] = []
        for i, it in enumerate(items):
            if i >= limit:
                break
            try:
                parsed.append(_parse_guigui_item(it))
            except Exception as e:
                logger.debug("eastmoney_service 解析鬼鬼单条失败: %s", e)
                continue
        raw = {
            "source": "guigui",
            "feed": {"title": "东方财富 7*24 全球直播", "link": settings.EASTMONEY_GUIGUI_URL},
            "entries_count": len(items),
            "update_time": data.get("update_time"),
        }
        return raw, parsed

    async def _fetch_rsshub(self, limit: int) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """从 RSSHub 拉取东方财富 7*24 直播"""
        rss_url = settings.EASTMONEY_RSS_URL
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        proxies = None
        if llm_settings.HTTP_PROXY or llm_settings.HTTPS_PROXY:
            proxies = (llm_settings.HTTPS_PROXY or llm_settings.HTTP_PROXY) or None
        async with httpx.AsyncClient(timeout=30.0, headers=headers, proxy=proxies) as client:
            resp = await client.get(rss_url)
            resp.raise_for_status()
            content = resp.text
        feed = feedparser.parse(content)
        entries = getattr(feed, "entries", []) or []
        parsed: List[Dict[str, Any]] = []
        for i, entry in enumerate(entries):
            if i >= limit:
                break
            try:
                parsed.append(_parse_rss_entry(entry))
            except Exception as e:
                logger.debug("eastmoney_service 解析 RSS 单条失败: %s", e)
                continue
        feed_meta = getattr(feed, "feed", None)
        raw = {
            "source": "rsshub",
            "feed": {
                "title": getattr(feed_meta, "title", "") if feed_meta else "",
                "link": getattr(feed_meta, "link", "") if feed_meta else "",
            },
            "entries_count": len(entries),
        }
        return raw, parsed

    async def fetch_and_parse(
        self,
        *,
        limit: int = 10,
    ) -> tuple[Any, List[Dict[str, Any]]]:
        """
        拉取东方财富 7*24 直播，解析为统一格式。
        默认使用鬼鬼API（国内可用），可配置 EASTMONEY_SOURCE=rsshub 使用 RSSHub。
        返回 (raw_feed_dict, parsed_items)。
        """
        source = (settings.EASTMONEY_SOURCE or "guigui").strip().lower()
        if source == "rsshub":
            try:
                return await self._fetch_rsshub(limit)
            except Exception as e:
                logger.warning("eastmoney_service RSSHub 拉取失败: %s，尝试鬼鬼API", e)
                return await self._fetch_guigui(limit)
        return await self._fetch_guigui(limit)

    async def save_to_decision_logs(
        self,
        db: AsyncIOMotorDatabase,
        items: List[Dict[str, Any]],
        type_: str = "live:7x24",
    ) -> int:
        """
        将解析后的条目保存至 decision_logs，source=eastmoney。
        返回成功写入条数。
        """
        if not items:
            return 0
        try:
            coll = db[DECISION_LOGS_COLLECTION]
            now = datetime.utcnow()
            count = 0
            for it in items:
                doc = {
                    "source": SOURCE_EASTMONEY,
                    "type": type_,
                    "title": it.get("title"),
                    "published_time": it.get("published_time"),
                    "summary": it.get("summary"),
                    "url": it.get("url"),
                    "sentiment": it.get("sentiment", 0),
                    "created_at": now,
                }
                await coll.insert_one(doc)
                count += 1
            logger.info("eastmoney_service 已保存 %d 条至 decision_logs", count)
            return count
        except Exception as e:
            logger.exception("eastmoney_service save_to_decision_logs 异常: %s", e)
            raise
