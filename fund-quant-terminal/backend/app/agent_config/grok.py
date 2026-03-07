# Grok (x.ai) 大模型配置与调用

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .common import build_messages

# Grok API 配置：接口地址、默认模型、最大 token、对话/测试超时（秒）
GROK_CONFIG = {
    "url": "https://api.x.ai/v1/chat/completions",
    "model": "grok-4-fast-reasoning",
    "max_tokens": 2000,
    "timeout_chat": 90,
    "timeout_test": 60,
}

# Grok 可用模型列表（x.ai API）
GROK_MODELS = [
    {"value": "grok-2-1212", "label": "grok-2-1212（推荐）"},
    {"value": "grok-3", "label": "grok-3"},
    {"value": "grok-3-mini", "label": "grok-3-mini"},
    {"value": "grok-4-1-fast-non-reasoning", "label": "grok-4-1-fast-non-reasoning"},
    {"value": "grok-4-fast-reasoning", "label": "grok-4-fast-reasoning"},
    {"value": "grok-4-fast-non-reasoning", "label": "grok-4-fast-non-reasoning"},
]

def chat(token: str, user_content: str, messages: list[dict] | None = None, system_prompt: str | None = None, model: str | None = None) -> tuple[bool, str]:
    """
    调用 Grok 对话接口，发送用户输入并获取模型回复。
    支持多轮对话：messages 为历史消息列表，当前 user_content 会追加到末尾。
    system_prompt: 可选，置于首条，用于角色设定或强调结合历史作答。
    返回: (成功与否, 模型回复内容或错误信息)
    """
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        cfg = GROK_CONFIG
        headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
            "User-Agent": "fund-quant-terminal/1.0",
        }
        api_messages = build_messages(messages, user_content, system_prompt)
        model_name = (model or "").strip() or cfg["model"]
        body = json.dumps({
            "model": model_name,
            "messages": api_messages,
            "max_tokens": cfg["max_tokens"],
            "stream": False,
        }).encode("utf-8")
        req = Request(cfg["url"], data=body, headers=headers, method="POST")
        with urlopen(req, timeout=cfg["timeout_chat"]) as resp:
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

def test_token(token: str, model: str | None = None) -> tuple[bool, str]:
    """
    测试 Grok API Token 是否有效。
    发送极简请求（"hi"，max_tokens=5）验证连接，用于 Token 配置页的连接测试。
    返回: (成功与否, 空字符串或错误信息)
    """
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        cfg = GROK_CONFIG
        headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
            "User-Agent": "fund-quant-terminal/1.0",
        }
        model_name = (model or "").strip() or cfg["model"]
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
            "stream": False,
        }).encode("utf-8")
        req = Request(cfg["url"], data=body, headers=headers, method="POST")
        with urlopen(req, timeout=cfg["timeout_test"]) as resp:
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
            msg = msg + "（403：API Key 权限不足、团队被限制，或所在地区无法访问 x.ai）"
        return False, msg
    except OSError as e:
        err_msg = str(e) or "连接失败"
        if "timed out" in err_msg.lower() or "timeout" in err_msg.lower():
            err_msg = "连接超时（约 60 秒），请检查网络或代理，x.ai 在国内需代理"
        return False, err_msg
    except (URLError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"

