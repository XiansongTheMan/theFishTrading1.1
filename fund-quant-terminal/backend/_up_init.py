p = "app/agent_config"
with open(p + "/__init__.py", "w", encoding="utf-8") as f:
    f.write("""# Agent config - get_agent_config(agent_name) returns config dict

from app.agent_config.grok import GROK_CONFIG, chat as chat_grok, test_token as test_grok_token
from app.agent_config.qwen import QWEN_CONFIG, chat as chat_qwen, test_token as test_qwen_token
from app.agent_config.common import build_messages

AGENT_CONFIGS = {
    "grok": GROK_CONFIG,
    "qwen": QWEN_CONFIG,
}


def get_agent_config(agent_name: str) -> dict | None:
    name = (agent_name or "").strip().lower()
    return AGENT_CONFIGS.get(name)


__all__ = ["get_agent_config", "AGENT_CONFIGS", "build_messages", "chat_grok", "chat_qwen", "test_grok_token", "test_qwen_token"]
""")
