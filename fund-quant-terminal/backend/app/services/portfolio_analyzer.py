# =====================================================
# 投资组合分析服务
# 聚合上下文、提示词、LLM 调用，返回结构化分析结果
# =====================================================

import json
import re
from datetime import datetime

from app.database import get_database
from app.services.portfolio_context_builder import PortfolioContextBuilder
from app.services.llm_client import MultiLLMClient
from app.routers.agent_prompts import get_analysis_prompt
from app.routers.config_router import (
    CONFIG_ID,
    CONFIG_AGENT_ROLE,
    PRIMARY_AI_AGENT_KEY,
    GROK_LIST_KEY,
    QWEN_LIST_KEY,
    VALID_AI_AGENTS,
    DEFAULT_AI_AGENT,
    _normalize_ai_list,
)
from app.agent_config import get_agent_config
from app.config import llm_settings
from app.utils.logger import logger


def _parse_json_from_response(raw: str) -> dict | None:
    """
    从 LLM 返回内容中安全解析 JSON。
    支持：纯 JSON、Markdown ```json ... ```、前后缀文本。
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    # 1. 尝试 Markdown 代码块
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # 2. 尝试 { ... } 块
    match = re.search(r"\{[\s\S]*\}", s)
    if match:
        try:
            return json.loads(match.group(0))
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. 直接解析
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass

    logger.warning("portfolio_analyzer: failed to parse JSON from response, len=%d", len(s))
    return None


def get_portfolio_analyzer() -> "PortfolioAnalyzer":
    """FastAPI Depends：返回 PortfolioAnalyzer 实例"""
    return PortfolioAnalyzer()


class PortfolioAnalyzer:
    """
    投资组合分析器。

    构建 portfolio_context，生成提示词，调用 LLM 生成分析，解析 JSON 返回。
    使用 DB 配置的 primary_ai_agent、Token、选中的模型；支持 model_type 覆盖。
    """

    def __init__(self) -> None:
        self._context_builder = PortfolioContextBuilder()
        self._llm_client = MultiLLMClient()

    async def analyze_portfolio(
        self,
        user_id: str,
        model_type: str | None = None,
    ) -> dict:
        """
        对指定用户投资组合进行 AI 分析。

        Args:
            user_id: 用户 ID，用于 context 与风险偏好。
            model_type: LLM 提供商（grok/qwen）。为 None 时使用 config 或 DB primary_ai_agent。

        Returns:
            包含以下 key 的 dict:
            - analysis: 解析后的 LLM 分析结果（符合 fund_analyst_prompt 的 JSON schema），
                        解析失败时为 {"error": str, "raw": str}
            - raw_context: 原始 portfolio_context（用于调试/审计）
            - timestamp: 分析完成时间 ISO8601
            - model: 实际使用的模型名
            - provider: 实际使用的提供商
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            # 1. 构建上下文
            context = await self._context_builder.build_context(user_id)
            logger.info("PortfolioAnalyzer: built context for user_id=%s", user_id)

            # 2. 获取 provider（model_type 为 provider）
            db = await get_database()
            tokens_doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
            provider = (model_type or "").strip().lower()
            if not provider or provider not in VALID_AI_AGENTS:
                provider = (
                    tokens_doc.get(PRIMARY_AI_AGENT_KEY) or llm_settings.LLM_PROVIDER or "qwen"
                ).strip().lower()
            if provider not in VALID_AI_AGENTS:
                provider = DEFAULT_AI_AGENT

            # 3. 获取 Token 与模型配置
            if provider == "grok":
                lst = _normalize_ai_list(tokens_doc, GROK_LIST_KEY, "grok_api")
            else:
                lst = _normalize_ai_list(tokens_doc, QWEN_LIST_KEY, "qwen_api")

            if not lst or not lst[0].get("token"):
                return {
                    "analysis": {
                        "error": "请先在 Token 配置中为该 Agent 添加 API Key",
                        "raw": "",
                    },
                    "raw_context": context,
                    "timestamp": timestamp,
                    "model": "",
                    "provider": provider,
                }

            token_val = lst[0]["token"].strip()
            role_config = await db["config"].find_one({"_id": CONFIG_AGENT_ROLE}) or {}
            selected_model = (role_config.get(f"selected_{provider}_model") or "").strip() or None
            cfg = get_agent_config(provider) or {}
            model_param = selected_model or cfg.get("model") or llm_settings.DEFAULT_MODEL
            api_url = cfg.get("url") or ""
            base_url = api_url.replace("/chat/completions", "").rstrip("/") if api_url else None

            # 4. 生成提示词
            prompt = await get_analysis_prompt(context, model_type=provider)
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "请基于上述 portfolio_context 给出投资建议，仅返回 JSON。"},
            ]

            # 5. 调用 LLM
            result = await self._llm_client.generate_response(
                messages=messages,
                model=model_param,
                provider=provider,
                temperature=cfg.get("temperature") or llm_settings.DEFAULT_TEMPERATURE,
                max_tokens=cfg.get("max_tokens") or llm_settings.MAX_TOKENS,
                api_key=token_val,
                base_url=base_url,
            )

            if not result.get("ok"):
                return {
                    "analysis": {
                        "error": result.get("error", "LLM 调用失败"),
                        "raw": "",
                    },
                    "raw_context": context,
                    "timestamp": timestamp,
                    "model": model_param or "",
                    "provider": provider,
                }

            content = result.get("content", "")
            parsed = _parse_json_from_response(content)
            used_model = result.get("model", model_param or "")
            used_provider = result.get("provider", provider)

            if parsed is None:
                return {
                    "analysis": {
                        "error": "LLM 返回无法解析为 JSON",
                        "raw": content[:500] + ("..." if len(content) > 500 else ""),
                    },
                    "raw_context": context,
                    "timestamp": timestamp,
                    "model": used_model,
                    "provider": used_provider,
                }

            return {
                "analysis": parsed,
                "raw_context": context,
                "timestamp": timestamp,
                "model": used_model,
                "provider": used_provider,
            }

        except Exception as e:
            logger.exception("PortfolioAnalyzer.analyze_portfolio error: %s", e)
            return {
                "analysis": {
                    "error": str(e),
                    "raw": "",
                },
                "raw_context": {},
                "timestamp": timestamp,
                "model": "",
                "provider": "",
            }
