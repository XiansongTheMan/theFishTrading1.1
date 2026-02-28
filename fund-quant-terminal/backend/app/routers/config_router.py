# =====================================================
# 配置 API - Token 等运行时配置
# 存储于 MongoDB config 集合
# =====================================================

import asyncio
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.routers.data import data_service
from app.schemas.response import api_success
from app.utils.logger import logger

router = APIRouter()
CONFIG_ID = "tokens"

# AI Agent 可选：grok / qwen，二选一，默认 grok
PRIMARY_AI_AGENT_KEY = "primary_ai_agent"
VALID_AI_AGENTS = ("grok", "qwen")
DEFAULT_AI_AGENT = "grok"

# AI Token 列表（每个 agent 支持多 Token + 备注，第一个为选中/主 Token）
GROK_LIST_KEY = "grok_list"
QWEN_LIST_KEY = "qwen_list"
AI_LIST_KEYS = {"grok": GROK_LIST_KEY, "qwen": QWEN_LIST_KEY}
AI_LABELS = {"grok": "Grok API", "qwen": "通义千问 API"}
AI_PLACEHOLDERS = {
    "grok": "在 console.x.ai 获取 API Key",
    "qwen": "在 dashscope.console.aliyun.com 获取 API Key",
}

TUSHARE_LIST_KEY = "tushare_list"
PRIMARY_DATA_SOURCE_KEY = "primary_data_source"
DEFAULT_DATA_SOURCE = "tushare"


def _mask_token(s: str | None) -> str:
    if not s or len(s) < 4:
        return "****" if s else ""
    return "*" * (len(s) - 4) + s[-4:]


class TushareItem(BaseModel):
    """单个 Tushare Token"""

    token: str = Field("", description="Token 值")
    remark: str = Field("", description="备注，如 主、备用1")


class TokensUpdateRequest(BaseModel):
    """Token 更新请求"""

    primary_ai_agent: str | None = Field(None, description="主要 AI Agent：grok 或 qwen，默认 grok")
    primary_data_source: str | None = Field(None, description="主要金融数据源：akshare 或 tushare，默认 tushare")
    tushare_list: list[dict] = Field(
        default_factory=list,
        description="Tushare 列表，每项 {token?, remark, keep_existing?}；keep_existing 时从已有列表取 token",
    )
    grok_list: list[dict] | None = Field(
        None,
        description="Grok Token 列表，每项 {token?, remark, keep_existing?}；第一个为选中",
    )
    qwen_list: list[dict] | None = Field(
        None,
        description="通义千问 Token 列表，每项 {token?, remark, keep_existing?}；第一个为选中",
    )


class TokenTestRequest(BaseModel):
    """Token 连接测试请求"""

    key: str = Field(..., description="token 键名：akshare, tushare, grok, qwen")
    value: str | None = Field(None, description="可选，用于测试输入框的值；不传则使用已存储的值")
    index: int | None = Field(None, description="多条目时指定第几个（0-based），如 tushare、grok、qwen")


def _normalize_ai_list(doc: dict, list_key: str, tokens_fallback_key: str | None) -> list[dict]:
    """从 DB 文档中提取 AI Token 列表，兼容旧格式（tokens.grok_api / tokens.qwen_api 单值）"""
    items = doc.get(list_key) or []
    if not items and tokens_fallback_key and doc.get("tokens", {}).get(tokens_fallback_key):
        val = (doc["tokens"].get(tokens_fallback_key) or "").strip()
        if val:
            items = [{"token": val, "remark": "主", "order": 0}]
    out = []
    for i, it in enumerate(items if isinstance(items, list) else []):
        item = it if isinstance(it, dict) else {}
        token = (item.get("token") or "").strip()
        remark = (item.get("remark") or ("主" if i == 0 else f"备用{i}")).strip()
        out.append({"token": token, "remark": remark or ("主" if i == 0 else ""), "order": i})
    return out


