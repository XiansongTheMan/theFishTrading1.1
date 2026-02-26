# =====================================================
# 数据获取服务
# AKShare / Tushare 集成，异步执行阻塞调用
# =====================================================

import asyncio
from typing import Any, Dict, List, Optional

from app.config import settings
from app.utils.logger import logger


class DataFetcherService:
    """金融数据获取服务 - 支持基金净值、基金列表、Tushare 基金信息"""

    def __init__(self) -> None:
        self._ts_pro = None
        if settings.TUSHARE_TOKEN:
            try:
                import tushare as ts

                ts.set_token(settings.TUSHARE_TOKEN)
                self._ts_pro = ts.pro_api()
                logger.info("Tushare pro_api 初始化成功")
            except Exception as e:
                logger.warning("Tushare 初始化失败: %s", e)
                self._ts_pro = None

    async def get_fund_nav(self, fund_code: str) -> List[Dict[str, Any]]:
        """
        获取基金净值走势
        使用 akshare fund_open_fund_info_em(indicator="单位净值走势")
        """
        def _fetch() -> List[Dict[str, Any]]:
            try:
                import akshare as ak
                df = ak.fund_open_fund_info_em(symbol=fund_code.strip(), indicator="单位净值走势")
                if df is None or df.empty:
                    return []
                # 统一列名: 净值日期->date, 单位净值->nav, 日增长率->daily_return
                col_map = {"净值日期": "date", "单位净值": "nav", "日增长率": "daily_return"}
                for old, new in col_map.items():
                    if old in df.columns:
                        df = df.rename(columns={old: new})
                return df.to_dict(orient="records")
            except Exception as e:
                logger.exception("get_fund_nav akshare 异常 fund_code=%s: %s", fund_code, e)
                raise

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.error("get_fund_nav 执行失败 fund_code=%s: %s", fund_code, e)
            raise

    async def get_fund_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取基金列表
        优先 akshare fund_name_em，失败时尝试 tushare fund_basic
        """
        def _akshare_fetch() -> List[Dict[str, Any]]:
            import akshare as ak
            df = ak.fund_name_em()
            if df is None or df.empty:
                return []
            df = df.head(limit)
            if "基金代码" in df.columns:
                df = df.rename(columns={"基金代码": "code", "基金简称": "name", "基金类型": "type"})
            return df.to_dict(orient="records")

        def _tushare_fetch() -> List[Dict[str, Any]]:
            if not self._ts_pro:
                return []
            df = self._ts_pro.fund_basic(market="E", limit=limit)
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")

        try:
            result = await asyncio.to_thread(_akshare_fetch)
            if result:
                return result
        except Exception as e:
            logger.warning("get_fund_list akshare 失败: %s，尝试 tushare", e)

        if self._ts_pro:
            try:
                return await asyncio.to_thread(_tushare_fetch)
            except Exception as e:
                logger.warning("get_fund_list tushare 失败: %s", e)

        return [
            {"code": "000001", "name": "华夏成长混合", "type": "混合型"},
            {"code": "110011", "name": "易方达中小盘", "type": "混合型"},
        ][:limit]

    async def get_tushare_fund_info(self, fund_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取 Tushare 基金信息
        需配置 TUSHARE_TOKEN
        """
        if not self._ts_pro:
            logger.warning("get_tushare_fund_info: TUSHARE_TOKEN 未配置")
            return []

        def _fetch() -> List[Dict[str, Any]]:
            # fund_basic 获取基金基础信息
            df = self._ts_pro.fund_basic(
                market="E",
                limit=500 if not fund_code else 10,
            )
            if df is None or df.empty:
                return []
            if fund_code:
                df = df[df["ts_code"].astype(str).str.replace(".OF", "").str.contains(fund_code, na=False)]
            return df.to_dict(orient="records")

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.exception("get_tushare_fund_info 异常: %s", e)
            raise

    async def get_fund_nav_history(
        self,
        fund_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取基金净值历史，支持日期过滤与条数限制
        """
        records = await self.get_fund_nav(fund_code)
        if not records:
            return []

        filtered = []
        for r in records:
            date_val = r.get("date") or r.get("净值日期")
            if not date_val:
                continue
            d = str(date_val)
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            filtered.append(r)
            if len(filtered) >= limit:
                break
        return filtered

    async def get_stock_daily(
        self, symbol: str, start: Optional[str] = None, end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取股票日线数据"""
        def _fetch() -> List[Dict[str, Any]]:
            import akshare as ak
            code = symbol.split(".")[0] if "." in symbol else symbol
            df = ak.stock_zh_a_hist(symbol=code, period="daily")
            if df is None or df.empty:
                return []
            if start:
                df = df[df["日期"] >= start]
            if end:
                df = df[df["日期"] <= end]
            return df.to_dict(orient="records")

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.warning("get_stock_daily 失败 symbol=%s: %s", symbol, e)
            return []

    async def get_index_daily(
        self, symbol: str = "000001", start: Optional[str] = None, end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指数日线数据"""
        def _fetch() -> List[Dict[str, Any]]:
            import akshare as ak
            sym = f"sh{symbol}" if symbol.startswith("0") else symbol
            df = ak.stock_zh_index_daily(symbol=sym)
            if df is None or df.empty:
                return []
            if start:
                df = df[df["date"] >= start]
            if end:
                df = df[df["date"] <= end]
            return df.to_dict(orient="records")

        try:
            return await asyncio.to_thread(_fetch)
        except Exception as e:
            logger.warning("get_index_daily 失败 symbol=%s: %s", symbol, e)
            return []
