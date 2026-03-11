# Agent role prompts API - grok/qwen multi-templates

import asyncio
from datetime import datetime

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
from app.agent_config import GROK_MODELS, QWEN_MODELS, get_agent_config, fetch_qwen_models
from app.agent_config.common import build_messages
from app.services.llm_client import MultiLLMClient, get_llm_client

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


class ChatMessageItem(BaseModel):
    role: str = Field(..., description="user or assistant")
    content: str = Field("", description="message content")


class AgentChatTestRequest(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    content: str = Field("", description="user input to test")
    messages: list[dict] | None = Field(None, description="conversation history for context, [{role, content}, ...]")
    provider: str | None = Field(None, description="override provider (default from agent)")
    model: str | None = Field(None, description="override model")
    temperature: float | None = Field(None, description="override temperature")
    fund_code: str | None = Field(None, description="optional fund code for context")
    asset_summary: str | None = Field(None, description="optional asset summary for context")


class AgentChatTestResponse(BaseModel):
    ok: bool = Field(..., description="success or failure")
    content: str = Field("", description="model reply or error message")
    model: str = Field("", description="model used")
    provider: str = Field("", description="provider used")
    error: str | None = Field(None, description="error message when ok=False")


class LLMDecisionCallRequest(BaseModel):
    fund_code: str = Field("", description="基金代码")
    provider: str | None = Field(None, description="grok 或 qwen，不传则从 config 取 primary_ai_agent")
    include_news: bool = Field(True, description="是否包含新闻与情绪")
    auto_call: bool = Field(False, description="是否自动调用 LLM 生成决策")


class AgentModelUpdate(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    model: str = Field("", description="model name to select")


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

        if a == "grok":
            models = GROK_MODELS
        else:
            models = QWEN_MODELS  # default fallback
            try:
                lst = _normalize_ai_list(tokens_doc, QWEN_LIST_KEY, "qwen_api")
                token = (lst[0]["token"] or "").strip() if lst and lst[0].get("token") else ""
                if token:
                    models_result = await asyncio.to_thread(fetch_qwen_models, token)
                    if models_result and isinstance(models_result, list) and len(models_result) > 0:
                        models = models_result
            except Exception:
                pass  # keep QWEN_MODELS
        cfg = get_agent_config(a) or {}
        selected_model = (config_doc.get(f"selected_{a}_model") or "").strip() or cfg.get("model", "")

        return api_success(data={
            "items": items,
            "selected_id": selected_id or (items[0]["id"] if items else ""),
            "primary_ai_agent": primary_ai,
            "models": models,
            "selected_model": selected_model,
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_agent_templates error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent-prompts/models")
async def sync_agent_models(
    agent: str = Query(..., description="grok or qwen"),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """从官方接口同步可用模型列表。qwen 调用 DashScope GET /v1/models，grok 返回本地列表。"""
    try:
        a = (agent or "").strip().lower()
        if a not in VALID_AI_AGENTS:
            a = DEFAULT_AI_AGENT

        if a == "grok":
            return api_success(data={"models": GROK_MODELS, "from_api": False})

        tokens_doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        lst = _normalize_ai_list(tokens_doc, QWEN_LIST_KEY, "qwen_api")
        token = (lst[0]["token"] or "").strip() if lst and lst[0].get("token") else ""
        if not token:
            return api_success(data={"models": QWEN_MODELS, "from_api": False})

        try:
            models_result = await asyncio.to_thread(fetch_qwen_models, token)
            if models_result and isinstance(models_result, list) and len(models_result) > 0:
                return api_success(data={"models": models_result, "from_api": True})
        except Exception:
            pass
        return api_success(data={"models": QWEN_MODELS, "from_api": False})
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("sync_agent_models error: %s", e)
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





@router.post("/agent-prompts-test")
async def agent_chat_test(
    body: AgentChatTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    llm_client: MultiLLMClient = Depends(get_llm_client),
):
    """测试 Agent 连接：用户输入内容，Agent 返回回复。不保存到数据库。使用 MultiLLMClient 统一调用。"""
    from bson import ObjectId

    try:
        provider = (body.agent or "").strip().lower()
        if provider not in VALID_AI_AGENTS:
            provider = DEFAULT_AI_AGENT

        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        if provider == "grok":
            lst = _normalize_ai_list(doc, GROK_LIST_KEY, "grok_api")
        else:
            lst = _normalize_ai_list(doc, QWEN_LIST_KEY, "qwen_api")

        if not lst or not lst[0].get("token"):
            return api_success(data={
                "ok": False,
                "content": "请先在 Token 配置中为该 Agent 添加 API Key",
                "model": "",
                "provider": provider,
                "error": "请先在 Token 配置中为该 Agent 添加 API Key",
            })

        token_val = lst[0]["token"].strip()
        user_content = (body.content or "").strip() or "你好"
        hist = body.messages if body.messages else None

        # 获取当前选中的 Agent 角色模板，作为 system 提示；若有历史则追加「结合历史作答」指令
        system_prompt = ""
        role_config = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
        selected_id = (role_config.get(f"selected_{provider}_id") or "").strip()
        if selected_id:
            try:
                template_doc = await db[COLLECTION].find_one({"_id": ObjectId(selected_id)})
                if template_doc and template_doc.get("content"):
                    system_prompt = (template_doc["content"] or "").strip()
            except Exception:
                pass
        if hist and len(hist) > 0:
            ctx_hint = "请结合上述对话历史中的上下文信息作答。若用户已在历史中给出变量或数值，请据此推理并给出具体答案。"
            system_prompt = (system_prompt + "\n\n" + ctx_hint).strip() if system_prompt else ctx_hint

        selected_model = (role_config.get(f"selected_{provider}_model") or "").strip() or None
        cfg = get_agent_config(provider) or {}
        model_param = selected_model or cfg.get("model") or None

        # 从 agent_config url 推导 base_url（OpenAI 客户端需要不含 /chat/completions 的 base）
        api_url = cfg.get("url") or ""
        base_url = api_url.replace("/chat/completions", "").rstrip("/") if api_url else None

        messages = build_messages(hist, user_content, system_prompt or None)

        result = await llm_client.generate_response(
            messages=messages,
            model=model_param,
            provider=provider,
            temperature=getattr(body, "temperature", None),
            max_tokens=cfg.get("max_tokens"),
            api_key=token_val,
            base_url=base_url,
        )

        if result.get("ok"):
            return api_success(data={
                "ok": True,
                "content": result.get("content", ""),
                "model": result.get("model", model_param or ""),
                "provider": result.get("provider", provider),
                "error": None,
            })
        return api_success(data={
            "ok": False,
            "content": result.get("error", "未知错误"),
            "model": model_param or cfg.get("model", ""),
            "provider": provider,
            "error": result.get("error", "未知错误"),
        })
    except Exception as e:
        logger.exception("agent_chat_test error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/llm-decision-call")
async def llm_decision_call(
    body: LLMDecisionCallRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    llm_client: MultiLLMClient = Depends(get_llm_client),
):
    """
    构建 LLM 决策上下文消息，可选自动调用 LLM 生成决策。
    - auto_call=False: 返回 messages 和 news_summary，供前端自行调用
    - auto_call=True: 使用 DB Token 调用 LLM，返回 content、model、provider、news_summary
    """
    from app.services.grok_decision import build_decision_messages

    try:
        provider = (body.provider or "").strip().lower()
        if not provider or provider not in VALID_AI_AGENTS:
            doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
            provider = (doc.get(PRIMARY_AI_AGENT_KEY) or DEFAULT_AI_AGENT).lower()
        if provider not in VALID_AI_AGENTS:
            provider = DEFAULT_AI_AGENT

        messages, news_summary = await build_decision_messages(
            fund_code=body.fund_code or "",
            db=db,
            provider=provider,
            include_news=body.include_news,
        )

        if not body.auto_call:
            return api_success(data={
                "ok": True,
                "content": "",
                "model": "",
                "provider": provider,
                "messages": messages,
                "news_summary": news_summary,
            })

        # auto_call: 使用 DB Token 调用 LLM
        doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
        if provider == "grok":
            lst = _normalize_ai_list(doc, GROK_LIST_KEY, "grok_api")
        else:
            lst = _normalize_ai_list(doc, QWEN_LIST_KEY, "qwen_api")

        if not lst or not lst[0].get("token"):
            return api_success(data={
                "ok": False,
                "content": "请先在 Token 配置中为该 Agent 添加 API Key",
                "model": "",
                "provider": provider,
                "messages": messages,
                "news_summary": news_summary,
            })

        token_val = lst[0]["token"].strip()
        role_config = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
        selected_model = (role_config.get(f"selected_{provider}_model") or "").strip() or None
        cfg = get_agent_config(provider) or {}
        model_param = selected_model or cfg.get("model") or None
        api_url = cfg.get("url") or ""
        base_url = api_url.replace("/chat/completions", "").rstrip("/") if api_url else None

        result = await llm_client.generate_response(
            messages=messages,
            model=model_param,
            provider=provider,
            temperature=cfg.get("temperature"),
            max_tokens=cfg.get("max_tokens"),
            api_key=token_val,
            base_url=base_url,
        )

        if result.get("ok"):
            return api_success(data={
                "ok": True,
                "content": result.get("content", ""),
                "model": result.get("model", model_param or ""),
                "provider": result.get("provider", provider),
                "news_summary": news_summary,
            })
        return api_success(data={
            "ok": False,
            "content": result.get("error", "未知错误"),
            "model": model_param or cfg.get("model", ""),
            "provider": provider,
            "news_summary": news_summary,
        })
    except Exception as e:
        logger.exception("llm_decision_call error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/agent-prompts/model")
async def update_agent_model(
    body: AgentModelUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """保存当前 Agent 选中的模型到 agent_role_config"""
    try:
        a = (body.agent or "").strip().lower()
        if a not in VALID_AI_AGENTS:
            a = DEFAULT_AI_AGENT
        model_val = (body.model or "").strip()
        await db["config"].update_one(
            {"_id": CONFIG_AGENT_ROLE},
            {"$set": {f"selected_{a}_model": model_val, "updated_at": datetime.utcnow()}},
            upsert=True,
        )
        return api_success(message="saved")
    except Exception as e:
        logger.exception("update_agent_model error: %s", e)
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