def _normalize_tushare_list(doc: dict) -> list[dict]:
    """从 DB 文档中提取 tushare 列表，兼容旧格式（tokens.tushare 字符串）"""
    from app.config import settings

    tushare_list = doc.get(TUSHARE_LIST_KEY) or []
    if not tushare_list and doc.get("tokens", {}).get("tushare"):
        # 迁移：旧格式单 token 转为列表
        val = (doc["tokens"].get("tushare") or settings.TUSHARE_TOKEN or "").strip()
        if val:
            tushare_list = [{"token": val, "remark": "主", "order": 0}]
    out = []
    for i, it in enumerate(tushare_list if isinstance(tushare_list, list) else []):
        item = it if isinstance(it, dict) else {}
        token = (item.get("token") or "").strip()
        remark = (item.get("remark") or ("主" if i == 0 else f"备用{i}")).strip()
        out.append({"token": token, "remark": remark or ("主" if i == 0 else ""), "order": i})
    return out


@router.get("/config/tokens")
async def get_tokens(db: AsyncIOMotorDatabase = Depends(get_database)):
    """获取所有 Token 配置（值脱敏）及元信息；tushare 为多条目列表"""
    try:
        from app.config import settings

        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        tokens_raw = doc.get("tokens") or {}
        if settings.TUSHARE_TOKEN and not doc.get(TUSHARE_LIST_KEY):
            tokens_raw.setdefault("tushare", settings.TUSHARE_TOKEN or "")

        tushare_list = _normalize_tushare_list(doc)
        tushare_items = [
            {"id": f"tushare_{i}", "key": "tushare", "value_masked": _mask_token(it["token"]), "remark": it["remark"], "has_value": bool(it["token"]), "order": i, "is_primary": i == 0}
            for i, it in enumerate(tushare_list)
        ]

        grok_list = _normalize_ai_list(doc, GROK_LIST_KEY, "grok_api")
        qwen_list = _normalize_ai_list(doc, QWEN_LIST_KEY, "qwen_api")
        grok_items = [
            {"id": f"grok_{i}", "key": "grok", "value_masked": _mask_token(it["token"]), "remark": it["remark"], "has_value": bool(it["token"]), "order": i, "is_primary": i == 0}
            for i, it in enumerate(grok_list)
        ]
        qwen_items = [
            {"id": f"qwen_{i}", "key": "qwen", "value_masked": _mask_token(it["token"]), "remark": it["remark"], "has_value": bool(it["token"]), "order": i, "is_primary": i == 0}
            for i, it in enumerate(qwen_list)
        ]

        primary_ai = (doc.get(PRIMARY_AI_AGENT_KEY) or DEFAULT_AI_AGENT).lower()
        if primary_ai not in VALID_AI_AGENTS:
            primary_ai = DEFAULT_AI_AGENT
        primary_src = (doc.get(PRIMARY_DATA_SOURCE_KEY) or DEFAULT_DATA_SOURCE).lower()
        if primary_src not in ("akshare", "tushare"):
            primary_src = DEFAULT_DATA_SOURCE
        return api_success(data={
            "grok_list": grok_items,
            "qwen_list": qwen_items,
            "primary_ai_agent": primary_ai,
            "tushare_list": tushare_items,
            "primary_data_source": primary_src,
        })
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
    """更新 Token 配置并立即应用；tushare_list、grok_list、qwen_list 为多 Token 列表，第一个为选中"""
    try:
        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        primary_ai = None
        if body.primary_ai_agent is not None:
            agent = (body.primary_ai_agent or "").strip().lower()
            primary_ai = agent if agent in VALID_AI_AGENTS else DEFAULT_AI_AGENT

        primary_src = None
        if body.primary_data_source is not None:
            src = (body.primary_data_source or "").strip().lower()
            primary_src = src if src in ("akshare", "tushare") else DEFAULT_DATA_SOURCE

        def _norm_agent_list(body_list: list | None, list_key: str, fallback: str | None, doc: dict) -> list[dict] | None:
            if body_list is None:
                return None
            existing = _normalize_ai_list(doc, list_key, fallback)
            out = []
            for i, it in enumerate(body_list):
                item = it if isinstance(it, dict) else {}
                remark = (item.get("remark") or ("主" if i == 0 else f"备用{i}")).strip()
                token = (item.get("token") or "").strip()
                if item.get("keep_existing") and i < len(existing):
                    token = (existing[i].get("token") or "").strip()
                if token:
                    out.append({"token": token, "remark": remark, "order": len(out)})
            return out

        tushare_list = None
        if body.tushare_list is not None:
            existing_tushare = _normalize_tushare_list(doc)
            tushare_list = []
            for i, it in enumerate(body.tushare_list):
                item = it if isinstance(it, dict) else {}
                remark = (item.get("remark") or ("主" if i == 0 else f"备用{i}")).strip()
                token = (item.get("token") or "").strip()
                if item.get("keep_existing") and i < len(existing_tushare):
                    token = (existing_tushare[i].get("token") or "").strip()
                if token:
                    tushare_list.append({"token": token, "remark": remark, "order": len(tushare_list)})

        grok_list = _norm_agent_list(body.grok_list, GROK_LIST_KEY, "grok_api", doc)
        qwen_list = _norm_agent_list(body.qwen_list, QWEN_LIST_KEY, "qwen_api", doc)

        set_fields = {"updated_at": datetime.utcnow()}
        if primary_ai is not None:
            set_fields[PRIMARY_AI_AGENT_KEY] = primary_ai
        if primary_src is not None:
            set_fields[PRIMARY_DATA_SOURCE_KEY] = primary_src
        if tushare_list is not None:
            set_fields[TUSHARE_LIST_KEY] = tushare_list
        if grok_list is not None:
            set_fields[GROK_LIST_KEY] = grok_list
        if qwen_list is not None:
            set_fields[QWEN_LIST_KEY] = qwen_list

        await db["config"].update_one(
            {"_id": CONFIG_ID},
            {"$set": set_fields},
            upsert=True,
        )

        if tushare_list is not None and hasattr(data_service, "update_tushare_tokens"):
            data_service.update_tushare_tokens(tushare_list)
            logger.info("Tushare tokens 已应用，共 %d 个", len(tushare_list))

        if primary_src is not None and hasattr(data_service, "set_primary_data_source"):
            data_service.set_primary_data_source(primary_src)
            logger.info("主要数据源已设置为: %s", primary_src)

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
        df = pro.daily(ts_code="000001.SZ", start_date="20180701", end_date="20180718")
        if df is None or df.empty:
            return False, "接口无返回"
        return True, ""
    except Exception as e:
        return False, str(e) or "连接失败"


