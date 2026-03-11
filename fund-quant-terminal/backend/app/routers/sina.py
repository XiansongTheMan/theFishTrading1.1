# =====================================================
# 新浪财经 API 路由
# POST /api/sina/test 测试（国际、市场、其他、焦点、公司、宏观、两会、观点）
# 新浪 RSS 已不可用，统一使用东方财富快讯
# =====================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_success
from app.services.eastmoney_service import EastMoneyService
from app.services.sina_service import SinaService
from app.utils.logger import logger

router = APIRouter()
_eastmoney_service: Optional[EastMoneyService] = None
_sina_service: Optional[SinaService] = None


def _get_eastmoney_service() -> EastMoneyService:
    global _eastmoney_service
    if _eastmoney_service is None:
        _eastmoney_service = EastMoneyService()
    return _eastmoney_service


def _get_sina_service() -> SinaService:
    global _sina_service
    if _sina_service is None:
        _sina_service = SinaService()
    return _sina_service


class SinaTestRequest(BaseModel):
    category: str = Field(default="macro", description="international/market/other/focus/company/macro/lianghui/opinion")
    limit: int = Field(default=10, ge=1, le=100)
    save_to_db: bool = Field(default=False)


@router.post("/test")
async def sina_test(req: SinaTestRequest, db: AsyncIOMotorDatabase = Depends(get_database)) -> dict:
    try:
        em = _get_eastmoney_service()
        raw_em, parsed = await em.fetch_and_parse(limit=req.limit)
        category = req.category or "macro"
        raw = {
            "source": "sina",
            "category": category,
            "feed": {
                "title": f"新浪财经-{category}（东方财富快讯）",
                "link": "https://finance.sina.com.cn/",
            },
            "entries_count": len(parsed),
        }
        saved_count = 0
        if req.save_to_db and parsed:
            sina_svc = _get_sina_service()
            saved_count = await sina_svc.save_to_decision_logs(db, parsed, type_=f"rss:{category}")
        data = {"type": f"rss:{category}", "data": raw, "parsed": parsed}
        if saved_count > 0:
            data["saved_count"] = saved_count
        return api_success(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("sina_test: %s", e)
        raise HTTPException(status_code=500, detail=str(e))