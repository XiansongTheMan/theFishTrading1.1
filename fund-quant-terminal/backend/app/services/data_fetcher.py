# =====================================================
# 数据获取服务
# AKShare / Tushare 集成，异步执行阻塞调用
# tenacity 重试、超时、耗时日志、异常兜底
# =====================================================

import asyncio
import re
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.logger import logger

T = TypeVar("T")
AKSHARE_TIMEOUT = 30
AKSHARE_RATE_LIMIT_SEC = 0.5
_last_akshare_call = 0.0


def _rate_limit_sync() -> None:
    """同步环境下的限流：距上次调用不足 AKSHARE_RATE_LIMIT_SEC 时 sleep"""
    global _last_akshare_call
    import time as _t

    now = _t.monotonic()
    elapsed = now - _last_akshare_call
    if elapsed < AKSHARE_RATE_LIMIT_SEC and _last_akshare_call > 0:
        _t.sleep(AKSHARE_RATE_LIMIT_SEC - elapsed)
    _last_akshare_call = _t.monotonic()


def akshare_retry(func: Callable[..., T]) -> Callable[..., T]:
    """AKShare 调用装饰器：重试 3 次、指数退避、限流、捕获异常"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        _rate_limit_sync()
        return func(*args, **kwargs)

    return wrapper


async def _run_akshare(
    fn: Callable[[], T],
    op_name: str,
) -> T:
    """执行 AKShare 同步函数：超时、耗时日志、异常兜底"""
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(asyncio.to_thread(fn), timeout=AKSHARE_TIMEOUT)
        duration = time.monotonic() - start
        logger.info("[%s] request completed in %.2fs", op_name, duration)
        return result
    except asyncio.TimeoutError:
        logger.warning("[%s] timeout after %.1fs", op_name, time.monotonic() - start)
        raise
    except Exception as e:
        logger.exception("[%s] failed after %.2fs: %s", op_name, time.monotonic() - start, e)
        raise


def _create_ts_pro(token: str):
    """用指定 token 创建 tushare pro_api 实例"""
    if not token or not token.strip():
        return None
    try:
        import tushare as ts

        ts.set_token(token.strip())
        return ts.pro_api()
    except Exception as e:
        logger.warning("Tushare 初始化失败: %s", e)
        return None


class DataFetcherService:
    """金融数据获取服务 - 支持基金净值、基金列表，可切换 akshare/tushare 为主数据源"""

    def __init__(self) -> None:
        self._tushare_tokens: list[dict] = []
        self._primary_source: str = "tushare"
        self._effective_source: str = "tushare"
        init_token = settings.TUSHARE_TOKEN or ""
        if init_token:
            self._tushare_tokens = [{"token": init_token, "remark": "主", "order": 0}]

    def set_primary_data_source(self, src: str) -> None:
        """设置主要金融数据源：akshare 或 tushare"""
        if src in ("akshare", "tushare"):
            self._primary_source = src
            self._effective_source = src
            logger.info("主要数据源已设为: %s", src)

    def get_effective_data_source(self) -> str:
        """获取当前实际使用的数据源"""
        return self._effective_source

    def update_tushare_tokens(self, tushare_list: list[dict]) -> None:
        """运行时更新 Tushare Token 列表，按 order 排序后依次尝试"""
        self._tushare_tokens = sorted(
            [{"token": (it.get("token") or "").strip(), "remark": it.get("remark", ""), "order": it.get("order", i)} for i, it in enumerate(tushare_list or []) if (it.get("token") or "").strip()],
            key=lambda x: x.get("order", 0),
        )
        logger.info("Tushare tokens 已更新，共 %d 个", len(self._tushare_tokens))

    async def _run_with_tushare(self, fn, op_name: str = "tushare"):
        """依次用 tokens 执行 fn(pro)，直到成功或全部失败"""
        last_err = None
        for i, item in enumerate(self._tushare_tokens):
            pro = _create_ts_pro(item.get("token", ""))
            if not pro:
                continue
            try:
                return await asyncio.to_thread(fn, pro)
            except Exception as e:
                last_err = e
                logger.warning("[%s] token[%d] 失败: %s，尝试下一个", op_name, i, e)
        if last_err:
            raise last_err
        return None

    async def get_fund_name(self, fund_code: str) -> Optional[str]:
        """
        根据基金代码获取真实基金名称
        优先 fund_individual_basic_info_xq，失败时从 fund_list 查找
        """
        @akshare_retry
        def _fetch() -> Optional[str]:
            import akshare as ak

            df = ak.fund_individual_basic_info_xq(symbol=fund_code.strip())
            if df is not None and not df.empty:
                cols = list(df.columns)
                if len(cols) >= 2:
                    key_col = cols[0] if "item" in str(cols[0]).lower() or "名称" in str(cols[0]) else cols[0]
                    val_col = cols[1]
                    for _, r in df.iterrows():
                        k = str(r.get(key_col, "")).strip()
                        if k in ("基金名称", "基金简称", "name"):
                            v = r.get(val_col)
                            if v and str(v).strip():
                                return str(v).strip()
                for col in ["基金名称", "name", "基金简称"]:
                    if col in df.columns:
                        val = df[col].iloc[0]
                        if val and str(val).strip():
                            return str(val).strip()
            return None

        try:
            name = await _run_akshare(_fetch, "get_fund_name")
            if name:
                return name
        except Exception as e:
            logger.debug("get_fund_name 异常 fund_code=%s: %s", fund_code, e)

        # 降级：从 fund_list 查找
        try:
            fund_list = await self.get_fund_list(limit=20000)
            code_clean = fund_code.strip().replace(".OF", "")
            for f in fund_list:
                c = str(f.get("code") or f.get("基金代码") or "")
                if c.replace(".OF", "").strip() == code_clean:
                    return str(f.get("name") or f.get("基金简称") or "").strip() or None
        except Exception as e:
            logger.debug("get_fund_name fund_list fallback 失败: %s", e)
        return None

    async def get_stock_name(self, symbol: str) -> Optional[str]:
        """
        根据股票代码获取真实股票名称
        使用 akshare stock_info_a_code_name
        """
        @akshare_retry
        def _fetch() -> Optional[str]:
            import akshare as ak

            df = ak.stock_info_a_code_name()
            if df is None or df.empty:
                return None
            code_col = "code" if "code" in df.columns else "代码"
            name_col = "name" if "name" in df.columns else "名称"
            sym = symbol.strip().split(".")[0].zfill(6)
            for _, r in df.iterrows():
                c = str(r.get(code_col, "")).zfill(6)
                if c == sym:
                    return str(r.get(name_col, "")).strip() or None
            return None

        try:
            return await _run_akshare(_fetch, "get_stock_name")
        except Exception as e:
            logger.debug("get_stock_name 异常: %s", e)
            return None

    async def get_fund_sector(self, fund_code: str) -> Optional[str]:
        """
        获取基金所属板块（行业配置中占比最高的行业）
        使用 akshare fund_portfolio_industry_allocation_em
        """
        @akshare_retry
        def _fetch() -> Optional[str]:
            import akshare as ak

            code = fund_code.strip().split(".")[0]
            year = str(datetime.now().year)
            df = ak.fund_portfolio_industry_allocation_em(symbol=code, date=year)
            if df is None or df.empty:
                return None
            col = "行业类别" if "行业类别" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
            if col:
                return str(df[col].iloc[0]).strip() or None
            return None

        try:
            return await _run_akshare(_fetch, "get_fund_sector")
        except Exception as e:
            logger.debug("get_fund_sector 异常: %s", e)
            return None

    async def get_stock_sector(self, symbol: str) -> Optional[str]:
        """
        获取股票所属行业
        使用 akshare stock_individual_info_em
        """
        @akshare_retry
        def _fetch() -> Optional[str]:
            import akshare as ak

            code = symbol.strip().split(".")[0].zfill(6)
            df = ak.stock_individual_info_em(symbol=code)
            if df is None or df.empty:
                return None
            cols = list(df.columns)
            if len(cols) >= 2:
                key_col, val_col = cols[0], cols[1]
                for _, r in df.iterrows():
                    k = str(r.get(key_col, "")).strip()
                    if k in ("行业", "所属行业", "证监会行业"):
                        v = r.get(val_col)
                        if v and str(v).strip():
                            return str(v).strip()
            return None

        try:
            return await _run_akshare(_fetch, "get_stock_sector")
        except Exception as e:
            logger.debug("get_stock_sector 异常: %s", e)
            return None

    async def get_fund_nav(self, fund_code: str) -> List[Dict[str, Any]]:
        """
        获取基金净值走势
        按 primary_data_source 先尝试主数据源，失败时切换另一数据源
        """
        code = fund_code.strip().split(".")[0].zfill(6)
        ts_code = code + ".OF"

        @akshare_retry
        def _akshare_fetch() -> List[Dict[str, Any]]:
            import akshare as ak

            df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            if df is None or df.empty:
                records: List[Dict[str, Any]] = []
                max_date = None
            else:
                col_map = {"净值日期": "date", "单位净值": "nav", "日增长率": "daily_return"}
                for old, new in col_map.items():
                    if old in df.columns:
                        df = df.rename(columns={old: new})
                records = df.to_dict(orient="records")
                max_date = df["date"].max() if "date" in df.columns else None
                if max_date is not None and hasattr(max_date, "date") and callable(getattr(max_date, "date")):
                    max_date = max_date.date()
            try:
                daily_df = ak.fund_open_fund_daily_em()
                if daily_df is not None and not daily_df.empty and "基金代码" in daily_df.columns:
                    nav_cols = [c for c in daily_df.columns if isinstance(c, str) and c.endswith("-单位净值")]
                    if nav_cols:
                        latest_col = nav_cols[0]
                        date_str = latest_col.replace("-单位净值", "").strip()
                        if re.match(r"\d{4}-\d{2}-\d{2}", date_str):
                            fund_row = daily_df[daily_df["基金代码"].astype(str).str.strip() == code]
                            if not fund_row.empty:
                                nav_val = fund_row[latest_col].iloc[0]
                                try:
                                    nav_float = float(nav_val)
                                    if nav_float == nav_float:
                                        new_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                                        if max_date is None or new_date > max_date:
                                            daily_ret = None
                                            if "日增长率" in daily_df.columns:
                                                dr = fund_row["日增长率"].iloc[0]
                                                try:
                                                    daily_ret = float(dr) if dr == dr else None
                                                except (TypeError, ValueError):
                                                    pass
                                            records.append({"date": new_date, "nav": nav_float, "daily_return": daily_ret})
                                except (TypeError, ValueError):
                                    pass
            except Exception as e:
                logger.debug("get_fund_nav daily fallback 跳过: %s", e)
            return records

        def _tushare_fetch(pro) -> List[Dict[str, Any]]:
            df = pro.fund_nav(ts_code=ts_code, start_date="20000101", end_date=datetime.now().strftime("%Y%m%d"))
            if df is None or df.empty:
                return []
            col_map = {"end_date": "date", "unit_nav": "nav"}
            for old, new in col_map.items():
                if old in df.columns:
                    df = df.rename(columns={old: new})
            if "daily_return" not in df.columns and "daily_growth_rate" in df.columns:
                df = df.rename(columns={"daily_growth_rate": "daily_return"})
            return df.to_dict(orient="records")

        first = self._primary_source
        if first == "akshare":
            try:
                result = await _run_akshare(_akshare_fetch, "get_fund_nav")
                if result:
                    self._effective_source = "akshare"
                    return result
            except Exception as e:
                logger.warning("get_fund_nav akshare 失败: %s，尝试 tushare", e)
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_fund_nav")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_fund_nav tushare 失败: %s", e)
        else:
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_fund_nav")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_fund_nav tushare 失败: %s，尝试 akshare", e)
            try:
                result = await _run_akshare(_akshare_fetch, "get_fund_nav")
                if result:
                    self._effective_source = "akshare"
                    return result
            except Exception as e:
                logger.warning("get_fund_nav akshare 失败: %s", e)
        raise RuntimeError(f"get_fund_nav 两个数据源均失败 fund_code={fund_code}")

    async def get_fund_list(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取基金列表
        按 primary_data_source 先尝试主数据源，失败时切换另一数据源
        """
        @akshare_retry
        def _akshare_fetch() -> List[Dict[str, Any]]:
            import akshare as ak

            df = ak.fund_name_em()
            if df is None or df.empty:
                return []
            df = df.head(limit)
            if "基金代码" in df.columns:
                df = df.rename(columns={"基金代码": "code", "基金简称": "name", "基金类型": "type"})
            return df.to_dict(orient="records")

        def _tushare_fetch(pro) -> List[Dict[str, Any]]:
            df = pro.fund_basic(market="E", limit=limit)
            if df is None or df.empty:
                return []
            return df.to_dict(orient="records")

        first, second = ("akshare", "tushare") if self._primary_source == "akshare" else ("tushare", "akshare")

        if first == "akshare":
            try:
                result = await _run_akshare(_akshare_fetch, "get_fund_list")
                if result:
                    self._effective_source = "akshare"
                    return result
            except Exception as e:
                logger.warning("get_fund_list akshare 失败: %s，尝试 tushare", e)
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_fund_list")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_fund_list tushare 失败: %s", e)
        else:
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_fund_list")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_fund_list tushare 失败: %s，尝试 akshare", e)
            try:
                result = await _run_akshare(_akshare_fetch, "get_fund_list")
                if result:
                    self._effective_source = "akshare"
                    return result
            except Exception as e:
                logger.warning("get_fund_list akshare 失败: %s", e)

        return [
            {"code": "000001", "name": "华夏成长混合", "type": "混合型"},
            {"code": "110011", "name": "易方达中小盘", "type": "混合型"},
        ][:limit]

    async def get_tushare_fund_info(self, fund_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取 Tushare 基金信息
        需配置 Tushare Token，支持多 Token 依次尝试
        """

        def _fetch(pro) -> List[Dict[str, Any]]:
            df = pro.fund_basic(market="E", limit=500 if not fund_code else 10)
            if df is None or df.empty:
                return []
            if fund_code:
                df = df[df["ts_code"].astype(str).str.replace(".OF", "").str.contains(fund_code, na=False)]
            return df.to_dict(orient="records")

        try:
            out = await self._run_with_tushare(_fetch, "get_tushare_fund_info")
            return out or []
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
        """获取股票日线数据，按 primary_data_source 主数据源优先，失败时切换"""
        code = symbol.split(".")[0] if "." in symbol else symbol
        ts_code = code + ".SH" if code.startswith("6") else code + ".SZ"

        @akshare_retry
        def _akshare_fetch() -> List[Dict[str, Any]]:
            import akshare as ak

            df = ak.stock_zh_a_hist(symbol=code, period="daily")
            if df is None or df.empty:
                return []
            if start:
                df = df[df["日期"] >= start]
            if end:
                df = df[df["日期"] <= end]
            return df.to_dict(orient="records")

        def _tushare_fetch(pro) -> List[Dict[str, Any]]:
            s = (start or "20000101").replace("-", "")
            e = (end or datetime.now().strftime("%Y%m%d")).replace("-", "")
            df = pro.daily(ts_code=ts_code, start_date=s, end_date=e)
            if df is None or df.empty:
                return []
            if "trade_date" in df.columns:
                df = df.rename(columns={"trade_date": "日期", "close": "收盘", "vol": "成交量"})
            return df.to_dict(orient="records")

        first = self._primary_source
        if first == "akshare":
            try:
                result = await _run_akshare(_akshare_fetch, "get_stock_daily")
                if result is not None:
                    self._effective_source = "akshare"
                    return result or []
            except Exception as e:
                logger.warning("get_stock_daily akshare 失败: %s，尝试 tushare", e)
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_stock_daily")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_stock_daily tushare 失败: %s", e)
        else:
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_stock_daily")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_stock_daily tushare 失败: %s，尝试 akshare", e)
            try:
                result = await _run_akshare(_akshare_fetch, "get_stock_daily")
                if result is not None:
                    self._effective_source = "akshare"
                    return result or []
            except Exception as e:
                logger.warning("get_stock_daily akshare 失败: %s", e)
        return []

    async def get_index_daily(
        self, symbol: str = "000001", start: Optional[str] = None, end: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """获取指数日线数据，按 primary_data_source 主数据源优先，失败时切换"""
        sym = f"sh{symbol}" if symbol.startswith("0") else symbol
        ts_code = f"000001.SH" if symbol == "000001" or symbol.startswith("0") else f"{symbol}.SH"

        @akshare_retry
        def _akshare_fetch() -> List[Dict[str, Any]]:
            import akshare as ak

            df = ak.stock_zh_index_daily(symbol=sym)
            if df is None or df.empty:
                return []
            if start:
                df = df[df["date"] >= start]
            if end:
                df = df[df["date"] <= end]
            return df.to_dict(orient="records")

        def _tushare_fetch(pro) -> List[Dict[str, Any]]:
            s = (start or "20000101").replace("-", "")
            e = (end or datetime.now().strftime("%Y%m%d")).replace("-", "")
            df = pro.index_daily(ts_code=ts_code, start_date=s, end_date=e)
            if df is None or df.empty:
                return []
            if "trade_date" in df.columns:
                df = df.rename(columns={"trade_date": "date"})
            return df.to_dict(orient="records")

        first = self._primary_source
        if first == "akshare":
            try:
                result = await _run_akshare(_akshare_fetch, "get_index_daily")
                if result is not None:
                    self._effective_source = "akshare"
                    return result or []
            except Exception as e:
                logger.warning("get_index_daily akshare 失败: %s，尝试 tushare", e)
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_index_daily")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_index_daily tushare 失败: %s", e)
        else:
            try:
                out = await self._run_with_tushare(_tushare_fetch, "get_index_daily")
                if out:
                    self._effective_source = "tushare"
                    return out
            except Exception as e:
                logger.warning("get_index_daily tushare 失败: %s，尝试 akshare", e)
            try:
                result = await _run_akshare(_akshare_fetch, "get_index_daily")
                if result is not None:
                    self._effective_source = "akshare"
                    return result or []
            except Exception as e:
                logger.warning("get_index_daily akshare 失败: %s", e)
        return []
