# =====================================================
# 数据相关 API 路由
# /api/data/fetch, /api/data/history, 基金/股票/指数数据
# =====================================================

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.response import api_success
from app.schemas.data_schemas import DataFetchRequest
from app.services.data_fetcher import DataFetcherService
from app.utils.logger import logger

router = APIRouter()
data_service = DataFetcherService()


# ---------- 新增 /fetch 与 /history ----------


@router.post("/fetch")
async def data_fetch(req: DataFetchRequest) -> dict:
    """
    数据拉取接口
    data_type: nav->基金净值, list->基金列表, info->Tushare基金信息
    """
    try:
        fund_code = (req.fund_code or "").strip()
        data_type = req.data_type or "nav"

        if data_type == "nav":
            if not fund_code:
                raise HTTPException(status_code=400, detail="data_type=nav 时需提供 fund_code")
            data = await data_service.get_fund_nav(fund_code)
            return api_success(data={"fund_code": fund_code, "data_type": "nav", "data": data, "total": len(data)})
        elif data_type == "list":
            data = await data_service.get_fund_list(limit=500)
            return api_success(data={"data_type": "list", "data": data, "total": len(data)})
        elif data_type == "info":
            fc = fund_code if fund_code else None
            data = await data_service.get_tushare_fund_info(fc)
            return api_success(data={"fund_code": fund_code, "data_type": "info", "data": data, "total": len(data)})
        else:
            raise HTTPException(status_code=400, detail=f"不支持的 data_type: {data_type}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("data_fetch 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def data_history(
    fund_code: str = Query(..., description="基金代码"),
    start_date: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
    limit: int = Query(100, ge=1, le=1000, description="返回条数"),
) -> dict:
    """
    获取基金净值历史
    """
    try:
        data = await data_service.get_fund_nav_history(
            fund_code=fund_code, start_date=start_date, end_date=end_date, limit=limit
        )
        return api_success(data={"fund_code": fund_code, "data": data, "total": len(data)})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("data_history 异常 fund_code=%s: %s", fund_code, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------- 原有接口（统一响应格式） ----------


@router.get("/fund/{fund_code}")
async def get_fund_info(fund_code: str) -> dict:
    """
    获取基金名称与最新净值，用于添加基金时自动填充
    """
    try:
        fund_code = (fund_code or "").strip()
        if not fund_code:
            raise HTTPException(status_code=400, detail="基金代码不能为空")
        nav_data = await data_service.get_fund_nav(fund_code)
        fund_list = await data_service.get_fund_list(limit=5000)
        nav = None
        if nav_data:
            for r in reversed(nav_data):
                n = r.get("nav") or r.get("单位净值")
                if n is not None:
                    nav = float(n)
                    break
            if nav is None and nav_data:
                nav = float(nav_data[-1].get("nav") or nav_data[-1].get("单位净值") or 0)
        # 优先用 fund_list 查找（快），未找到则调用 get_fund_name 获取真实名称
        name = None
        code_clean = fund_code.strip().replace(".OF", "")
        for f in fund_list:
            c = str(f.get("code") or f.get("基金代码") or "").replace(".OF", "").strip()
            if c == code_clean:
                name = str(f.get("name") or f.get("基金简称") or "").strip()
                break
        if not name:
            name = await data_service.get_fund_name(fund_code)
        return api_success(data={"fund_code": fund_code, "name": name or f"基金{fund_code}", "nav": nav})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_fund_info 异常 fund_code=%s: %s", fund_code, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{symbol}")
async def get_stock_info(symbol: str) -> dict:
    """
    获取股票名称与最新价，用于添加股票时自动填充
    """
    try:
        symbol = (symbol or "").strip().split(".")[0]
        if not symbol:
            raise HTTPException(status_code=400, detail="股票代码不能为空")
        name = await data_service.get_stock_name(symbol)
        # 可选：获取最新价
        daily = await data_service.get_stock_daily(symbol=symbol, start=None, end=None)
        latest_price = None
        if daily and len(daily) > 0:
            last_rec = daily[-1]
            latest_price = last_rec.get("收盘") or last_rec.get("close")
            if latest_price is not None:
                latest_price = float(latest_price)
        return api_success(
            data={
                "symbol": symbol,
                "name": name or f"股票{symbol}",
                "latest_price": latest_price,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_stock_info 异常 symbol=%s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/funds")
async def get_fund_list(limit: int = Query(100, ge=1, le=500)) -> dict:
    """获取基金列表"""
    try:
        data = await data_service.get_fund_list(limit=limit)
        return api_success(data={"data": data, "total": len(data)})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_fund_list 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{symbol}/daily")
async def get_stock_daily(
    symbol: str,
    start: Optional[str] = Query(None, description="开始日期 YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="结束日期 YYYY-MM-DD"),
) -> dict:
    """获取股票日线数据"""
    try:
        data = await data_service.get_stock_daily(symbol=symbol, start=start, end=end)
        return api_success(data={"data": data, "symbol": symbol})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_stock_daily 异常 symbol=%s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/{symbol}/daily")
async def get_index_daily(
    symbol: str = "000001",
    start: Optional[str] = Query(None, description="开始日期"),
    end: Optional[str] = Query(None, description="结束日期"),
) -> dict:
    """获取指数日线数据"""
    try:
        data = await data_service.get_index_daily(symbol=symbol, start=start, end=end)
        return api_success(data={"data": data, "symbol": symbol})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_index_daily 异常 symbol=%s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=str(e))