def _test_grok_token(token: str) -> tuple[bool, str]:
    """测试 Grok (x.ai) API Token 是否有效；使用 HTTP chat/completions + 轻量模型，超时 60 秒"""
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "fund-quant-terminal/1.0",
        }
        # grok-4-1-fast-non-reasoning 无推理模式，响应更快；极简 prompt
        body = json.dumps({
            "model": "grok-4-1-fast-non-reasoning",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "stream": False,
        }).encode("utf-8")
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            if data.get("choices") and len(data["choices"]) > 0:
                return True, ""
            return False, "接口无返回"
    except HTTPError as e:
        try:
            err_body = e.read().decode()
            err_data = json.loads(err_body)
            msg = err_data.get("error", {}).get("message", err_body) or str(e)
        except Exception:
            msg = str(e) or "连接失败"
        if e.code == 403:
            msg = f"{msg}（403：API Key 权限不足、团队被限制，或所在地区无法访问 x.ai）"
        return False, msg
    except OSError as e:
        err_msg = str(e) or "连接失败"
        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            err_msg = f"连接超时（约 60 秒），请检查网络或代理，x.ai 在国内需代理"
        return False, err_msg
    except (URLError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"


def _test_qwen_token(token: str) -> tuple[bool, str]:
    """测试通义千问 (DashScope) API Token 是否有效"""
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
        }
        body = json.dumps({
            "model": "qwen-turbo",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }).encode("utf-8")
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get("choices") and len(data["choices"]) > 0:
                return True, ""
            return False, "接口返回异常"
    except HTTPError as e:
        try:
            err_body = e.read().decode()
            err_data = json.loads(err_body)
            msg = err_data.get("error", {}).get("message", err_body) or str(e)
        except Exception:
            msg = str(e) or "连接失败"
        return False, msg
    except (URLError, OSError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"


def _test_akshare_connection() -> tuple[bool, str]:
    """测试 AKShare 基本连接，使用轻量接口 stock_info_a_code_name"""
    try:
        import akshare as ak

        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            return False, "接口无返回"
        return True, ""
    except Exception as e:
        err_msg = str(e) or "连接失败"
        hint = " 若仍失败，请尝试登录东方财富网站 (eastmoney.com) 后再试。"
        if "登录" not in err_msg and "cookies" not in err_msg.lower():
            err_msg = err_msg + hint
        return False, err_msg


@router.post("/config/tokens/test")
async def test_token(
    body: TokenTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """测试指定 Token 的连接是否成功"""
    try:
        key = (body.key or "").strip()

        if key == "akshare":
            ok, msg = await asyncio.to_thread(_test_akshare_connection)
            if ok:
                return api_success(data={"ok": True})
            return api_success(
                data={"ok": False, "message": msg or "连接失败。若仍失败，请尝试登录东方财富网站 (eastmoney.com) 后再试。"}
            )

        if key == "tushare":
            token_val = (body.value or "").strip()
            if not token_val:
                doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
                tushare_list = _normalize_tushare_list(doc)
                idx = body.index if body.index is not None else 0
                if 0 <= idx < len(tushare_list):
                    token_val = (tushare_list[idx].get("token") or "").strip()
            if not token_val:
                return api_success(data={"ok": False, "message": "请先配置 Token"})
            ok, msg = await asyncio.to_thread(_test_tushare_token, token_val)
            if ok:
                return api_success(data={"ok": True})
            return api_success(data={"ok": False, "message": msg or "连接失败"})

        if key == "grok":
            token_val = (body.value or "").strip()
            if not token_val:
                doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
                grok_list = _normalize_ai_list(doc, GROK_LIST_KEY, "grok_api")
                idx = body.index if body.index is not None else 0
                if 0 <= idx < len(grok_list):
                    token_val = (grok_list[idx].get("token") or "").strip()
            if not token_val:
                return api_success(data={"ok": False, "message": "请先配置 Token"})
            ok, msg = await asyncio.to_thread(_test_grok_token, token_val)
            if ok:
                return api_success(data={"ok": True})
            return api_success(data={"ok": False, "message": msg or "连接失败"})

        if key == "qwen":
            token_val = (body.value or "").strip()
            if not token_val:
                doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
                qwen_list = _normalize_ai_list(doc, QWEN_LIST_KEY, "qwen_api")
                idx = body.index if body.index is not None else 0
                if 0 <= idx < len(qwen_list):
                    token_val = (qwen_list[idx].get("token") or "").strip()
            if not token_val:
                return api_success(data={"ok": False, "message": "请先配置 Token"})
            ok, msg = await asyncio.to_thread(_test_qwen_token, token_val)
            if ok:
                return api_success(data={"ok": True})
            return api_success(data={"ok": False, "message": msg or "连接失败"})

        raise HTTPException(status_code=400, detail=f"不支持的 token 类型: {key}")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("test_token error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/data-source")
async def get_data_source(db: AsyncIOMotorDatabase = Depends(get_database)):
    """获取主要金融数据源配置及当前实际使用的数据源"""
    try:
        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        primary = (doc.get(PRIMARY_DATA_SOURCE_KEY) or DEFAULT_DATA_SOURCE).lower()
        if primary not in ("akshare", "tushare"):
            primary = DEFAULT_DATA_SOURCE
        effective = primary
        if hasattr(data_service, "get_effective_data_source"):
            effective = data_service.get_effective_data_source() or primary
        return api_success(data={"primary": primary, "effective": effective})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_data_source error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# 定时新闻采集关注的基金列表（APScheduler 每 4 小时抓取）
WATCHED_FUNDS_ID = "watched_funds"


class WatchedFundsUpdateRequest(BaseModel):
    fund_codes: list[str] = Field(default_factory=list, description="基金代码列表，如 ['021896','000001']")


@router.get("/config/watched-funds")
async def get_watched_funds(db: AsyncIOMotorDatabase = Depends(get_database)):
    """获取定时新闻采集关注的基金列表"""
    try:
        doc = await db["config"].find_one({"_id": WATCHED_FUNDS_ID})
        codes = list(doc.get("fund_codes", [])) if doc else []
        return api_success(data={"fund_codes": codes})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_watched_funds error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/watched-funds")
async def update_watched_funds(
    body: WatchedFundsUpdateRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """更新定时新闻采集关注的基金列表"""
    try:
        codes = [str(c).strip().split(".")[0].zfill(6) for c in (body.fund_codes or []) if c]
        codes = list(dict.fromkeys(codes))
        await db["config"].update_one(
            {"_id": WATCHED_FUNDS_ID},
            {"$set": {"fund_codes": codes, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return api_success(data={"fund_codes": codes}, message="已保存")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_watched_funds error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
