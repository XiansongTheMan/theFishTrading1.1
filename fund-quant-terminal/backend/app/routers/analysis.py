# =====================================================
# 投资组合分析 API
# POST /api/analyze-portfolio
# =====================================================

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.response import api_success
from app.services.portfolio_analyzer import PortfolioAnalyzer, get_portfolio_analyzer
from app.utils.logger import logger
from pydantic import BaseModel, Field

router = APIRouter(tags=["投资组合分析"])


@router.get("/analyze-portfolio/health")
async def analyze_portfolio_health() -> dict:
    """调试用：确认 analysis 路由已挂载"""
    return {"ok": True, "route": "/api/analyze-portfolio"}


class AnalyzePortfolioRequest(BaseModel):
    """投资组合分析请求"""

    user_id: str = Field(default="default", description="用户 ID")
    model_type: str | None = Field(None, description="LLM 提供商 grok/qwen，不传则用配置的主 Agent")


@router.post("/analyze-portfolio")
async def analyze_portfolio(
    body: AnalyzePortfolioRequest | None = None,
    analyzer: PortfolioAnalyzer = Depends(get_portfolio_analyzer),
) -> dict:
    """
    对指定用户投资组合进行 AI 分析。

    聚合资产汇总、近期新闻、市场快照、风险偏好，调用 LLM 生成投资建议。
    返回解析后的 JSON 分析结果及原始上下文。
    """
    try:
        b = body or AnalyzePortfolioRequest()
        user_id = (b.user_id or "default").strip() or "default"
        model_type = (b.model_type or "").strip() if b.model_type else None
        result = await analyzer.analyze_portfolio(user_id=user_id, model_type=model_type)
        return api_success(data=result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("analyze_portfolio error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
