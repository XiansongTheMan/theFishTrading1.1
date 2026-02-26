# =====================================================
# 资产相关请求/响应模型
# =====================================================

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AssetItem(BaseModel):
    """单条资产"""

    symbol: str
    name: str
    quantity: float
    cost_price: Optional[float] = None
    current_price: Optional[float] = None
    asset_type: str = "fund"


class AssetsUpdateRequest(BaseModel):
    """资产更新请求（交易执行后）"""

    capital: Optional[float] = Field(None, description="当前现金/总资金")
    assets: Optional[List[Dict[str, Any]]] = Field(None, description="持仓列表")


class HoldingTransactionCreate(BaseModel):
    """持仓交易（买入/卖出）"""

    symbol: str = Field(..., description="标的代码")
    asset_type: str = Field("fund", description="资产类型: fund/stock")
    date: str = Field(..., description="交易日期 YYYY-MM-DD")
    type: str = Field(..., description="类型: buy/sell")
    quantity: float = Field(..., gt=0, description="数量/份额")
    price: float = Field(..., gt=0, description="单价")
    amount: Optional[float] = Field(None, description="金额（可选，缺省为 quantity * price）")
