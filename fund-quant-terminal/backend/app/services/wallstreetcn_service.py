# =====================================================
# 华尔街见闻业务服务
# 调用 Client、解析关键字段、可选保存至 decision_logs
#
# 【Grok Agent 调用指南】
# 未来 Grok 4.2 决策时可调用 POST /api/wallstreetcn/test 获取股市情报：
# - type=lives: 实时快讯，无额外参数，用于最新市场动态
# - type=articles: 深度文章，channel 默认 news
# - type=keyword: 关键词搜索，必填 keyword，如 "美联储" "加息"
# - type=search: 个股搜索，必填 keyword 作为股票名称/代码
# - type=quote: 行情快照，必填 code（如 600519）
# 返回 parsed 时含 title、published_time、summary、url、sentiment，可直接纳入 Grok 决策上下文。
# 与 AKShare/Tushare 完全独立，无数据源冲突。
# =====================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.services.wallstreetcn_client import WallStreetCNClient
from app.utils.logger import logger

# 情绪分析关键词（复用 news_fetch 逻辑）
POSITIVE_KEYWORDS = ["利好", "上涨", "买入", "大涨", "看涨", "反弹", "增长", "突破", "增持", "推荐"]
NEGATIVE_KEYWORDS = ["利空", "下跌", "卖出", "大跌", "看跌", "回落", "跌破", "亏损", "减持", "预警"]
DECISION_LOGS_COLLECTION = "decision_logs"
SOURCE_WALLSTREETCN = "wallstreetcn"


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


def _parse_timestamp(ts: Any) -> Optional[datetime]:
    """解析时间戳：支持 Unix 秒、毫秒或 ISO 字符串"""
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            if ts > 1e12:
                ts = ts / 1000.0
            return datetime.utcfromtimestamp(ts)
        s = str(ts).strip()
        for fmt, max_len in (("%Y-%m-%dT%H:%M:%S", 19), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
            try:
                return datetime.strptime(s[:max_len], fmt)
            except ValueError:
                continue
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _extract_items(raw: Any) -> List[Dict[str, Any]]:
    """从 API 响应中提取 items 列表"""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        items = raw.get("items")
        if items is None:
            data = raw.get("data")
            if isinstance(data, dict):
                items = data.get("items")
        if isinstance(items, list):
            return items
    return []


def _parse_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """解析单条为统一格式：title, published_time, summary, url, sentiment"""
    title = str(item.get("title") or item.get("headline") or "").strip()
    content = str(item.get("content_text") or item.get("content") or item.get("summary") or "").strip()
    summary = content[:500] if content else ""
    url = str(item.get("uri") or item.get("link") or item.get("url") or "").strip()
    ts = item.get("display_time") or item.get("created_at") or item.get("published_at") or item.get("timestamp")
    published_time = _parse_timestamp(ts)
    text_for_sentiment = f"{title} {summary}"
    sentiment = _compute_sentiment(text_for_sentiment)
    return {
        "title": title or "(无标题)",
        "published_time": published_time.isoformat() if published_time else None,
        "summary": summary,
        "url": url or None,
        "sentiment": sentiment,
    }


class WallStreetCNService:
    """华尔街见闻业务服务：拉取、解析、可选保存"""

    def __init__(self) -> None:
        self._client = WallStreetCNClient(base_url=settings.WALLSTREETCN_BASE_URL)

    async def fetch_and_parse(
        self,
        type_: str,
        *,
        limit: int = 10,
        cursor: int = 0,
        channel: str = "news",
        keyword: Optional[str] = None,
        code: Optional[str] = None,
    ) -> tuple[Any, List[Dict[str, Any]]]:
        """
        调用 Client 拉取数据，对新闻类结果解析关键字段。
        返回 (raw, parsed_items)，parsed_items 仅对 lives/articles/keyword 有值。
        """
        raw = None
        if type_ == "lives":
            raw = await self._client.get_live_news(limit=limit, cursor=cursor)
        elif type_ == "articles":
            raw = await self._client.get_articles(channel=channel, limit=limit)
        elif type_ == "keyword" and keyword:
            raw = await self._client.search_by_keyword(keyword=keyword, limit=limit)
        elif type_ == "search" and keyword:
            raw = await self._client.search_stock(query=keyword, limit=limit)
        elif type_ == "quote" and code:
            raw = await self._client.get_quote(code=code)
        else:
            return None, []

        if type_ in ("lives", "articles", "keyword"):
            items = _extract_items(raw)
            parsed = [_parse_item(i) for i in items]
            return raw, parsed
        return raw, []

    async def save_to_decision_logs(
        self,
        db: AsyncIOMotorDatabase,
        items: List[Dict[str, Any]],
        type_: str,
    ) -> int:
        """
        将解析后的条目保存至 decision_logs，source=wallstreetcn。
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
                    "source": SOURCE_WALLSTREETCN,
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
            logger.info("wallstreetcn_service 已保存 %d 条至 decision_logs", count)
            return count
        except Exception as e:
            logger.exception("wallstreetcn_service save_to_decision_logs 异常: %s", e)
            raise
