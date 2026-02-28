# Agent role prompts API - grok/qwen multi-templates

import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from fastapi import APIRouter, Depends, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field

from app.database import get_database
from app.routers.config_router import (
    CONFIG_ID,
    PRIMARY_AI_AGENT_KEY,
    VALID_AI_AGENTS,
    DEFAULT_AI_AGENT,
    GROK_LIST_KEY,
    QWEN_LIST_KEY,
    _normalize_ai_list,
)
from app.schemas.response import api_success
from app.utils.logger import logger

router = APIRouter()
COLLECTION = "agent_role_templates"
CONFIG_AGENT_ROLE = "agent_role_config"


class AgentTemplateCreate(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    name: str = Field(..., description="template name")
    content: str = Field("", description="role content")


class AgentTemplateUpdate(BaseModel):
    name: str | None = Field(None, description="template name")
    content: str | None = Field(None, description="role content")


class AgentChatTestRequest(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    content: str = Field("", description="user input to test")


@router.get("/agent-prompts")
async def list_agent_templates(
    agent: str = Query(..., description="grok or qwen"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        a = (agent or "").strip().lower()
        if a not in VALID_AI_AGENTS:
            a = DEFAULT_AI_AGENT

        config_doc = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
        selected_key = f"selected_{a}_id"
        selected_id = config_doc.get(selected_key) or ""

        # 迁移：若 grok 无模板但 grok_prompts 有数据，迁移最新一条
        if a == "grok":
            count = await db[COLLECTION].count_documents({"agent": "grok"})
            if count == 0:
                old = await db["grok_prompts"].find_one({}, sort=[("version", -1)])
                if old and old.get("content"):
                    now = datetime.utcnow()
                    r = await db[COLLECTION].insert_one({
                        "agent": "grok",
                        "name": f"迁移 v{old.get('version', 1)}",
                        "content": old["content"],
                        "updated_at": now,
                    })
                    tid = str(r.inserted_id)
                    await db["config"].update_one(
                        {"_id": CONFIG_AGENT_ROLE},
                        {"$set": {"selected_grok_id": tid, "updated_at": now}},
                        upsert=True,
                    )
                    selected_id = tid
                    logger.info("已从 grok_prompts 迁移角色设定至 agent_role_templates")

        cursor = db[COLLECTION].find({"agent": a}).sort("updated_at", -1)
        items = []
        async for doc in cursor:
            ut = doc.get("updated_at")
            items.append({
                "id": str(doc["_id"]),
                "agent": doc.get("agent", a),
                "name": doc.get("name", ""),
                "content": doc.get("content", ""),
                "updated_at": ut.isoformat() if ut and hasattr(ut, "isoformat") else str(ut or ""),
                "is_selected": str(doc["_id"]) == selected_id,
            })

        tokens_doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        primary_ai = (tokens_doc.get(PRIMARY_AI_AGENT_KEY) or DEFAULT_AI_AGENT).lower()
        if primary_ai not in VALID_AI_AGENTS:
            primary_ai = DEFAULT_AI_AGENT

        return api_success(data={
            "items": items,
            "selected_id": selected_id or (items[0]["id"] if items else ""),
            "primary_ai_agent": primary_ai,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_agent_templates error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-prompts/primary")
async def get_primary_agent(db: AsyncIOMotorDatabase = Depends(get_database)):
    try:
        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        primary = (doc.get(PRIMARY_AI_AGENT_KEY) or DEFAULT_AI_AGENT).lower()
        if primary not in VALID_AI_AGENTS:
            primary = DEFAULT_AI_AGENT
        return api_success(data={"primary_ai_agent": primary})
    except Exception as e:
        logger.exception("get_primary_agent error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-prompts")
async def create_agent_template(
    body: AgentTemplateCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        a = (body.agent or "").strip().lower()
        if a not in VALID_AI_AGENTS:
            a = DEFAULT_AI_AGENT
        name = (body.name or "").strip() or "unnamed"
        now = datetime.utcnow()
        doc = {
            "agent": a,
            "name": name,
            "content": body.content or "",
            "updated_at": now,
        }
        result = await db[COLLECTION].insert_one(doc)
        doc_id = str(result.inserted_id)

        config_doc = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
        selected_key = f"selected_{a}_id"
        if not config_doc.get(selected_key):
            await db["config"].update_one(
                {"_id": CONFIG_AGENT_ROLE},
                {"$set": {selected_key: doc_id, "updated_at": now}},
                upsert=True,
            )

        return api_success(
            data={"id": doc_id, "name": name, "updated_at": now.isoformat()},
            message="saved",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("create_agent_template error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _chat_grok(token: str, user_content: str) -> tuple[bool, str]:
    """调用 Grok 对话，返回 (成功, 内容或错误信息)"""
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        url = "https://api.x.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token.strip()}",
            "Content-Type": "application/json",
            "User-Agent": "fund-quant-terminal/1.0",
        }
        body = json.dumps({
            "model": "grok-4-1-fast-non-reasoning",
            "messages": [{"role": "user", "content": (user_content or "hi").strip()[:4000]}],
            "max_tokens": 2000,
            "stream": False,
        }).encode("utf-8")
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
            choices = data.get("choices") or []
            if choices and choices[0].get("message", {}).get("content"):
                return True, choices[0]["message"]["content"]
            return False, "接口无返回"
    except HTTPError as e:
        try:
            err_data = json.loads(e.read().decode())
            msg = err_data.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return False, msg
    except (URLError, OSError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"


def _chat_qwen(token: str, user_content: str) -> tuple[bool, str]:
    """调用通义千问对话，返回 (成功, 内容或错误信息)"""
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
            "messages": [{"role": "user", "content": (user_content or "hi").strip()[:4000]}],
            "max_tokens": 2000,
        }).encode("utf-8")
        req = Request(url, data=body, headers=headers, method="POST")
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            choices = data.get("choices") or []
            if choices and choices[0].get("message", {}).get("content"):
                return True, choices[0]["message"]["content"]
            return False, "接口无返回"
    except HTTPError as e:
        try:
            err_data = json.loads(e.read().decode())
            msg = err_data.get("error", {}).get("message", str(e))
        except Exception:
            msg = str(e)
        return False, msg
    except (URLError, OSError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"


@router.post("/agent-prompts-test")
async def agent_chat_test(
    body: AgentChatTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """测试 Agent 连接：用户输入内容，Agent 返回回复。不保存到数据库。"""
    import asyncio
    try:
        a = (body.agent or "").strip().lower()
        if a not in VALID_AI_AGENTS:
            a = DEFAULT_AI_AGENT

        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        if a == "grok":
            lst = _normalize_ai_list(doc, GROK_LIST_KEY, "grok_api")
        else:
            lst = _normalize_ai_list(doc, QWEN_LIST_KEY, "qwen_api")

        if not lst or not lst[0].get("token"):
            return api_success(data={"ok": False, "content": "请先在 Token 配置中为该 Agent 添加 API Key"})

        token_val = lst[0]["token"].strip()
        user_content = (body.content or "").strip() or "你好"
        if a == "grok":
            ok, result = await asyncio.to_thread(_chat_grok, token_val, user_content)
        else:
            ok, result = await asyncio.to_thread(_chat_qwen, token_val, user_content)

        if ok:
            return api_success(data={"ok": True, "content": result})
        return api_success(data={"ok": False, "content": result})
    except Exception as e:
        logger.exception("agent_chat_test error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agent-prompts/{template_id}")
async def update_agent_template(
    template_id: str,
    body: AgentTemplateUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        from bson import ObjectId

        oid = ObjectId(template_id)
        update = {"updated_at": datetime.utcnow()}
        if body.name is not None:
            update["name"] = (body.name or "").strip() or "unnamed"
        if body.content is not None:
            update["content"] = body.content

        result = await db[COLLECTION].update_one({"_id": oid}, {"$set": update})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="not found")
        return api_success(message="updated")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("update_agent_template error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/agent-prompts/{template_id}")
async def delete_agent_template(
    template_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        from bson import ObjectId

        oid = ObjectId(template_id)
        doc = await db[COLLECTION].find_one({"_id": oid})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        agent = doc.get("agent", "grok")

        await db[COLLECTION].delete_one({"_id": oid})

        config_doc = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
        selected_key = f"selected_{agent}_id"
        if config_doc.get(selected_key) == template_id:
            next_doc = await db[COLLECTION].find_one({"agent": agent}, sort=[("updated_at", -1)])
            new_selected = str(next_doc["_id"]) if next_doc else ""
            await db["config"].update_one(
                {"_id": CONFIG_AGENT_ROLE},
                {"$set": {selected_key: new_selected, "updated_at": datetime.utcnow()}},
                upsert=True,
            )

        return api_success(message="deleted")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("delete_agent_template error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent-prompts/{template_id}/select")
async def select_agent_template(
    template_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    try:
        from bson import ObjectId

        oid = ObjectId(template_id)
        doc = await db[COLLECTION].find_one({"_id": oid})
        if not doc:
            raise HTTPException(status_code=404, detail="not found")
        agent = doc.get("agent", "grok")

        selected_key = f"selected_{agent}_id"
        await db["config"].update_one(
            {"_id": CONFIG_AGENT_ROLE},
            {"$set": {selected_key: template_id, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return api_success(message="selected")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("select_agent_template error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
