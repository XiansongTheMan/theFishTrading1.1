# =====================================================
# 第一财经 API 路由
# POST /api/yicai/test 测试快讯（仅官方 RSS，无备用接口）
# =====================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.yicai_service import YicaiService
from app.utils.logger import logger

router = APIRouter()
_yicai_service: Optional[YicaiService] = None


def _get_service() -> YicaiService:
    global _yicai_service
    if _yicai_service is None:
        _yicai_service = YicaiService()
    return _yicai_service


class YicaiTestRequest(BaseModel):
    """第一财经测试请求"""

    limit: int = Field(default=10, ge=1, le=100, description="返回条数")
    save_to_db: bool = Field(default=False, description="是否保存至 decision_logs")


@router.post(
    "/test",
    summary="第一财经快讯测试",
    description="从第一财经官方 RSS 拉取快讯，解析为统一格式。仅此单一接口，无备用源。",
    responses={
        200: {"description": "成功，返回 type、data、parsed、saved_count"},
        500: {"description": "服务异常"},
    },
)
async def yicai_test(
    req: YicaiTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """测试第一财经快讯。返回格式与 eastmoney/cailianshe 一致。"""
    try:
        service = _get_service()
        raw, parsed = await service.fetch_and_parse(limit=req.limit)

        saved_count = 0
        if req.save_to_db and parsed:
            saved_count = await service.save_to_decision_logs(
                db, parsed, type_="kuaixun"
            )

        data = {"type": "kuaixun", "data": raw}
        if parsed:
            data["parsed"] = parsed
        if saved_count > 0:
            data["saved_count"] = saved_count

        return api_success(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("yicai_test 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
