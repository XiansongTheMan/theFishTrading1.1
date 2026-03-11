# =====================================================
# 投资组合分析 API 响应模型
# 与 fund_analyst_prompt 中的 JSON schema 对应
# =====================================================

from typing import Any, Literal

from pydantic import BaseModel, Field


class AnalysisResultSchema(BaseModel):
    """LLM 分析结果 schema（与 fund_analyst_prompt 约定一致）"""

    fund_code: str = Field(default="", description="6 位基金代码")
    action: Literal["buy", "sell", "hold"] = Field(..., description="建议动作")
    amount: float = Field(default=0.0, ge=0, description="金额 RMB，需 <= total_value * 0.5")
    stop_profit_price: float | None = Field(None, description="止盈价")
    stop_loss_price: float | None = Field(None, description="止损价")
    confidence: int = Field(default=0, ge=0, le=100, description="信心度 0-100")
    risk_level: Literal["low", "medium", "high"] = Field(..., description="风险等级")
    reason: str = Field(default="", description="详细理由，需引用新闻与市场数据")
    disclaimer: str = Field(
        default="本分析仅供参考，不构成投资建议，投资有风险，请自行决策。",
        description="免责声明",
    )
