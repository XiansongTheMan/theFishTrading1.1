# =====================================================
# 财联社 API 路由
# POST /api/cailianshe/test 测试电报快讯（加红、提醒、港美股、公司、基金、看板）
# =====================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.cailianshe_service import CailiansheService
from app.utils.logger import logger

router = APIRouter()
_cailianshe_service: Optional[CailiansheService] = None


def _get_service() -> CailiansheService:
    global _cailianshe_service
    if _cailianshe_service is None:
        _cailianshe_service = CailiansheService()
    return _cailianshe_service


class CailiansheTestRequest(BaseModel):
    """财联社测试请求"""

    category: str = Field(
        default="red",
        description="分类：red=加红, remind=提醒, hk=港美股, announcement=公司, fund=基金, watch=看板",
    )
    limit: int = Field(default=10, ge=1, le=100, description="返回条数")
    save_to_db: bool = Field(default=False, description="是否保存至 decision_logs")


@router.post(
    "/test",
    summary="财联社电报快讯测试",
    description="从 RSSHub 拉取财联社电报，支持加红/提醒/港美股/公司/基金/看板，解析为统一格式。",
    responses={
        200: {"description": "成功，返回 type、data、parsed、saved_count"},
        500: {"description": "服务异常"},
    },
)
async def cailianshe_test(
    req: CailiansheTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """测试财联社电报快讯。返回格式与 eastmoney/wallstreetcn 一致。"""
    try:
        service = _get_service()
        raw, parsed = await service.fetch_and_parse(
            category=req.category or "red",
            limit=req.limit,
        )

        saved_count = 0
        if req.save_to_db and parsed:
            saved_count = await service.save_to_decision_logs(
                db, parsed, type_=f"telegraph:{req.category}"
            )

        data = {"type": f"telegraph:{req.category}", "data": raw}
        if parsed:
            data["parsed"] = parsed
        if saved_count > 0:
            data["saved_count"] = saved_count

        return api_success(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("cailianshe_test 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
