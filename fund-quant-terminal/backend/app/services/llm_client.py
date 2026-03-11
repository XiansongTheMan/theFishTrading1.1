# =====================================================
# 多 LLM 统一调用客户端
# 基于 OpenAI SDK 兼容接口，支持 Grok、Qwen 等提供商
# 支持 tenacity 限流重试、标准化错误映射、API Key 脱敏日志
# Proxy: 支持 HTTP_PROXY/HTTPS_PROXY 环境变量，OpenAI 客户端会自动使用
# =====================================================

from typing import Any

from fastapi import Depends
from openai import AsyncOpenAI, AuthenticationError, RateLimitError, APIConnectionError, APITimeoutError, BadRequestError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import llm_settings
from app.utils.logger import logger

# 支持的提供商注册表：provider -> (base_url_env_key, api_key_env_key)
PROVIDER_REGISTRY = {
    "grok": ("GROK_BASE_URL", "GROK_API_KEY"),
    "qwen": ("QWEN_BASE_URL", "QWEN_API_KEY"),
}

# 各 provider 的默认模型（当 model 未指定时使用，避免 grok 模型用于 qwen 等）
PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "grok": "grok-4-fast-reasoning",
    "qwen": "qwen-turbo",
}


def _mask_api_key(key: str | None) -> str:
    """API Key 脱敏：返回 sk-*** + 后4位，若长度<=8 则返回 ***"""
    if not key or not isinstance(key, str):
        return "***"
    k = key.strip()
    if len(k) <= 8:
        return "***"
    return "sk-***" + k[-4:]


