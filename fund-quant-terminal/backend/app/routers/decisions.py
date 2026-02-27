# =====================================================
# 决策日志 API 路由
# POST /log, GET /list
# 创建决策时若含 capital_after 且为 buy/sell，与资产更新同事务原子提交
# =====================================================

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.models.decision_log import DecisionLog, DecisionLogCreate
from app.schemas.response import api_success
from app.services.assets import update_assets
from app.services.grok_decision import generate_grok_prompt
from app.utils.logger import logger

router = APIRouter()
COLLECTION = "decision_logs"


class GrokDecisionRequest(BaseModel):
    fund_code: str = Field(..., description="基金代码")
    include_news: bool = Field(True, description="是否在响应中包含新闻摘要列表")


def _serialize_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
    return doc


@router.post("/grok-decision")
async def decisions_grok_decision(
    body: GrokDecisionRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """生成 Grok 决策提示词：基于基金最近 72 小时新闻与情绪分析，返回可直接复制的完整提示 + 新闻摘要"""
    try:
        prompt, news_summary = await generate_grok_prompt(
            body.fund_code,
            db,
            include_news_list=body.include_news,
        )
        data = {"prompt": prompt}
        if body.include_news:
            data["news_summary"] = news_summary
        return api_success(data=data, message="已生成决策提示词")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("decisions_grok_decision 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log")
async def log_decision(
    item: DecisionLogCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """保存新决策日志。当 user_action 为 buy/sell 且含 capital_after 时，与资产更新同事务原子提交"""
    from datetime import datetime

    try:
        doc = item.model_dump(exclude_none=True)
        if "timestamp" not in doc or doc["timestamp"] is None:
            doc["timestamp"] = datetime.utcnow()
        if "created_at" not in doc:
            doc["created_at"] = datetime.utcnow()

        capital_after = doc.get("capital_after")
        user_action = (doc.get("user_action") or "").lower()
        needs_asset_update = (
            user_action in ("buy", "sell")
            and capital_after is not None
        )

        if needs_asset_update:
            client = db.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    coll = db[COLLECTION]
                    result = await coll.insert_one(doc, session=session)
                    doc["_id"] = result.inserted_id
                    await update_assets(db, capital=float(capital_after), session=session)
        else:
            coll = db[COLLECTION]
            result = await coll.insert_one(doc)
            doc["_id"] = result.inserted_id

        return api_success(data=_serialize_doc(doc))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("log_decision 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_decisions 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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


@router.put("/{decision_id}")
async def update_decision(
    decision_id: str,
    item: DecisionLogCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """更新决策记录。当 user_action 为 buy/sell 且含 capital_after 时，与资产更新同事务原子提交"""
    from bson import ObjectId
    from datetime import datetime

    try:
        doc = item.model_dump(exclude_none=True)
        doc["updated_at"] = datetime.utcnow()

        capital_after = doc.get("capital_after")
        user_action = (doc.get("user_action") or "").lower()
        needs_asset_update = (
            user_action in ("buy", "sell")
            and capital_after is not None
        )

        if needs_asset_update:
            client = db.client
            async with await client.start_session() as session:
                async with session.start_transaction():
                    coll = db[COLLECTION]
                    result = await coll.find_one_and_update(
                        {"_id": ObjectId(decision_id)},
                        {"$set": doc},
                        return_document="after",
                        session=session,
                    )
                    if not result:
                        raise HTTPException(status_code=404, detail="决策不存在")
                    await update_assets(db, capital=float(capital_after), session=session)
        else:
            coll = db[COLLECTION]
            result = await coll.find_one_and_update(
                {"_id": ObjectId(decision_id)},
                {"$set": doc},
                return_document="after",
            )
            if not result:
                raise HTTPException(status_code=404, detail="决策不存在")

        return api_success(data=_serialize_doc(result))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_decision 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


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
            raise HTTPException(status_code=404, detail="决策不存在")
        return api_success(data=None, message="已删除")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_decision 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
