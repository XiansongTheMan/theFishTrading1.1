# =====================================================
# 投资组合上下文构建服务
# 聚合资产汇总、近期新闻、市场快照、用户风险偏好，供 AI 决策或展示使用
# =====================================================

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.services.account_service import get_capital
from app.services.data_fetcher import DataFetcherService
from app.services.wallstreetcn_service import WallStreetCNService
from app.utils.logger import logger

# 常量
ASSETS_COLLECTION = "assets"
CONFIG_COLLECTION = "config"
RISK_PROFILE_DOC_ID = "risk_profile"
RISK_PROFILE_USER_PREFIX = "risk_profile_"
DEFAULT_RISK_PROFILE = "moderate"
HS300_SYMBOL = "000300"
FUND_INDEX_SYMBOL = "000011"  # 上证基金指数


def _get_data_service() -> DataFetcherService:
    """获取已配置 tokens 的共享 DataFetcherService（含 DB 更新的 tushare/akshare 配置）"""
    from app.routers.data import data_service
    return data_service


class PortfolioContextOutput(BaseModel):
    """PortfolioContextBuilder 输出结构（用于类型校验与文档）"""

    asset_summary: Dict[str, Any] = Field(default_factory=dict, description="资产汇总")
    recent_news: List[Dict[str, Any]] = Field(default_factory=list, description="近期新闻列表")
    market_snapshot: Dict[str, Any] = Field(default_factory=dict, description="市场指数快照")
    timestamp: str = Field(default="", description="构建时间 ISO8601")
    risk_profile: str = Field(default=DEFAULT_RISK_PROFILE, description="用户风险偏好")


def _serialize_doc(doc: Optional[Dict]) -> Dict:
    """序列化 MongoDB 文档，移除 _id 并转为 id"""
    if not doc:
        return {}
    d = dict(doc)
    if "_id" in d:
        d["id"] = str(d["_id"])
        del d["_id"]
    return d


async def _fetch_asset_summary(db: AsyncIOMotorDatabase) -> Dict[str, Any]:
    """
    获取资产汇总：现金、持仓、持仓市值、总资产。
    复用 assets 路由逻辑，当前为单用户模式，暂不按 user_id 过滤。
    """
    try:
        capital = await get_capital(db)
        coll = db[ASSETS_COLLECTION]
        cursor = coll.find({})
        docs = await cursor.to_list(length=500)
        holdings = []
        holdings_value = 0.0
        for d in docs:
            h = _serialize_doc(d)
            holdings.append(h)
            price = h.get("current_price") or h.get("cost_price") or 0
            holdings_value += (h.get("quantity") or 0) * float(price)
        return {
            "capital": capital,
            "holdings": holdings,
            "holdings_value": round(holdings_value, 2),
            "total_value": round(capital + holdings_value, 2),
        }
    except Exception as e:
        logger.exception("_fetch_asset_summary 异常: %s", e)
        return {
            "capital": 0.0,
            "holdings": [],
            "holdings_value": 0.0,
            "total_value": 0.0,
            "_error": str(e),
        }


