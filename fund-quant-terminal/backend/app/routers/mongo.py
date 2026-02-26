# =====================================================
# MongoDB 连接状态测试
# =====================================================

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.config import settings
from app.database import get_database
from app.schemas.response import api_error, api_success

router = APIRouter()


@router.get("/status")
async def mongo_status(db: AsyncIOMotorDatabase = Depends(get_database)):
    """测试 MongoDB 连接状态"""
    try:
        result = await db.command("ping")
        return api_success(
            data={
                "connected": True,
                "database": settings.MONGODB_DB_NAME,
                "ping": result.get("ok") == 1,
                "message": "MongoDB 连接正常",
            }
        )
    except Exception as e:
        return api_error(
            code=503,
            message=str(e),
            data={"connected": False, "database": settings.MONGODB_DB_NAME},
        )
