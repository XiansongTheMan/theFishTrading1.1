# =====================================================
# 资产 API 路由
# 持仓与资产配置的增删改查，统一响应 {code, data, message}
# =====================================================

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import ReturnDocument

from app.database import get_database
from app.models.asset import AssetCreate
from app.schemas.assets_schemas import AssetsUpdateRequest
from app.schemas.response import api_error, api_success
from app.services.account_service import get_capital, set_capital
from app.utils.logger import logger

router = APIRouter()
COLLECTION = "assets"


def _serialize_doc(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
    return doc


@router.get("")
async def list_assets(
    limit: int = 100,
    skip: int = 0,
    symbol: Optional[str] = None,
    asset_type: Optional[str] = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """获取资产列表"""
    try:
        coll = db[COLLECTION]
        query = {}
        if symbol:
            query["symbol"] = symbol
        if asset_type:
            query["asset_type"] = asset_type
        cursor = coll.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(length=limit)
        data = [_serialize_doc(d) for d in docs]
        return api_success(data=data)
    except Exception as e:
        logger.exception("list_assets 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.post("")
async def create_asset(
    item: AssetCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """创建资产记录"""
    try:
        coll = db[COLLECTION]
        doc = item.model_dump()
        result = await coll.insert_one(doc)
        doc["_id"] = result.inserted_id
        return api_success(data=_serialize_doc(doc))
    except Exception as e:
        logger.exception("create_asset 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/summary")
async def assets_summary(db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    """资产汇总：现金、持仓、总价值"""
    try:
        capital = await get_capital(db)
        coll = db[COLLECTION]
        cursor = coll.find({})
        docs = await cursor.to_list(length=500)
        holdings = []
        holdings_value = 0.0
        for d in docs:
            h = _serialize_doc(d)
            holdings.append(h)
            price = h.get("current_price") or h.get("cost_price") or 0
            holdings_value += (h.get("quantity") or 0) * price
        total_value = capital + holdings_value
        return api_success(
            data={
                "capital": capital,
                "holdings": holdings,
                "holdings_value": round(holdings_value, 2),
                "total_value": round(total_value, 2),
            }
        )
    except Exception as e:
        logger.exception("assets_summary 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.post("/update")
async def assets_update(
    body: AssetsUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """交易执行后更新：资本、持仓"""
    try:
        if body.capital is not None:
            await set_capital(db, body.capital)
        if body.assets is not None:
            coll = db[COLLECTION]
            await coll.delete_many({})
            for a in body.assets:
                doc = {
                    "symbol": a.get("symbol", ""),
                    "name": a.get("name", ""),
                    "quantity": float(a.get("quantity", 0)),
                    "cost_price": a.get("cost_price"),
                    "current_price": a.get("current_price"),
                    "asset_type": a.get("asset_type", "fund"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }
                if doc["symbol"] and doc["name"]:
                    await coll.insert_one(doc)
        return api_success(data=None, message="更新成功")
    except Exception as e:
        logger.exception("assets_update 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """根据 ID 获取资产"""
    try:
        coll = db[COLLECTION]
        doc = await coll.find_one({"_id": ObjectId(asset_id)})
        if not doc:
            return api_error(code=404, message="资产不存在")
        return api_success(data=_serialize_doc(doc))
    except Exception as e:
        logger.exception("get_asset 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.put("/{asset_id}")
async def update_asset(
    asset_id: str,
    item: AssetCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """更新资产"""
    try:
        coll = db[COLLECTION]
        doc = item.model_dump()
        doc["updated_at"] = datetime.utcnow()
        result = await coll.find_one_and_update(
            {"_id": ObjectId(asset_id)},
            {"$set": doc},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            return api_error(code=404, message="资产不存在")
        return api_success(data=_serialize_doc(result))
    except Exception as e:
        logger.exception("update_asset 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """删除资产"""
    try:
        coll = db[COLLECTION]
        result = await coll.delete_one({"_id": ObjectId(asset_id)})
        if result.deleted_count == 0:
            return api_error(code=404, message="资产不存在")
        return api_success(data=None, message="已删除")
    except Exception as e:
        logger.exception("delete_asset 异常: %s", e)
        return api_error(code=500, message=str(e))
