# =====================================================
# 资产 API 路由
# 持仓与资产配置的增删改查，统一响应 {code, data, message}
# =====================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo import ReturnDocument

from app.database import get_database
from app.models.asset import AssetCreate
from app.schemas.assets_schemas import AssetsUpdateRequest, HoldingTransactionCreate
from app.schemas.response import api_error, api_success
from app.services.account_service import get_capital, set_capital
from app.services.data_fetcher import DataFetcherService
from app.utils.logger import logger

data_service = DataFetcherService()

router = APIRouter()
COLLECTION = "assets"
HISTORY_COLLECTION = "holding_histories"
TRANSACTION_COLLECTION = "holding_transactions"


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


async def _store_holding_history(
    db: AsyncIOMotorDatabase,
    symbol: str,
    asset_type: str,
    data: List[Dict[str, Any]],
) -> None:
    """将历史数据存入 holding_histories"""
    if not symbol or not data:
        return
    try:
        history_data = []
        for r in data:
            date_val = r.get("date") or r.get("净值日期") or r.get("日期")
            value_val = r.get("nav") or r.get("单位净值") or r.get("收盘") or r.get("close")
            if date_val and value_val is not None:
                history_data.append({"date": str(date_val), "value": float(value_val)})
        if not history_data:
            return
        await db[HISTORY_COLLECTION].update_one(
            {"symbol": symbol.strip(), "asset_type": asset_type or "fund"},
            {"$set": {"data": history_data, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
    except Exception as e:
        logger.warning("_store_holding_history 失败 %s %s: %s", symbol, asset_type, e)


@router.post("")
async def create_asset(
    item: AssetCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """创建资产记录，并拉取历史数据存入数据库"""
    try:
        coll = db[COLLECTION]
        doc = item.model_dump()
        doc["created_at"] = datetime.utcnow()
        doc["updated_at"] = datetime.utcnow()
        result = await coll.insert_one(doc)
        doc["_id"] = result.inserted_id

        # 新增后拉取历史信息并存储
        sym = (item.symbol or "").strip().split(".")[0]
        if sym:
            try:
                if (item.asset_type or "fund") == "fund":
                    nav_list = await data_service.get_fund_nav(sym)
                    await _store_holding_history(db, sym, "fund", nav_list)
                else:
                    daily_list = await data_service.get_stock_daily(symbol=sym)
                    await _store_holding_history(db, sym, "stock", daily_list)
            except Exception as e:
                logger.warning("create_asset 拉取历史失败 %s: %s", sym, e)

        return api_success(data=_serialize_doc(doc))
    except Exception as e:
        logger.exception("create_asset 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.post("/sync")
async def assets_sync(db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    """同步全部持仓：从外部接口拉取最新净值/价格、名称，并更新历史数据"""
    try:
        coll = db[COLLECTION]
        cursor = coll.find({})
        docs = await cursor.to_list(length=500)
        updated = 0
        failed = 0
        for d in docs:
            sym = (d.get("symbol") or "").strip().split(".")[0]
            asset_type = (d.get("asset_type") or "fund").lower()
            if not sym:
                continue
            try:
                updates: Dict[str, Any] = {"updated_at": datetime.utcnow()}
                if asset_type == "fund":
                    name = await data_service.get_fund_name(sym)
                    if name:
                        updates["name"] = name
                    nav_list = await data_service.get_fund_nav(sym)
                    if nav_list:
                        for r in reversed(nav_list):
                            n = r.get("nav") or r.get("单位净值")
                            if n is not None:
                                updates["current_price"] = float(n)
                                break
                    await _store_holding_history(db, sym, "fund", nav_list)
                else:
                    name = await data_service.get_stock_name(sym)
                    if name:
                        updates["name"] = name
                    daily_list = await data_service.get_stock_daily(symbol=sym)
                    if daily_list and len(daily_list) > 0:
                        last_rec = daily_list[-1]
                        price = last_rec.get("收盘") or last_rec.get("close")
                        if price is not None:
                            updates["current_price"] = float(price)
                    await _store_holding_history(db, sym, "stock", daily_list)

                if len(updates) > 1:
                    await coll.update_one({"_id": d["_id"]}, {"$set": updates})
                    updated += 1
            except Exception as e:
                logger.warning("sync 单条失败 %s %s: %s", sym, asset_type, e)
                failed += 1

        return api_success(
            data={"updated": updated, "failed": failed, "total": len(docs)},
            message=f"同步完成：成功 {updated}，失败 {failed}",
        )
    except Exception as e:
        logger.exception("assets_sync 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/history/{asset_type}/{symbol}")
async def get_holding_history(
    asset_type: str,
    symbol: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """从数据库获取已缓存的持仓历史（净值/价格走势）"""
    try:
        sym = (symbol or "").strip().split(".")[0]
        at = (asset_type or "fund").lower()
        if not sym:
            return api_error(code=400, message="标的代码不能为空")
        doc = await db[HISTORY_COLLECTION].find_one(
            {"symbol": sym, "asset_type": at}
        )
        if not doc or not doc.get("data"):
            return api_success(data={"data": [], "symbol": sym, "source": "empty"})
        return api_success(
            data={
                "data": doc["data"],
                "symbol": sym,
                "source": "db",
                "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
            }
        )
    except Exception as e:
        logger.exception("get_holding_history 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/history/{asset_type}/{symbol}/transactions")
async def get_holding_transactions(
    asset_type: str,
    symbol: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """获取该持仓的历史交易记录"""
    try:
        sym = (symbol or "").strip().split(".")[0]
        at = (asset_type or "fund").lower()
        if not sym:
            return api_error(code=400, message="标的代码不能为空")
        cursor = db[TRANSACTION_COLLECTION].find(
            {"symbol": sym, "asset_type": at}
        ).sort("date", -1)
        docs = await cursor.to_list(length=500)
        data = [_serialize_doc(d) for d in docs]
        return api_success(data=data)
    except Exception as e:
        logger.exception("get_holding_transactions 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/history/{asset_type}/{symbol}/summary")
async def get_holding_summary(
    asset_type: str,
    symbol: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """获取该持仓的汇总：投入资金、持有收益，当前市值使用真实行情价"""
    try:
        sym = (symbol or "").strip().split(".")[0]
        at = (asset_type or "fund").lower()
        if not sym:
            return api_error(code=400, message="标的代码不能为空")
        asset = await db[COLLECTION].find_one({"symbol": sym, "asset_type": at})
        quantity = 0.0
        cost_price = 0.0
        current_price = 0.0
        name = sym
        if asset:
            quantity = float(asset.get("quantity") or 0)
            cost_price = float(asset.get("cost_price") or 0)
            current_price = float(asset.get("current_price") or cost_price or 0)
            name = asset.get("name") or sym
        if quantity > 0:
            try:
                if at == "fund":
                    nav_list = await data_service.get_fund_nav(sym)
                    if nav_list:
                        for r in reversed(nav_list):
                            p = r.get("nav") or r.get("单位净值")
                            if p is not None:
                                current_price = float(p)
                                break
                else:
                    daily_list = await data_service.get_stock_daily(symbol=sym)
                    if daily_list:
                        last_rec = daily_list[-1]
                        p = last_rec.get("收盘") or last_rec.get("close")
                        if p is not None:
                            current_price = float(p)
            except Exception as e:
                logger.debug("get_holding_summary 拉取实时价失败 %s %s: %s", sym, at, e)
        invested = round(quantity * cost_price, 2)
        market_value = round(quantity * current_price, 2)
        # 持有收益 = 市值 - 成本
        profit = round(market_value - invested, 2)
        return api_success(
            data={
                "symbol": sym,
                "asset_type": at,
                "name": name,
                "quantity": quantity,
                "cost_price": cost_price,
                "current_price": current_price,
                "invested": invested,
                "market_value": market_value,
                "profit": profit,
                "profit_rate": round((profit / invested * 100), 2) if invested else 0,
            }
        )
    except Exception as e:
        logger.exception("get_holding_summary 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.post("/transactions")
async def create_transaction(
    item: HoldingTransactionCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """添加买入/卖出交易，并更新资产持仓（无效交易不会写入）"""
    try:
        sym = (item.symbol or "").strip().split(".")[0]
        at = (item.asset_type or "fund").lower()
        if not sym:
            return api_error(code=400, message="标的代码不能为空")
        if item.type not in ("buy", "sell"):
            return api_error(code=400, message="type 必须为 buy 或 sell")
        if item.quantity <= 0 or item.price <= 0:
            return api_error(code=400, message="数量和单价必须大于 0")
        amount = item.amount if item.amount is not None else round(item.quantity * item.price, 2)
        if amount <= 0:
            return api_error(code=400, message="金额必须大于 0")
        if not item.date or len(item.date.strip()) < 8:
            return api_error(code=400, message="请填写有效交易日期")

        coll = db[COLLECTION]
        asset = await coll.find_one({"symbol": sym, "asset_type": at})
        if item.type == "sell":
            if not asset:
                return api_error(code=400, message="无此持仓，无法卖出")
            old_qty = float(asset.get("quantity") or 0)
            if item.quantity > old_qty:
                return api_error(code=400, message=f"卖出数量不能超过持仓 {old_qty}")

        tx_doc = {
            "symbol": sym,
            "asset_type": at,
            "date": item.date.strip(),
            "type": item.type,
            "quantity": item.quantity,
            "price": item.price,
            "amount": amount,
            "created_at": datetime.utcnow(),
        }
        result = await db[TRANSACTION_COLLECTION].insert_one(tx_doc)
        tx_doc["_id"] = result.inserted_id

        if item.type == "buy":
            if asset:
                old_qty = float(asset.get("quantity") or 0)
                old_cost = float(asset.get("cost_price") or 0)
                new_qty = old_qty + item.quantity
                new_cost = (old_qty * old_cost + item.quantity * item.price) / new_qty if new_qty else 0
                await coll.update_one(
                    {"_id": asset["_id"]},
                    {"$set": {"quantity": new_qty, "cost_price": new_cost, "updated_at": datetime.utcnow()}},
                )
            else:
                await coll.insert_one({
                    "symbol": sym,
                    "name": sym,
                    "asset_type": at,
                    "quantity": item.quantity,
                    "cost_price": item.price,
                    "current_price": item.price,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
        else:  # sell（已在插入前校验）
            old_qty = float(asset.get("quantity") or 0)
            new_qty = old_qty - item.quantity
            cost_price = float(asset.get("cost_price") or 0)
            updates = {"quantity": new_qty, "updated_at": datetime.utcnow()}
            if new_qty <= 0:
                await coll.delete_one({"_id": asset["_id"]})
            else:
                updates["cost_price"] = cost_price
                await coll.update_one({"_id": asset["_id"]}, {"$set": updates})

        return api_success(data=_serialize_doc(tx_doc), message="交易记录已添加")
    except Exception as e:
        logger.exception("create_transaction 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.delete("/history/{asset_type}/{symbol}/transactions/{transaction_id}")
async def delete_transaction(
    asset_type: str,
    symbol: str,
    transaction_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """删除交易记录，并反向更新资产持仓"""
    try:
        coll_tx = db[TRANSACTION_COLLECTION]
        coll_asset = db[COLLECTION]
        try:
            tx_doc = await coll_tx.find_one({"_id": ObjectId(transaction_id)})
        except Exception:
            return api_error(code=400, message="交易ID无效")
        if not tx_doc:
            return api_error(code=404, message="交易记录不存在")
        sym = (tx_doc.get("symbol") or "").strip()
        at = (tx_doc.get("asset_type") or "fund").lower()
        tx_type = tx_doc.get("type")
        qty = float(tx_doc.get("quantity") or 0)
        price = float(tx_doc.get("price") or 0)
        asset = await coll_asset.find_one({"symbol": sym, "asset_type": at})
        if tx_type == "buy":
            if asset:
                new_qty = float(asset.get("quantity") or 0)
                new_cost = float(asset.get("cost_price") or 0)
                old_qty = new_qty - qty
                if old_qty < 0:
                    return api_error(code=400, message="无法删除：会导致持仓数量为负")
                if old_qty <= 0:
                    await coll_asset.delete_one({"_id": asset["_id"]})
                else:
                    old_cost = (new_qty * new_cost - qty * price) / old_qty
                    await coll_asset.update_one(
                        {"_id": asset["_id"]},
                        {"$set": {"quantity": old_qty, "cost_price": old_cost, "updated_at": datetime.utcnow()}},
                    )
            else:
                return api_error(code=400, message="无对应持仓，无法反向删除买入")
        else:
            if asset:
                old_qty = float(asset.get("quantity") or 0)
                cost_price = float(asset.get("cost_price") or 0)
                await coll_asset.update_one(
                    {"_id": asset["_id"]},
                    {"$set": {"quantity": old_qty + qty, "cost_price": cost_price, "updated_at": datetime.utcnow()}},
                )
            else:
                await coll_asset.insert_one({
                    "symbol": sym,
                    "name": sym,
                    "asset_type": at,
                    "quantity": qty,
                    "cost_price": price,
                    "current_price": price,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                })
        await coll_tx.delete_one({"_id": ObjectId(transaction_id)})
        return api_success(data=None, message="交易已删除")
    except Exception as e:
        logger.exception("delete_transaction 异常: %s", e)
        return api_error(code=500, message=str(e))


@router.post("/history/{asset_type}/{symbol}/transactions/clear")
async def clear_holding_transactions(
    asset_type: str,
    symbol: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """强制清空该基金/股票的全部历史操作，并移除对应持仓"""
    try:
        sym = (symbol or "").strip().split(".")[0]
        at = (asset_type or "fund").lower()
        if not sym:
            return api_error(code=400, message="标的代码不能为空")
        coll_tx = db[TRANSACTION_COLLECTION]
        coll_asset = db[COLLECTION]
        result = await coll_tx.delete_many({"symbol": sym, "asset_type": at})
        await coll_asset.delete_many({"symbol": sym, "asset_type": at})
        return api_success(
            data={"deleted": result.deleted_count},
            message=f"已清空 {result.deleted_count} 条历史操作及对应持仓",
        )
    except Exception as e:
        logger.exception("clear_holding_transactions 异常: %s", e)
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
