# =====================================================
# 决策日志 API 路由
# POST /log, GET /list
# =====================================================

from typing import List, Optional

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_database
from app.models.decision_log import DecisionLog, DecisionLogCreate
from app.schemas.response import api_error, api_success
from app.utils.logger import logger

router = APIRouter()
COLLECTION = "decision_logs"


def _serialize_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
    return doc


@router.post("/log")
async def log_decision(
    item: DecisionLogCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """保存新决策日志"""
    try:
        from datetime import datetime

        coll = db[COLLECTION]
        doc = item.model_dump(exclude_none=True)
        if "timestamp" not in doc or doc["timestamp"] is None:
            doc["timestamp"] = datetime.utcnow()
        if "created_at" not in doc:
            doc["created_at"] = datetime.utcnow()
        result = await coll.insert_one(doc)
        doc["_id"] = result.inserted_id
        return api_success(data=_serialize_doc(doc))
    except Exception as e:
        logger.exception("log_decision 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/list")
async def list_decisions(
    limit: int = 100,
    skip: int = 0,
    fund_code: Optional[str] = None,
    user_action: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """获取决策日志列表"""
    try:
        coll = db[COLLECTION]
        query = {}
        if fund_code:
            query["fund_code"] = fund_code
        if user_action:
            query["user_action"] = user_action
        cursor = coll.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        data = [_serialize_doc(d) for d in docs]
        return api_success(data=data)
    except Exception as e:
        logger.exception("list_decisions 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("")
async def list_decisions_legacy(
    limit: int = 100,
    skip: int = 0,
    symbol: Optional[str] = None,
    action: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """兼容旧版：获取决策列表（symbol->fund_code, action->user_action）"""
    return await list_decisions(
        limit=limit, skip=skip, fund_code=symbol, user_action=action, db=db
    )


@router.delete("/{decision_id}")
async def delete_decision(
    decision_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """删除决策记录"""
    from bson import ObjectId

    try:
        coll = db[COLLECTION]
        result = await coll.delete_one({"_id": ObjectId(decision_id)})
        if result.deleted_count == 0:
            return api_error(code=404, message="决策不存在")
        return api_success(data=None, message="已删除")
    except Exception as e:
        logger.exception("delete_decision 异常: %s", e)
        return api_error(code=500, message=str(e))
