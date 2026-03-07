# 大模型 Agent 配置统一入口

from app.agent_config.grok import GROK_CONFIG, GROK_MODELS, chat as chat_grok, test_token as test_grok_token
from app.agent_config.qwen import QWEN_CONFIG, QWEN_MODELS, chat as chat_qwen, test_token as test_qwen_token, fetch_models as fetch_qwen_models
from app.agent_config.common import build_messages

# 按 agent 名称索引的配置字典
AGENT_CONFIGS = {
    "grok": GROK_CONFIG,
    "qwen": QWEN_CONFIG,
}


def get_agent_config(agent_name: str) -> dict | None:
    """
    根据 agent 名称获取对应配置字典。
    返回包含 url、model、max_tokens、timeout_chat、timeout_test 等字段的配置，
    若名称不存在则返回 None。
    """
    name = (agent_name or "").strip().lower()
    return AGENT_CONFIGS.get(name)


__all__ = ["get_agent_config", "AGENT_CONFIGS", "build_messages", "chat_grok", "chat_qwen", "test_grok_token", "test_qwen_token", "GROK_MODELS", "QWEN_MODELS", "fetch_qwen_models"]
