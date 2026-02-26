# =====================================================
# 数据相关 API 的请求/响应模型
# =====================================================

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DataFetchRequest(BaseModel):
    """数据拉取请求 - /api/data/fetch"""

    fund_code: str = Field(default="", description="基金代码，data_type=list 时可空")
    data_type: str = Field(default="nav", description="数据类型: nav|list|info")


class DataFetchResponse(BaseModel):
    """数据拉取响应"""

    fund_code: Optional[str] = None
    data_type: str = "nav"
    data: Any = None
    total: Optional[int] = None


class DataHistoryRequest(BaseModel):
    """历史数据请求 - /api/data/history"""

    fund_code: str = Field(..., description="基金代码")
    start_date: Optional[str] = Field(None, description="开始日期 YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="结束日期 YYYY-MM-DD")
    limit: int = Field(default=100, ge=1, le=1000, description="返回条数")


class FundNavItem(BaseModel):
    """基金净值单条记录"""

    date: str
    nav: float
    cumulative_nav: Optional[float] = None
    daily_return: Optional[float] = None
