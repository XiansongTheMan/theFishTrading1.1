# 大模型对话消息构建（共享逻辑）

def build_messages(
    history: list[dict] | None,
    user_content: str,
    system_prompt: str | None = None,
) -> list[dict]:
    """
    构建 API 所需的 messages 数组：可选 system + 历史对话 + 当前用户输入。
    用于多轮对话上下文，符合 OpenAI/DashScope 兼容接口格式。
    限制历史长度为最近 20 轮（40 条消息），单条内容截断至 4000 字符，以控制 token 消耗。
    system_prompt: 可选，置于首条，用于角色设定或强调结合历史作答。
    返回: [{"role": "system"|"user"|"assistant", "content": str}, ...]
    """
    content = (user_content or "hi").strip()[:4000]
    msgs: list[dict] = []

    sys = (system_prompt or "").strip()
    if sys:
        msgs.append({"role": "system", "content": sys[:4000]})

    if not history or len(history) == 0:
        msgs.append({"role": "user", "content": content})
        return msgs

    trimmed = history[-40:] if len(history) > 40 else history
    for m in trimmed:
        msgs.append({"role": m.get("role", "user"), "content": (m.get("content") or "")[:4000]})
    msgs.append({"role": "user", "content": content})
    return msgs
