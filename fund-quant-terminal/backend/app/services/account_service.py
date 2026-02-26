# =====================================================
# 账户服务 - 资本与资产汇总
# =====================================================

from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

ACCOUNT_DOC_ID = "main"  # MongoDB 允许 string 作为 _id
DEFAULT_CAPITAL = 2000.0


async def get_capital(db: AsyncIOMotorDatabase) -> float:
    """获取当前现金"""
    doc = await db["account"].find_one({"_id": ACCOUNT_DOC_ID})
    return float(doc["capital"]) if doc and "capital" in doc else DEFAULT_CAPITAL


async def set_capital(db: AsyncIOMotorDatabase, capital: float) -> None:
    """设置当前现金"""
    from datetime import datetime

    await db["account"].update_one(
        {"_id": ACCOUNT_DOC_ID},
        {"$set": {"capital": capital, "updated_at": datetime.utcnow()}},
        upsert=True,
    )
