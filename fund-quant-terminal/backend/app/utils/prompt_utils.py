# =====================================================
# 多 LLM 提示词工具
# 支持 per-provider 模板、完整上下文构建（资产+决策+新闻）
# =====================================================

from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.logger import logger

# 单条消息内容最大字符数，控制 token 消耗
MAX_CONTENT_CHARS = 4000
# 决策历史最多条数
MAX_DECISION_HISTORY = 10
# 资产摘要最大字符
MAX_ASSET_SUMMARY_CHARS = 1500

COLLECTION_TEMPLATES = "agent_role_templates"
CONFIG_AGENT_ROLE = "agent_role_config"
COLLECTION_GROK_PROMPTS = "grok_prompts"
COLLECTION_DECISION_LOGS = "decision_logs"
COLLECTION_ASSETS = "assets"
ACCOUNT_DOC_ID = "main"


def _truncate(content: str, max_len: int = MAX_CONTENT_CHARS) -> str:
    """安全截断内容，避免超长 token"""
    if not content or not isinstance(content, str):
        return ""
    s = content.strip()
    return s[:max_len] + ("..." if len(s) > max_len else "")


async def load_system_prompt(db: AsyncIOMotorDatabase, provider: str) -> str:
    """
    加载 per-provider 系统提示词。
    优先：agent_role_templates 中该 provider 选中的模板；
    回退：grok 用 grok_prompts 最新版；qwen 同 grok 逻辑（共用模板）；
    最后：项目根 GROK_ROLE_PROMPT.md 文件。
    """
    p = (provider or "grok").strip().lower()
    if p not in ("grok", "qwen"):
        p = "grok"

    # 1. agent_role_templates（per-provider 选中模板）
    config_doc = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
    selected_key = f"selected_{p}_id"
    selected_id = (config_doc.get(selected_key) or "").strip()
    if selected_id:
        try:
            from bson import ObjectId
            doc = await db[COLLECTION_TEMPLATES].find_one({"_id": ObjectId(selected_id)})
            if doc and doc.get("content"):
                content = (doc.get("content") or "").strip()
                if content:
                    logger.info("prompt_utils: loaded system prompt from agent_role_templates for %s", p)
                    return _truncate(content)
        except Exception as e:
            logger.warning("prompt_utils: load template %s failed: %s", selected_id, e)

    # 2. grok_prompts 最新版（grok/qwen 共用）
    old = await db[COLLECTION_GROK_PROMPTS].find_one({}, sort=[("version", -1)])
    if old and old.get("content"):
        content = (old.get("content") or "").strip()
        if content:
            logger.info("prompt_utils: loaded system prompt from grok_prompts for %s", p)
            return _truncate(content)

    # 3. 文件回退
    try:
        base = Path(__file__).resolve().parent.parent.parent.parent
        path = base / "GROK_ROLE_PROMPT.md"
        if path.exists():
            text = path.read_text(encoding="utf-8").strip()
            if text:
                logger.info("prompt_utils: loaded system prompt from file for %s", p)
                return _truncate(text)
    except Exception as e:
        logger.warning("prompt_utils: load file failed: %s", e)

    logger.info("prompt_utils: no system prompt found for %s, using default", p)
    return _truncate("你是一位专业量化基金经理，请基于提供的上下文给出投资建议。")


async def _get_asset_summary(db: AsyncIOMotorDatabase) -> str:
    """获取资产摘要：现金 + 持仓"""
    parts = []
    try:
        doc = await db["account"].find_one({"_id": ACCOUNT_DOC_ID})
        cap = float(doc["capital"]) if doc and "capital" in doc else 0
        parts.append(f"现金: {cap:.2f} 元")
    except Exception as e:
        logger.debug("prompt_utils: get_capital failed: %s", e)

    try:
        cursor = db[COLLECTION_ASSETS].find({}).sort("created_at", -1).limit(50)
        docs = await cursor.to_list(length=50)
        if docs:
            lines = []
            for d in docs:
                sym = d.get("symbol") or ""
                name = d.get("name") or ""
                qty = float(d.get("quantity") or 0)
                cost = d.get("cost_price")
                cur = d.get("current_price")
                if sym and name:
                    lines.append(f"  - {name}({sym}): {qty} 份" + (f", 成本 {cost}" if cost else "") + (f", 现价 {cur}" if cur else ""))
            if lines:
                parts.append("持仓:\n" + "\n".join(lines[:20]))
    except Exception as e:
        logger.debug("prompt_utils: get assets failed: %s", e)

    s = "\n".join(parts) if parts else "（暂无资产数据）"
    return _truncate(s, MAX_ASSET_SUMMARY_CHARS)


