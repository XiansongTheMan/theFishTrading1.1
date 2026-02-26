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
