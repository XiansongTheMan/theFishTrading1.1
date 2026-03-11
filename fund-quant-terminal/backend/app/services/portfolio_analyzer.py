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
from app.routers.config_router import CONFIG_ID, QWEN_LIST_KEY, _normalize_ai_list
from app.agent_config import get_agent_config
from app.config import llm_settings
from app.utils.logger import logger

ANALYSIS_MODEL = "qwen3-max"  # 投资组合分析强制使用 Qwen 最强推理模型


def _parse_json_from_response(raw: str) -> dict | None:
    """
    从 LLM 返回内容中安全解析 JSON。
    支持：markdown 代码块、<thinking> 后的 JSON、前后缀文本、尾部逗号修复。
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip()
    if not s:
        return None

    def _try_parse(text: str) -> dict | None:
        if not text or not text.strip():
            return None
        t = text.strip()
        # 修复常见问题：尾部逗号、单引号键名
        t = re.sub(r",\s*}", "}", t)
        t = re.sub(r",\s*]", "]", t)
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            pass
        return None

    # 1. 移除 <thinking>...</thinking> 等推理块（qwen3-max 可能输出）
    for tag in (r"<thinking>[\s\S]*?</thinking>", r"<reasoning>[\s\S]*?</reasoning>", r"<thought>[\s\S]*?</thought>"):
        s = re.sub(tag, "", s, flags=re.IGNORECASE)

    # 2. Markdown ```json ... ``` 或 ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", s)
    if match:
        parsed = _try_parse(match.group(1))
        if parsed:
            return parsed

    # 3. 找第一个 { 到最后一个 } 的完整块（兼容前后有中文说明）
    start = s.find("{")
    end = s.rfind("}")
    if start >= 0 and end > start:
        block = s[start : end + 1]
        parsed = _try_parse(block)
        if parsed:
            return parsed

    # 4. 直接解析全文
    parsed = _try_parse(s)
    if parsed:
        return parsed

    logger.warning("portfolio_analyzer: failed to parse JSON, len=%d, preview=%s", len(s), repr(s[:200]))
    return None


def _validate_and_normalize_analysis(parsed: dict, total_value: float) -> dict:
    """
    校验并规范化分析结果：reason 必须是字符串，disclaimer 固定中文，amount 限制。
    """
    if not isinstance(parsed, dict):
        return parsed
    out = dict(parsed)

    # reason 必须是字符串
    reason_val = out.get("reason")
    if reason_val is not None and not isinstance(reason_val, str):
        out["reason"] = json.dumps(reason_val, ensure_ascii=False) if isinstance(reason_val, dict) else str(reason_val)

    # disclaimer 固定
    out["disclaimer"] = "本分析仅供参考，不构成投资建议，投资有风险，请自行决策。"

    # amount 不得超过 total_value * 0.5
    if total_value and total_value > 0:
        amt = out.get("amount")
        if isinstance(amt, (int, float)) and amt > total_value * 0.5:
            out["amount"] = round(total_value * 0.5, 2)
            logger.warning("portfolio_analyzer: amount 超过限制已修正为 total_value*0.5")

    return out


def get_portfolio_analyzer() -> "PortfolioAnalyzer":
    """FastAPI Depends：返回 PortfolioAnalyzer 实例"""
    return PortfolioAnalyzer()


class PortfolioAnalyzer:
    """
    投资组合分析器。
    强制使用 qwen3-max 保证分析质量，支持 JSON 解析重试与 schema 校验。
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
        强制使用 qwen3-max 模型，保证推理质量与 grounding。
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        try:
            context = await self._context_builder.build_context(user_id)
            news_count = len(context.get("recent_news") or [])
            # 粗略估算 context tokens（约 4 字符/token）
            context_str = json.dumps(context, ensure_ascii=False)
            approx_tokens = len(context_str) // 4
            logger.info(
                "Using Qwen3-Max strongest model | Context tokens: ~%d | News referenced: %d",
                approx_tokens, news_count,
            )

            db = await get_database()
            tokens_doc = await db["config"].find_one({"_id": CONFIG_ID}) or {}
            # 投资组合分析强制使用 qwen + qwen3-max
            provider = "qwen"
            lst = _normalize_ai_list(tokens_doc, QWEN_LIST_KEY, "qwen_api")

            if not lst or not lst[0].get("token"):
                return {
                    "analysis": {
                        "error": "请先在 Token 配置中为 Qwen 添加 API Key",
                        "raw": "",
                    },
                    "raw_context": context,
                    "timestamp": timestamp,
                    "model": ANALYSIS_MODEL,
                    "provider": provider,
                }

            token_val = lst[0]["token"].strip()
            cfg = get_agent_config(provider) or {}
            model_param = ANALYSIS_MODEL
            api_url = cfg.get("url") or ""
            base_url = api_url.replace("/chat/completions", "").rstrip("/") if api_url else None

            prompt = await get_analysis_prompt(context, model_type=provider)
            messages = [
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": "请基于上述 portfolio_context 给出投资建议。你必须只输出一个纯 JSON 对象（以 { 开头、以 } 结尾），不要输出任何解释、markdown 代码块、或前后缀文字。",
                },
            ]

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
                    "model": model_param,
                    "provider": provider,
                }

            content = result.get("content", "")
            parsed = _parse_json_from_response(content)

            # 解析失败时重试一次（strip 常见前缀）
            if parsed is None and content:
                for prefix in ("分析结果：", "建议：", "根据分析，", "```json\n", "```"):
                    stripped = content.strip()
                    if stripped.startswith(prefix):
                        stripped = stripped[len(prefix):].strip()
                    if stripped.endswith("```"):
                        stripped = stripped[:-3].strip()
                    parsed = _parse_json_from_response(stripped)
                    if parsed:
                        break

            if parsed is None:
                return {
                    "analysis": {
                        "error": "LLM 返回无法解析为 JSON",
                        "raw": content[:500] + ("..." if len(content) > 500 else ""),
                    },
                    "raw_context": context,
                    "timestamp": timestamp,
                    "model": model_param,
                    "provider": provider,
                }

            total_value = float((context.get("asset_summary") or {}).get("total_value") or 0)
            normalized = _validate_and_normalize_analysis(parsed, total_value)

            return {
                "analysis": normalized,
                "raw_context": context,
                "timestamp": timestamp,
                "model": result.get("model", model_param),
                "provider": provider,
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