async def _get_decision_history(db: AsyncIOMotorDatabase, fund_code: str | None) -> str:
    """获取近期决策历史"""
    query = {}
    if fund_code and str(fund_code).strip():
        code = str(fund_code).strip().split(".")[0].zfill(6)
        query["fund_code"] = code
    try:
        cursor = db[COLLECTION_DECISION_LOGS].find(query).sort("timestamp", -1).limit(MAX_DECISION_HISTORY)
        docs = await cursor.to_list(length=MAX_DECISION_HISTORY)
        if not docs:
            return "（暂无决策记录）"
        lines = []
        for d in docs:
            ts = d.get("timestamp")
            ts_str = ts.isoformat()[:19] if ts and hasattr(ts, "isoformat") else str(ts or "")
            action = d.get("user_action") or ""
            resp = (d.get("grok_response") or d.get("llm_response") or "")[:200]
            lines.append(f"  - [{ts_str}] {action}: {resp}...")
        return _truncate("\n".join(lines), MAX_CONTENT_CHARS)
    except Exception as e:
        logger.debug("prompt_utils: get decision history failed: %s", e)
        return "（获取决策记录失败）"


async def build_full_context_messages(
    fund_code: str,
    db: AsyncIOMotorDatabase,
    provider: str,
    include_news: bool = True,
    custom_news_links: list[str] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    """
    构建完整上下文消息列表，兼容 unified LLM client。
    组合：system prompt + 资产摘要 + 决策历史 + 新闻与情绪（来自 grok_decision）。
    返回: (messages, news_summary)
      - messages: [{"role": "system", "content": ...}, {"role": "user", "content": ...}]
      - news_summary: 新闻摘要列表，include_news=False 时为空
    """
    from app.services.grok_decision import generate_grok_prompt

    p = (provider or "grok").strip().lower()
    if p not in ("grok", "qwen"):
        p = "grok"

    # 1. system prompt
    system_prompt = await load_system_prompt(db, p)
    system_content = system_prompt or "你是一位专业量化基金经理，请基于提供的上下文给出投资建议。"
    system_content = _truncate(system_content)

    # 2. 资产摘要
    asset_summary = await _get_asset_summary(db)

    # 3. 决策历史
    decision_history = await _get_decision_history(db, fund_code)

    # 4. 新闻与情绪（include_news=False 时跳过）
    news_prompt = ""
    news_summary: list[dict[str, Any]] = []
    if include_news:
        news_prompt, news_summary = await generate_grok_prompt(
            fund_code or "",
            db,
            include_news_list=True,
            custom_news_links=custom_news_links,
        )

    # 5. 组装 user 消息
    code = (fund_code or "").strip().split(".")[0] if fund_code else ""
    code = code.zfill(6) if code else ""
    scope = f"基金{code}" if code else "市场"

    user_parts = [
        f"以下是{scope}相关的完整上下文，请基于此给出投资建议。",
        "",
        "【资产概况】",
        asset_summary,
        "",
        "【近期决策】",
        decision_history,
    ]
    if include_news:
        user_parts.extend(["", "【新闻与情绪】", news_prompt])
    user_content = "\n".join(user_parts)
    user_content = _truncate(user_content)

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
    logger.info(
        "prompt_utils: built %d messages for provider=%s fund_code=%s include_news=%s",
        len(messages), p, fund_code or "(all)", include_news,
    )
    return messages, news_summary
