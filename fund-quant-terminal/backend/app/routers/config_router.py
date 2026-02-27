# =====================================================
# 配置 API - Token 等运行时配置
# 存储于 MongoDB config 集合
# =====================================================

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.routers.data import data_service
from app.schemas.response import api_success
from app.utils.logger import logger

router = APIRouter()
CONFIG_ID = "tokens"

# 预定义 Token 项：当前使用 / 未来将使用
TOKEN_ITEMS = {
    "tushare": {
        "label": "tushare",
        "status": "using",
        "placeholder": "在 tushare.pro 注册获取",
    },
    "grok_api": {
        "label": "grok_api",
        "status": "future",
        "placeholder": "后续对接 Grok API",
    },
}


def _mask_token(s: str | None) -> str:
    if not s or len(s) < 4:
        return "****" if s else ""
    return "*" * (len(s) - 4) + s[-4:]


class TokensUpdateRequest(BaseModel):
    """Token 更新请求"""

    tokens: dict[str, str] = Field(default_factory=dict, description="token 键值对")


class TokenTestRequest(BaseModel):
    """Token 连接测试请求"""

    key: str = Field(..., description="token 键名，如 tushare")
    value: str | None = Field(None, description="可选，用于测试输入框的值；不传则使用已存储的值")


@router.get("/config/tokens")
async def get_tokens(db: AsyncIOMotorDatabase = Depends(get_database)):
    """获取所有 Token 配置（值脱敏）及元信息"""
    try:
        from app.config import settings

        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        tokens_raw = doc.get("tokens") or {}
        tokens_raw.setdefault("tushare", settings.TUSHARE_TOKEN or "")

        result = []
        for key, meta in TOKEN_ITEMS.items():
            val = tokens_raw.get(key) or ""
            result.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "status": meta.get("status", "using"),
                    "placeholder": meta["placeholder"],
                    "value_masked": _mask_token(val),
                    "has_value": bool(val),
                }
            )
        return api_success(data={"items": result})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_tokens error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/tokens")
async def update_tokens(
    body: TokensUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """更新 Token 配置并立即应用（支持部分更新）"""
    try:
        from app.config import settings

        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        current = doc.get("tokens") or {}
        current.setdefault("tushare", settings.TUSHARE_TOKEN or "")
        for key in TOKEN_ITEMS:
            current.setdefault(key, "")

        updates = body.tokens or {}
        for k, v in updates.items():
            if k in TOKEN_ITEMS:
                current[k] = (v or "").strip()

        await db["config"].update_one(
            {"_id": CONFIG_ID},
            {"$set": {"tokens": current, "updated_at": datetime.utcnow()}},
            upsert=True,
        )

        # 应用 Tushare Token
        tushare_val = current.get("tushare", "").strip()
        if hasattr(data_service, "update_tushare_token"):
            data_service.update_tushare_token(tushare_val)
            logger.info("Tushare token 已应用")

        return api_success(message="Token 已保存并应用")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_tokens error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _test_tushare_token(token: str) -> tuple[bool, str]:
    """测试 Tushare Token 是否有效"""
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        import tushare as ts

        ts.set_token(token.strip())
        pro = ts.pro_api()
        df = pro.trade_cal(exchange="", start_date="20240101", end_date="20240105")
        if df is None or df.empty:
            return False, "接口无返回"
        return True, ""
    except Exception as e:
        return False, str(e) or "连接失败"


@router.post("/config/tokens/test")
async def test_token(
    body: TokenTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """测试指定 Token 的连接是否成功"""
    try:
        key = (body.key or "").strip()
        if key not in TOKEN_ITEMS:
            raise HTTPException(status_code=400, detail=f"不支持的 token 类型: {key}")

        # 优先使用传入的 value，否则从数据库读取
        token_val = body.value
        if token_val is None or token_val == "":
            doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
            tokens_raw = doc.get("tokens") or {}
            token_val = tokens_raw.get(key, "")

        token_val = (token_val or "").strip()
        if not token_val:
            return api_success(data={"ok": False, "message": "请先配置 Token"})

        if key == "tushare":
            ok, msg = await asyncio.to_thread(_test_tushare_token, token_val)
            if ok:
                return api_success(data={"ok": True})
            return api_success(data={"ok": False, "message": msg or "连接失败"})

        if key == "grok_api":
            return api_success(data={"ok": False, "message": "该接口尚未对接，无法测试"})

        return api_success(data={"ok": False, "message": "暂不支持该 Token 的连接测试"})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("test_token error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
