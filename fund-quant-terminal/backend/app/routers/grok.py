# =====================================================
# Grok 角色提示词 API
# GET 获取最新 / POST 保存新版本（自动递增 version）
# =====================================================

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.schemas.response import api_error, api_success
from app.utils.logger import logger

router = APIRouter()

COLLECTION = "grok_prompts"


class GrokPromptSave(BaseModel):
    """保存 Grok 提示词请求"""

    content: str = Field(..., description="提示词内容")


@router.get("/grok-prompt")
async def get_grok_prompt(
    version: int | None = Query(None, description="指定版本号，不传则返回最新"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """获取 Grok 角色提示词（最新或指定版本）"""
    try:
        filt = {"version": version} if version else {}
        kw: dict = {"sort": [("version", -1)]} if not version else {}
        doc = await db[COLLECTION].find_one(filt, **kw)
        if not doc:
            return api_success(data=None, message="暂无提示词")
        ut = doc.get("updated_at")
        data = {
            "id": str(doc["_id"]),
            "content": doc.get("content", ""),
            "version": doc.get("version", 0),
            "updated_at": ut.isoformat() if ut and hasattr(ut, "isoformat") else "",
        }
        return api_success(data=data)
    except Exception as e:
        logger.exception("get_grok_prompt error: %s", e)
        return api_error(code=500, message=str(e))


@router.post("/grok-prompt")
async def save_grok_prompt(
    body: GrokPromptSave,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """保存新版本 Grok 提示词（自动递增 version）"""
    try:
        last = await db[COLLECTION].find_one({}, sort=[("version", -1)])
        next_version = (last["version"] + 1) if last else 1
        now = datetime.utcnow()
        doc: dict[str, Any] = {
            "content": body.content,
            "version": next_version,
            "updated_at": now,
        }
        result = await db[COLLECTION].insert_one(doc)
        doc["id"] = str(result.inserted_id)
        logger.info("grok_prompt saved, version=%s", next_version)
        return api_success(
            data={
                "id": doc["id"],
                "version": next_version,
                "updated_at": now.isoformat(),
            },
            message=f"已保存为新版本 v{next_version}",
        )
    except Exception as e:
        logger.exception("save_grok_prompt error: %s", e)
        return api_error(code=500, message=str(e))


@router.get("/grok-prompt/history")
async def get_grok_prompt_history(
    limit: int = 20,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """获取历史版本列表"""
    try:
        cursor = db[COLLECTION].find(
            {},
            {"content": 0},
            sort=[("version", -1)],
        ).limit(limit)
        items = []
        async for doc in cursor:
            d = {"id": str(doc["_id"]), "version": doc.get("version", 0)}
            if "updated_at" in doc:
                d["updated_at"] = doc["updated_at"].isoformat() if hasattr(doc["updated_at"], "isoformat") else str(doc["updated_at"])
            items.append(d)
        return api_success(data=items)
    except Exception as e:
        logger.exception("get_grok_prompt_history error: %s", e)
        return api_error(code=500, message=str(e))
