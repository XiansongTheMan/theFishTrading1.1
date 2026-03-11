# =====================================================
# 新浪财经 RSS 服务
# 支持 8 个二级分类：国际、市场、其他、焦点、公司、宏观、两会、观点
# 使用新浪原生 RSS 地址（国内可用）
# =====================================================

from datetime import datetime
from typing import Any, Dict, List

import feedparser
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import llm_settings
from app.utils.logger import logger

# 二级 Tab 与新浪 RSS 的映射（category -> rss path）
# 新浪 RSS 基地址（优先 https）
SINA_CATEGORY_MAP = {
    "international": "finance/usstock.xml",      # 国际 -> 美股快报
    "market": "roll/stock/hot_roll.xml",         # 市场 -> 股票要闻汇总
    "other": "finance/financial.xml",            # 其他 -> 理财要闻
    "focus": "news/allnews/finance.xml",         # 焦点 -> 焦点新闻
    "company": "finance/fund.xml",               # 公司 -> 基金要闻（含公司动态）
    "macro": "roll/finance/hot_roll.xml",        # 宏观 -> 财经要闻汇总
    "lianghui": "roll/finance/hot_roll.xml",     # 两会 -> 财经要闻汇总（综合热点）
    "opinion": "finance/jsy.xml",                # 观点 -> 股市及时雨
}

SINA_RSS_BASE = "https://rss.sina.com.cn/"
RSSHUB_SINA_URL = "https://rsshub.app/finance/sina/roll"  # 备用：RSSHub 新浪财经
DECISION_LOGS_COLLECTION = "decision_logs"
SOURCE_SINA = "sina"

# 情绪分析关键词（与 eastmoney/cailianshe 一致）
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


class SinaService:
    """新浪财经 RSS 服务"""

    def _get_rss_url(self, category: str) -> str:
        """根据 category 获取 RSS 地址。category 为空时使用宏观（默认）"""
        path = SINA_CATEGORY_MAP.get(category, SINA_CATEGORY_MAP["macro"])
        return f"{SINA_RSS_BASE}{path}"

    async def fetch_and_parse(
        self,
        *,
        category: str = "macro",
        limit: int = 10,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        拉取财经快讯，解析为统一格式。
        新浪原生 RSS 已无可用条目，统一使用东方财富快讯（国内可用）。
        返回 (raw_feed_dict, parsed_items)。
        """
        from app.services.eastmoney_service import EastMoneyService

        _em = EastMoneyService()
        raw_fallback, parsed = await _em.fetch_and_parse(limit=limit)
        raw = {
            "source": SOURCE_SINA,
            "category": category,
            "feed": {
                "title": f"新浪财经-{category}（东方财富快讯）",
                "link": "https://finance.sina.com.cn/",
            },
            "entries_count": len(parsed),
        }
        return raw, parsed

    async def save_to_decision_logs(
        self,
        db: AsyncIOMotorDatabase,
        items: List[Dict[str, Any]],
        type_: str = "rss",
    ) -> int:
        """将解析后的条目保存至 decision_logs，source=sina"""
        if not items:
            return 0
        try:
            coll = db[DECISION_LOGS_COLLECTION]
            now = datetime.utcnow()
            count = 0
            for it in items:
                doc = {
                    "source": SOURCE_SINA,
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
            logger.info("sina_service 已保存 %d 条至 decision_logs", count)
            return count
        except Exception as e:
            logger.exception("sina_service save_to_decision_logs 异常: %s", e)
            raise