@retry(
    retry=retry_if_exception_type((RateLimitError, APIConnectionError, APITimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _create_completion_with_retry(
    client: AsyncOpenAI, model: str, messages: list, temp: float, max_tok: int
):
    """内部 API 调用，对限流/连接/超时错误自动重试"""
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temp,
        max_tokens=max_tok,
        stream=False,
    )


def _map_openai_error(e: Exception) -> str:
    """将 OpenAI 异常映射为标准化中文错误信息"""
    if isinstance(e, AuthenticationError):
        return "API Key 无效或已过期"
    if isinstance(e, RateLimitError):
        return "请求过于频繁，请稍后重试"
    if isinstance(e, APITimeoutError):
        return "请求超时"
    if isinstance(e, APIConnectionError):
        return "网络连接失败"
    if isinstance(e, BadRequestError):
        return getattr(e, "message", str(e)) or "请求参数错误"
    return str(e) or "未知错误"


def get_llm_client() -> "MultiLLMClient":
    """FastAPI Depends：返回 MultiLLMClient 单例"""
    return MultiLLMClient()


class MultiLLMClient:
    """
    多 LLM 统一调用客户端（单例，通过 Depends 注入）

    支持 Grok、Qwen 等 OpenAI 兼容接口的提供商。
    根据 provider 动态初始化 AsyncOpenAI，调用 chat.completions.create。

    Proxy: 支持 HTTP_PROXY/HTTPS_PROXY 环境变量，OpenAI 客户端会自动使用。
    """

    def __init__(self) -> None:
        self._clients: dict[str, AsyncOpenAI] = {}

    def _get_client(self, provider: str) -> AsyncOpenAI:
        """根据 provider 获取或创建 AsyncOpenAI 客户端"""
        if provider not in PROVIDER_REGISTRY:
            raise ValueError(f"Unknown LLM provider: {provider}. Supported: {list(PROVIDER_REGISTRY.keys())}")

        if provider in self._clients:
            return self._clients[provider]

        base_key, key_key = PROVIDER_REGISTRY[provider]
        base_url = getattr(llm_settings, base_key, "")
        api_key = getattr(llm_settings, key_key, "")

        if not api_key or not str(api_key).strip():
            raise ValueError(f"API key not configured for provider: {provider}")

        client = AsyncOpenAI(
            base_url=base_url.rstrip("/") if base_url else None,
            api_key=api_key.strip(),
        )
        self._clients[provider] = client
        logger.info("MultiLLMClient: initialized %s client, base_url=%s", provider, base_url or "(default)")
        return client

    # 各 provider 的默认模型，避免跨 provider 使用错误模型
    PROVIDER_DEFAULT_MODELS: dict[str, str] = {
        "grok": "grok-4-fast-reasoning",
        "qwen": "qwen-turbo",
    }

    def _resolve_provider_and_model(
        self,
        model: str | None,
        provider: str | None,
    ) -> tuple[str, str]:
        """
        解析实际使用的 provider 和 model。
        若 provider 未指定，使用 llm_settings.LLM_PROVIDER。
        若 model 未指定，使用该 provider 的默认模型（避免 grok 模型用于 qwen 等）。
        """
        p = (provider or "").strip().lower() or llm_settings.LLM_PROVIDER.strip().lower()
        if p not in PROVIDER_REGISTRY:
            p = llm_settings.LLM_PROVIDER.strip().lower()
        m = (model or "").strip()
        if not m:
            m = self.PROVIDER_DEFAULT_MODELS.get(p) or llm_settings.DEFAULT_MODEL
        return p, m

    async def generate_response(
        self,
        messages: list[dict],
        model: str | None = None,
        provider: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> dict[str, Any]:
        """
        调用 LLM 生成回复（非流式）。

        Args:
            messages: OpenAI 格式消息列表 [{"role": "user"|"assistant"|"system", "content": "..."}]
            model: 模型名，如 grok-4-fast-reasoning、qwen-max。不传则用 DEFAULT_MODEL
            provider: 提供商 grok 或 qwen。不传则用 LLM_PROVIDER
            temperature: 采样温度，不传则用 DEFAULT_TEMPERATURE
            max_tokens: 最大生成 token 数，不传则用 MAX_TOKENS

        Returns:
            成功: {"ok": True, "content": str, "model": str, "provider": str, "usage": {...} | None}
            失败: {"ok": False, "error": str}
        """
        # 输入校验
        if not messages or not isinstance(messages, list):
            logger.warning("MultiLLMClient.generate_response: empty or invalid messages")
            return {"ok": False, "error": "messages must be a non-empty list"}

        for i, m in enumerate(messages):
            if not isinstance(m, dict) or "role" not in m or "content" not in m:
                logger.warning("MultiLLMClient.generate_response: invalid message at index %d", i)
                return {"ok": False, "error": f"message[{i}] must have role and content"}

        try:
            used_provider, used_model = self._resolve_provider_and_model(model, provider)
            used_key = api_key.strip() if api_key else None
            if api_key and base_url:
                client = AsyncOpenAI(api_key=api_key.strip(), base_url=base_url.rstrip("/"))
                logger.info(
                    "MultiLLMClient: using per-request credentials for %s, api_key=%s",
                    used_provider,
                    _mask_api_key(api_key),
                )
            else:
                client = self._get_client(used_provider)
                base_key, key_key = PROVIDER_REGISTRY[used_provider]
                used_key = getattr(llm_settings, key_key, "")

            temp = temperature if temperature is not None else llm_settings.DEFAULT_TEMPERATURE
            max_tok = max_tokens if max_tokens is not None else llm_settings.MAX_TOKENS

            logger.info(
                "MultiLLMClient.generate_response REQUEST: provider=%s model=%s messages_count=%d temperature=%s max_tokens=%d api_key=%s",
                used_provider,
                used_model,
                len(messages),
                temp,
                max_tok,
                _mask_api_key(used_key),
            )

            response = await _create_completion_with_retry(
                client, used_model, messages, temp, max_tok
            )

            choice = response.choices[0] if response.choices else None
            content = (choice.message.content if choice and choice.message else "") or ""
            usage = response.usage.model_dump() if response.usage else None

            logger.info(
                "MultiLLMClient.generate_response RESPONSE: provider=%s model=%s content_len=%d usage=%s",
                used_provider,
                used_model,
                len(content),
                usage,
            )

            return {
                "ok": True,
                "content": content,
                "model": used_model,
                "provider": used_provider,
                "usage": usage,
            }
        except ValueError as e:
            logger.warning("MultiLLMClient.generate_response: validation error %s", e)
            return {"ok": False, "error": str(e)}
        except (AuthenticationError, RateLimitError, APITimeoutError, APIConnectionError, BadRequestError) as e:
            err_msg = _map_openai_error(e)
            logger.warning("MultiLLMClient.generate_response: %s -> %s", type(e).__name__, err_msg)
            return {"ok": False, "error": err_msg}
        except Exception as e:
            logger.exception("MultiLLMClient.generate_response: %s", e)
            return {"ok": False, "error": str(e)}
