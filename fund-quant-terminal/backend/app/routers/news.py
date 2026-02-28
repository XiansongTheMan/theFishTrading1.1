# =====================================================
# 新闻 API 路由
# GET /api/news/fetch - 抓取 RSS 并返回新闻列表
# GET /api/news/list - 分页列表，支持 keyword、page、limit、sentiment
# =====================================================

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.grok_decision import generate_grok_prompt
from app.services.news_fetch import NewsFetchService, _compute_sentiment
from app.utils.logger import logger


def _get_sentiment_score(doc: dict) -> float:
    """优先使用 DB 的 sentiment，缺失时现场计算"""
    if doc.get("sentiment") is not None:
        return float(doc["sentiment"])
    text = f"{doc.get('title') or ''} {doc.get('content_summary') or ''}"
    return _compute_sentiment(text)


class GrokDecisionRequest(BaseModel):
    fund_code: str = Field("", description="基金代码，空则为全局/市场")
    include_news: bool = Field(True, description="是否在响应中包含新闻摘要列表")
    news_links: Optional[list[str]] = Field(None, description="指定新闻 link 列表，优先于 fund_code 查询")


class BatchGrokRequest(BaseModel):
    news_links: list[str] = Field(..., min_length=1, description="批量新闻 link 列表，聚合生成综合 Grok 决策提示")


router = APIRouter()
news_service = NewsFetchService()


async def _get_news_list(
    fund_code: Optional[str],
    days: int,
    refresh: bool,
    db: AsyncIOMotorDatabase,
) -> list:
    """共享逻辑：抓取或读取新闻列表"""
    if refresh:
        items = await news_service.fetch_and_save(db, fund_code=fund_code, days=days)
        if not items:
            items = await news_service.get_news(db, fund_code=fund_code, days=days)
    else:
        items = await news_service.get_news(db, fund_code=fund_code, days=days)
    items.sort(key=lambda x: x.get("pub_date") or x.get("created_at") or "", reverse=True)
    result = []
    for d in items:
        d = dict(d)
        for k in ("pub_date", "created_at"):
            if k in d and d[k] and hasattr(d[k], "isoformat"):
                d[k] = d[k].isoformat()
        d.pop("_id", None)
        result.append(d)
    return result


def _parse_sort(s: Optional[str]) -> list:
    """解析 sort=field,direction，如 pub_date,-1 或 sentiment,1"""
    if not s or not isinstance(s, str) or "," not in s:
        return [("pub_date", -1)]
    parts = s.strip().split(",", 1)
    field = (parts[0] or "pub_date").strip()
    if field not in ("pub_date", "sentiment", "created_at"):
        field = "pub_date"
    try:
        direction = int(parts[1].strip()) if len(parts) > 1 else -1
    except (ValueError, TypeError):
        direction = -1
    if direction not in (1, -1):
        direction = -1
    return [(field, direction)]


@router.get("/list")
async def news_list(
    fund_code: Optional[str] = Query(None, description="基金代码，可选"),
    days: int = Query(7, ge=1, le=30, description="返回最近 N 天的新闻"),
    keyword: Optional[str] = Query(None, description="关键词搜索（标题、摘要）"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    sort: Optional[str] = Query(None, description="排序，如 pub_date,-1 或 sentiment,1"),
    refresh: bool = Query(False, description="是否从 RSS 重新抓取后再查"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """
    分页新闻列表，从 news_raw 查询，按 pub_date 倒序。
    支持 keyword 全文搜索；缺失时补充 sentiment_score。
    """
    try:
        if refresh:
            await news_service.fetch_and_save(db, fund_code=fund_code, days=days)

        items, total = await news_service.get_news_paginated(
            db,
            fund_code=fund_code,
            days=days,
            keyword=keyword,
            page=page,
            limit=limit,
            sort=_parse_sort(sort),
        )

        for d in items:
            score = _get_sentiment_score(d)
            d["sentiment_score"] = score
            if "sentiment" not in d or d.get("sentiment") is None:
                d["sentiment"] = score

        positives = sum(1 for d in items if d.get("sentiment_score", 0) > 0.3)
        neutrals = sum(1 for d in items if -0.3 <= (d.get("sentiment_score") or 0) <= 0.3)
        negatives = sum(1 for d in items if (d.get("sentiment_score") or 0) < -0.3)
        avg_sentiment = round(sum(d.get("sentiment_score", 0) or 0 for d in items) / len(items), 2) if items else 0

        return api_success(
            data={
                "items": items,
                "total": total,
                "page": page,
                "limit": limit,
                "sentiment_summary": {
                    "positive": positives,
                    "neutral": neutrals,
                    "negative": negatives,
                    "avg": avg_sentiment,
                },
            },
            message=f"共 {total} 条",
        )
    except Exception as e:
        logger.exception("news_list 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch")
async def news_fetch(
    fund_code: Optional[str] = Query(None, description="基金代码，可选"),
    days: int = Query(3, ge=1, le=30, description="返回最近 N 天的新闻"),
    refresh: bool = Query(True, description="是否从 RSS 重新抓取；False 时仅从 DB 读取"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """抓取 RSS 并返回新闻列表"""
    try:
        result = await _get_news_list(fund_code, days, refresh, db)
        return api_success(data=result, message=f"共抓取 {len(result)} 条新闻")
    except Exception as e:
        logger.exception("news_fetch 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


NEWS_COLLECTION = "news_raw"


@router.get("/sentiment-trend")
async def news_sentiment_trend(
    fund_code: str = Query("", description="基金代码，空则为市场整体"),
    days: int = Query(14, ge=1, le=60, description="最近 N 天"),
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """按日聚合情绪得分趋势，供 ECharts 折线图使用"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    match_q: dict = {"pub_date": {"$gte": cutoff}}
    if fund_code and fund_code.strip():
        fc = fund_code.strip()
        match_q["$or"] = [
            {"fund_code": fc},
            {"fund_code": {"$in": [None, ""]}},
            {"fund_code": {"$exists": False}},
        ]

    pipeline = [
        {"$match": match_q},
        {"$addFields": {"sentiment_val": {"$ifNull": ["$sentiment", 0]}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$pub_date"}},
                "avg_sentiment": {"$avg": "$sentiment_val"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    cursor = db[NEWS_COLLECTION].aggregate(pipeline)
    items = []
    async for doc in cursor:
        items.append({"date": doc["_id"], "avg_sentiment": round(float(doc.get("avg_sentiment", 0)), 2), "count": doc.get("count", 0)})
    return api_success(data={"items": items, "fund_code": fund_code or "market"}, message="OK")


@router.post("/batch-grok")
async def news_batch_grok(
    body: BatchGrokRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """批量聚合多条新闻生成综合 Grok 决策提示词"""
    try:
        prompt, news_summary = await generate_grok_prompt(
            "",
            db,
            include_news_list=True,
            custom_news_links=body.news_links,
        )
        return api_success(
            data={"prompt": prompt, "news_summary": news_summary},
            message=f"已聚合 {len(body.news_links)} 条新闻生成综合决策提示",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("news_batch_grok 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grok-decision")
async def news_grok_decision(
    body: GrokDecisionRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """生成 Grok 决策提示词：基于基金或指定新闻，返回可直接复制的完整提示 + 新闻摘要"""
    try:
        prompt, news_summary = await generate_grok_prompt(
            body.fund_code or "",
            db,
            include_news_list=body.include_news,
            custom_news_links=body.news_links,
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
