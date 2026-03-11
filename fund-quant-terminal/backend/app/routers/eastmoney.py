# =====================================================
# 东方财富 API 路由
# POST /api/eastmoney/test 测试 7*24 全球直播
# =====================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.eastmoney_service import EastMoneyService
from app.utils.logger import logger

router = APIRouter()
_eastmoney_service: Optional[EastMoneyService] = None


def _get_service() -> EastMoneyService:
    global _eastmoney_service
    if _eastmoney_service is None:
        _eastmoney_service = EastMoneyService()
    return _eastmoney_service


class EastMoneyTestRequest(BaseModel):
    """东方财富测试请求"""

    limit: int = Field(default=10, ge=1, le=100, description="返回条数")
    save_to_db: bool = Field(default=False, description="是否将解析结果保存至 decision_logs")


@router.post(
    "/test",
    summary="东方财富 7*24 全球直播测试",
    description="从 RSSHub 拉取东方财富 7*24 直播，解析为统一格式，可选保存至 decision_logs。",
    responses={
        200: {"description": "成功，返回 type、data、parsed、saved_count"},
        500: {"description": "服务异常"},
    },
)
async def eastmoney_test(
    req: EastMoneyTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """
    测试东方财富 7*24 全球直播。返回格式与 wallstreetcn lives 一致，便于前端复用时间线展示。
    """
    try:
        service = _get_service()
        raw, parsed = await service.fetch_and_parse(limit=req.limit)

        saved_count = 0
        if req.save_to_db and parsed:
            saved_count = await service.save_to_decision_logs(db, parsed, type_="live:7x24")

        data = {"type": "live:7x24", "data": raw}
        if parsed:
            data["parsed"] = parsed
        if saved_count > 0:
            data["saved_count"] = saved_count

        return api_success(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("eastmoney_test 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