async def _fetch_recent_news(
    wallstreetcn_service: WallStreetCNService,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    从华尔街见闻获取最新快讯，解析为 title, content, sentiment 格式。
    """
    try:
        _, parsed = await wallstreetcn_service.fetch_and_parse(
            type_="lives",
            limit=limit,
            cursor=0,
            channel="a-stock-channel",
        )
        if not parsed:
            return []
        result = []
        for p in parsed[:limit]:
            result.append({
                "title": p.get("title") or "",
                "content": p.get("summary") or "",
                "sentiment": float(p.get("sentiment", 0.0)),
            })
        return result
    except Exception as e:
        logger.exception("_fetch_recent_news 异常: %s", e)
        return []


async def _fetch_market_snapshot(
    data_service: DataFetcherService,
) -> Dict[str, Any]:
    """
    获取沪深300(000300)、上证基金指数(000011)最新日线数据。
    使用共享 data_service（AKShare/Tushare），确保获取真实数据并记录日志。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")
    indices: List[Dict[str, Any]] = []

    for symbol, name in [(HS300_SYMBOL, "沪深300"), (FUND_INDEX_SYMBOL, "上证基金指数")]:
        try:
            rows = await data_service.get_index_daily(
                symbol=symbol,
                start=start_date,
                end=today,
            )
            if not rows:
                logger.warning("_fetch_market_snapshot %s(%s) 无数据，跳过", name, symbol)
                indices.append({
                    "symbol": symbol,
                    "name": name,
                    "date": None,
                    "close": None,
                    "change_pct": None,
                    "_error": "无日线数据",
                })
                continue
            sorted_rows = sorted(
                rows,
                key=lambda r: str(r.get("date") or r.get("trade_date") or ""),
                reverse=True,
            )
            latest = sorted_rows[0]
            date_val = latest.get("date") or latest.get("trade_date")
            close_val = latest.get("close")
            if close_val is None:
                close_val = latest.get("收盘价") or latest.get("收盘") or latest.get("收")
            change_val = latest.get("pct_chg") or latest.get("涨跌幅") or latest.get("change_pct")
            if change_val is None and "幅度" in latest:
                change_val = latest.get("幅度")
            close_float = float(close_val) if close_val is not None else None
            change_float = float(change_val) if change_val is not None else None
            idx = {
                "symbol": symbol,
                "name": name,
                "date": str(date_val) if date_val else None,
                "close": close_float,
                "change_pct": change_float,
            }
            indices.append(idx)
            logger.info(
                "market_snapshot 已获取: %s %s date=%s close=%s change_pct=%s",
                name, symbol, idx["date"], idx["close"], idx["change_pct"],
            )
        except Exception as e:
            logger.warning("_fetch_market_snapshot 指数 %s(%s) 获取失败: %s", name, symbol, e)
            indices.append({
                "symbol": symbol,
                "name": name,
                "date": None,
                "close": None,
                "change_pct": None,
                "_error": str(e),
            })

    return {"indices": indices}


async def _fetch_risk_profile(db: AsyncIOMotorDatabase, user_id: str) -> str:
    """
    从 MongoDB config 获取用户风险偏好。
    先查 user_id 专属文档，再查默认文档，均无则返回 moderate。
    """
    valid_profiles = ("conservative", "moderate", "aggressive")
    try:
        doc = await db[CONFIG_COLLECTION].find_one({
            "_id": f"{RISK_PROFILE_USER_PREFIX}{user_id}"
        })
        if doc:
            profile = (doc.get("profile") or doc.get("risk_profile") or "").strip().lower()
            if profile in valid_profiles:
                return profile

        doc = await db[CONFIG_COLLECTION].find_one({"_id": RISK_PROFILE_DOC_ID})
        if doc:
            default = (doc.get("default") or doc.get("profile") or "").strip().lower()
            if default in valid_profiles:
                return default
            users = doc.get("user_profiles") or {}
            up = (users.get(user_id) or "").strip().lower()
            if up in valid_profiles:
                return up
    except Exception as e:
        logger.warning("_fetch_risk_profile 异常: %s", e)
    return DEFAULT_RISK_PROFILE


def get_portfolio_context_builder() -> "PortfolioContextBuilder":
    """FastAPI Depends：返回 PortfolioContextBuilder 单例"""
    return PortfolioContextBuilder()


class PortfolioContextBuilder:
    """
    投资组合上下文构建器。

    聚合资产汇总、华尔街见闻近期新闻、沪深300/上证基金指数市场快照、
    用户风险偏好，供 AI 决策或前端展示使用。
    """

    def __init__(self) -> None:
        self._wallstreetcn_service = WallStreetCNService()

    async def build_context(self, user_id: str) -> dict:
        """
        构建完整的投资组合上下文。

        Args:
            user_id: 用户 ID，用于风险偏好查询。

        Returns:
            asset_summary, recent_news, market_snapshot, timestamp, risk_profile
        """
        from app.database import get_database as _get_db
        db = await _get_db()
        data_service = _get_data_service()

        timestamp = datetime.utcnow().isoformat() + "Z"

        asset_task = _fetch_asset_summary(db)
        news_task = _fetch_recent_news(self._wallstreetcn_service, limit=10)
        market_task = _fetch_market_snapshot(data_service)
        risk_task = _fetch_risk_profile(db, user_id)

        asset_summary, recent_news, market_snapshot, risk_profile = await asyncio.gather(
            asset_task, news_task, market_task, risk_task
        )

        ctx = {
            "asset_summary": asset_summary,
            "recent_news": recent_news,
            "market_snapshot": market_snapshot,
            "timestamp": timestamp,
            "risk_profile": risk_profile,
        }
        return PortfolioContextOutput(**ctx).model_dump()
