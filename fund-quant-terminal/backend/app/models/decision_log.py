# =====================================================
# 决策日志模型
# 完整决策记录：Grok 输入输出、用户动作、资金变动
# =====================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DecisionLogCreate(BaseModel):
    """创建决策日志请求"""

    timestamp: Optional[datetime] = Field(None, description="时间戳，默认当前")
    grok_prompt: Optional[str] = Field(None, description="Grok 输入提示")
    grok_response: Optional[str] = Field(None, description="Grok 回复/建议")
    user_action: str = Field(..., description="用户动作: buy/sell/hold")
    fund_code: str = Field(..., description="基金代码")
    amount_rmb: Optional[float] = Field(None, ge=0, description="交易金额（元）")
    nav: Optional[float] = Field(None, description="净值")
    fee: Optional[float] = Field(None, ge=0, description="手续费")
    pnl: Optional[float] = Field(None, description="盈亏")
    notes: Optional[str] = Field(None, description="备注")
    capital_before: Optional[float] = Field(None, description="交易前总资产")
    capital_after: Optional[float] = Field(None, description="交易后总资产")


class DecisionLog(DecisionLogCreate):
    """数据库中的决策日志（含 ID）"""

    id: Optional[str] = Field(None, description="文档 ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
