# =====================================================
# 财联社电报快讯服务
# 支持财联社原生 API（cls，国内可用）和 RSSHub（可能需代理）
# 输出与 eastmoney/wallstreetcn 一致的统一格式
# =====================================================

import hashlib
from datetime import datetime
from typing import Any, Dict, List

import feedparser
import httpx
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import llm_settings, settings
from app.utils.logger import logger

# 财联社 category 映射（与 config 中 typeOptions 的 value 对应，RSSHub 支持：watch,announcement,explain,red,jpush,remind,fund,hk）
CATEGORY_MAP = {
    "red": "加红",
    "remind": "提醒",
    "hk": "港美股",
    "announcement": "公司",
    "fund": "基金",
    "watch": "看板",
}
DECISION_LOGS_COLLECTION = "decision_logs"
SOURCE_CAILIANSHERSS = "cailianshe"
CLS_ROOT = "https://www.cls.cn"

# 情绪分析关键词（与 eastmoney_service 一致）
POSITIVE_KEYWORDS = ["利好", "上涨", "买入", "大涨", "看涨", "反弹", "增长", "突破", "增持", "推荐"]
NEGATIVE_KEYWORDS = ["利空", "下跌", "卖出", "大跌", "看跌", "回落", "跌破", "亏损", "减持", "预警"]


def _cls_sign(params: Dict[str, str]) -> str:
    """财联社 API 签名：MD5(SHA1(sorted_query_string))"""
    sorted_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    sha1_hex = hashlib.sha1(sorted_str.encode()).hexdigest()
    return hashlib.md5(sha1_hex.encode()).hexdigest()


def _parse_cls_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """解析财联社 API 单条为统一格式"""
    title = str(item.get("title") or item.get("content") or "").strip()
    content = str(item.get("content") or "").strip()[:500]
    url = str(item.get("shareurl") or "").strip()
    ctime = item.get("ctime")
    published_time = None
    if ctime is not None:
        try:
            ts = int(ctime) * 1000 if int(ctime) < 1e12 else int(ctime)
            dt = datetime.utcfromtimestamp(ts / 1000.0)
            published_time = dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        except (TypeError, ValueError, OSError):
            pass
    text_for_sentiment = f"{title} {content}"
    sentiment = _compute_sentiment(text_for_sentiment)
    return {
        "title": title or "(无标题)",
        "published_time": published_time,
        "summary": content,
        "url": url or None,
        "sentiment": sentiment,
    }


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


class CailiansheService:
    """财联社电报快讯服务：支持 cls 原生 API（国内可用）和 RSSHub"""

    async def _fetch_cls(
        self,
        *,
        category: str = "",
        limit: int = 10,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """从财联社 cls.cn 原生 API 拉取电报（国内可用）"""
        params: Dict[str, str] = {
            "appName": "CailianpressWeb",
            "os": "web",
            "sv": "7.7.5",
            "hasFirstVipArticle": "1",
        }
        if category:
            params["category"] = category
        params["sign"] = _cls_sign(params)

        api_path = "/v1/roll/get_roll_list" if category else "/nodeapi/updateTelegraphList"
        url = f"{CLS_ROOT}{api_path}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.cls.cn/telegraph",
        }
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        inner = data.get("data") or {}
        roll_data = inner.get("roll_data") or []
        parsed: List[Dict[str, Any]] = []
        for i, item in enumerate(roll_data):
            if i >= limit:
                break
            try:
                parsed.append(_parse_cls_item(item))
            except Exception as e:
                logger.debug("cailianshe_service 解析 cls 单条失败: %s", e)
                continue
        label = CATEGORY_MAP.get(category, "全部") if category else "全部"
        raw = {
            "source": "cailianshe",
            "category": category or "all",
            "feed": {"title": f"财联社电报-{label}", "link": f"{CLS_ROOT}/telegraph"},
            "entries_count": len(roll_data),
        }
        return raw, parsed

    async def fetch_and_parse(
        self,
        *,
        category: str = "",
        limit: int = 10,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        拉取财联社电报，解析为统一格式。
        默认使用 cls 原生 API（国内可用），可配置 CAILIANSHERSS_SOURCE=rsshub 使用 RSSHub。
        返回 (raw_feed_dict, parsed_items)。
        """
        source = (settings.CAILIANSHERSS_SOURCE or "cls").strip().lower()
        if source == "rsshub":
            try:
                return await self._fetch_rsshub(category=category, limit=limit)
            except Exception as e:
                logger.warning("cailianshe_service RSSHub 拉取失败: %s，尝试 cls 原生 API", e)
                return await self._fetch_cls(category=category, limit=limit)
        try:
            return await self._fetch_cls(category=category, limit=limit)
        except Exception as e:
            logger.warning("cailianshe_service cls 原生 API 拉取失败: %s，尝试 RSSHub", e)
            return await self._fetch_rsshub(category=category, limit=limit)

    def _get_rss_url(self, category: str) -> str:
        """获取 RSS 地址。category 为空时拉取全部"""
        base = settings.CAILIANSHERSS_RSS_BASE_URL.rstrip("/")
        if category:
            return f"{base}/cls/telegraph/{category}"
        return f"{base}/cls/telegraph"

    async def _fetch_rsshub(
        self,
        *,
        category: str = "",
        limit: int = 10,
    ) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """从 RSSHub 拉取财联社电报"""
        rss_url = self._get_rss_url(category)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        proxies = None
        if llm_settings.HTTP_PROXY or llm_settings.HTTPS_PROXY:
            proxies = (llm_settings.HTTPS_PROXY or llm_settings.HTTP_PROXY) or None

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers, proxy=proxies) as client:
                resp = await client.get(rss_url)
                resp.raise_for_status()
                content = resp.text
        except Exception as e:
            logger.warning("cailianshe_service 拉取 RSS 失败: %s", e)
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
                logger.debug("cailianshe_service 解析单条失败: %s", e)
                continue

        feed_meta = getattr(feed, "feed", None)
        label = CATEGORY_MAP.get(category, "全部") if category else "全部"
        raw = {
            "source": "cailianshe",
            "category": category or "all",
            "feed": {
                "title": getattr(feed_meta, "title", "") if feed_meta else f"财联社电报-{label}",
                "link": getattr(feed_meta, "link", "") if feed_meta else "",
            },
            "entries_count": len(entries),
        }
        return raw, parsed

    async def save_to_decision_logs(
        self,
        db: AsyncIOMotorDatabase,
        items: List[Dict[str, Any]],
        type_: str = "telegraph",
    ) -> int:
        """将解析后的条目保存至 decision_logs，source=cailianshe"""
        if not items:
            return 0
        try:
            coll = db[DECISION_LOGS_COLLECTION]
            now = datetime.utcnow()
            count = 0
            for it in items:
                doc = {
                    "source": SOURCE_CAILIANSHERSS,
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
            logger.info("cailianshe_service 已保存 %d 条至 decision_logs", count)
            return count
        except Exception as e:
            logger.exception("cailianshe_service save_to_decision_logs 异常: %s", e)
            raise
