# =====================================================
# 新闻 API 路由
# GET /api/news/fetch - 抓取 RSS 并返回新闻列表
# =====================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.grok_decision import generate_grok_prompt
from app.services.news_fetch import NewsFetchService
from app.utils.logger import logger


class GrokDecisionRequest(BaseModel):
    fund_code: str = Field(..., description="基金代码")
    include_news: bool = Field(True, description="是否在响应中包含新闻摘要列表")


router = APIRouter()
news_service = NewsFetchService()


@router.get("/fetch")
async def news_fetch(
    fund_code: Optional[str] = Query(None, description="基金代码，可选"),
    days: int = Query(3, ge=1, le=30, description="返回最近 N 天的新闻"),
    refresh: bool = Query(True, description="是否从 RSS 重新抓取；False 时仅从 DB 读取"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """
    抓取东方财富、新浪财经等 RSS 源，写入 news_raw，并返回 JSON 列表（按时间倒序）
    """
    try:
        if refresh:
            items = await news_service.fetch_and_save(db, fund_code=fund_code, days=days)
            # 若 RSS 抓取为空，回退到 DB 已有数据（定时任务或历史抓取）
            if not items:
                items = await news_service.get_news(db, fund_code=fund_code, days=days)
        else:
            items = await news_service.get_news(db, fund_code=fund_code, days=days)
        # 按 pub_date 倒序
        items.sort(
            key=lambda x: x.get("pub_date") or x.get("created_at") or "",
            reverse=True,
        )
        result = []
        for d in items:
            d = dict(d)
            for k in ("pub_date", "created_at"):
                if k in d and d[k] and hasattr(d[k], "isoformat"):
                    d[k] = d[k].isoformat()
            d.pop("_id", None)
            result.append(d)
        return api_success(data=result, message=f"共抓取 {len(result)} 条新闻")
    except Exception as e:
        logger.exception("news_fetch 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grok-decision")
async def news_grok_decision(
    body: GrokDecisionRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """生成 Grok 决策提示词：基于基金最近 72 小时新闻与情绪分析，返回可直接复制的完整提示 + 新闻摘要"""
    try:
        prompt, news_summary = await generate_grok_prompt(
            body.fund_code,
            db,
            include_news_list=body.include_news,
        )
        data = {"prompt": prompt}
        if body.include_news:
            data["news_summary"] = news_summary
        return api_success(data=data, message="已生成决策提示词")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("news_grok_decision 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
