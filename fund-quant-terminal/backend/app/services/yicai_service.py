# =====================================================
# 第一财经快讯服务
# 使用第一财经官方 RSS，输出与 eastmoney/cailianshe 一致的统一格式
# 严禁使用备用新闻源，仅此单一接口
# =====================================================

from datetime import datetime
from typing import Any, Dict, List

import feedparser
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.utils.logger import logger

DECISION_LOGS_COLLECTION = "decision_logs"
SOURCE_YICAI = "yicai"

POSITIVE_KEYWORDS = ["利好", "上涨", "买入", "大涨", "看涨", "反弹", "增长", "突破", "增持", "推荐"]
NEGATIVE_KEYWORDS = ["利空", "下跌", "卖出", "大跌", "看跌", "回落", "跌破", "亏损", "减持", "预警"]


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
            published_time = datetime(
                st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour, st.tm_min, st.tm_sec
            )
        except (TypeError, ValueError):
            pass
    elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
        try:
            from time import struct_time

            st = entry.updated_parsed
            published_time = datetime(
                st.tm_year, st.tm_mon, st.tm_mday, st.tm_hour, st.tm_min, st.tm_sec
            )
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


class YicaiService:
    """第一财经快讯服务：从官方 RSS 拉取，输出统一格式"""

    def _get_rss_url(self) -> str:
        """获取第一财经快讯 RSS 地址"""
        return (settings.YICAI_RSS_URL or "https://www.yicai.com/feed/").strip().rstrip("/")

    async def fetch_and_parse(
        self,
        *,
        limit: int = 10,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        从第一财经官方 RSS 拉取快讯，解析为统一格式。
        返回 (raw_feed_dict, parsed_items)。
        """
        url = self._get_rss_url()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                content = resp.text
        except Exception as e:
            logger.warning("yicai_service 拉取 RSS 失败 %s: %s", url, e)
            raise

        feed = feedparser.parse(content)
        entries = getattr(feed, "entries", []) or []
        parsed: List[Dict[str, Any]] = []
        for i, entry in enumerate(entries):
            if i >= limit:
                break
            try:
                parsed.append(_parse_rss_entry(entry))
            except Exception as e:
                logger.debug("yicai_service 解析单条失败: %s", e)
                continue

        feed_meta = getattr(feed, "feed", None)
        raw = {
            "source": SOURCE_YICAI,
            "type": "kuaixun",
            "feed": {
                "title": getattr(feed_meta, "title", "") if feed_meta else "第一财经快讯",
                "link": getattr(feed_meta, "link", "") if feed_meta else "https://www.yicai.com/",
            },
            "entries_count": len(entries),
        }
        return raw, parsed

    async def save_to_decision_logs(
        self,
        db: AsyncIOMotorDatabase,
        items: List[Dict[str, Any]],
        type_: str = "kuaixun",
    ) -> int:
        """将解析后的条目保存至 decision_logs，source=yicai"""
        if not items:
            return 0
        try:
            coll = db[DECISION_LOGS_COLLECTION]
            now = datetime.utcnow()
            count = 0
            for it in items:
                doc = {
                    "source": SOURCE_YICAI,
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
            logger.info("yicai_service 已保存 %d 条至 decision_logs", count)
            return count
        except Exception as e:
            logger.exception("yicai_service save_to_decision_logs 异常: %s", e)
            raise
