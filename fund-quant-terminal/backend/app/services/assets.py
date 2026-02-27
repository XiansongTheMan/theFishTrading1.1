# =====================================================
# 资产更新服务
# 支持事务 session，供决策流程与 assets_update 原子化
# =====================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClientSession, AsyncIOMotorDatabase

from app.services.account_service import set_capital

ASSETS_COLLECTION = "assets"


async def update_assets(
    db: AsyncIOMotorDatabase,
    *,
    capital: Optional[float] = None,
    assets: Optional[List[Dict[str, Any]]] = None,
    session: Optional[AsyncIOMotorClientSession] = None,
) -> None:
    """
    更新资本和/或持仓，支持事务。
    用于与 record_decision 同事务，或 assets_update 路由。
    """
    kw = {}
    if session is not None:
        kw["session"] = session

    if capital is not None:
        await set_capital(db, capital, session=session)

    if assets is not None:
        coll = db[ASSETS_COLLECTION]
        await coll.delete_many({}, **kw)
        now = datetime.utcnow()
        for a in assets:
            doc = {
                "symbol": a.get("symbol", ""),
                "name": a.get("name", ""),
                "quantity": float(a.get("quantity", 0)),
                "cost_price": a.get("cost_price"),
                "current_price": a.get("current_price"),
                "asset_type": a.get("asset_type", "fund"),
                "created_at": now,
                "updated_at": now,
            }
            if doc["symbol"] and doc["name"]:
                await coll.insert_one(doc, **kw)
