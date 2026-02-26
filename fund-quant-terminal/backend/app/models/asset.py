# =====================================================
# 资产模型
# 记录持仓与资产配置
# =====================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssetBase(BaseModel):
    """资产基础模型"""

    # 标的代码
    symbol: str = Field(..., description="标的代码")
    # 标的名称
    name: str = Field(..., description="标的名称")
    # 数量/份额
    quantity: float = Field(..., ge=0, description="持有数量")
    # 成本均价
    cost_price: Optional[float] = Field(None, description="成本均价")
    # 当前价格（可选，可实时更新）
    current_price: Optional[float] = Field(None, description="当前价格")
    # 资产类型：fund / stock
    asset_type: str = Field(..., description="资产类型: fund/stock")
    # 备注
    remark: Optional[str] = Field(None, description="备注")


class AssetCreate(AssetBase):
    """创建资产的请求模型"""

    pass


class AssetInDB(AssetBase):
    """数据库中的资产模型（含 ID 与时间戳）"""

    id: Optional[str] = Field(None, alias="_id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class Asset(AssetInDB):
    """API 返回的资产模型"""

    @property
    def market_value(self) -> Optional[float]:
        """市值 = 数量 * 当前价格"""
        if self.current_price is not None:
            return round(self.quantity * self.current_price, 2)
        return None
