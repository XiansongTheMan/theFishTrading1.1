# 通义千问 (DashScope) 大模型配置与调用

import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from .common import build_messages

# 通义千问 API 配置：接口地址、默认模型（qwen3-max 为最强推理）、最大 token、对话/测试超时（秒）
QWEN_CONFIG = {
    "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "model": "qwen3-max",
    "max_tokens": 2000,
    "timeout_chat": 60,
    "timeout_test": 15,
}

# 通义千问可用模型列表（DashScope 兼容接口，官方接口失败时的兜底）
QWEN_MODELS = [
    {"value": "qwen-turbo", "label": "qwen-turbo（快速）"},
    {"value": "qwen-turbo-latest", "label": "qwen-turbo-latest"},
    {"value": "qwen3.5-flash", "label": "qwen3.5-flash（推荐）"},
    {"value": "qwen-flash", "label": "qwen-flash"},
    {"value": "qwen-flash-latest", "label": "qwen-flash-latest"},
    {"value": "qwen-plus", "label": "qwen-plus"},
    {"value": "qwen-plus-latest", "label": "qwen-plus-latest"},
    {"value": "qwen3.5-plus", "label": "qwen3.5-plus"},
    {"value": "qwen3-max", "label": "qwen3-max（最强推理，推荐）"},
    {"value": "qwen-max", "label": "qwen-max"},
    {"value": "qwen-max-latest", "label": "qwen-max-latest"},
    {"value": "qwen-long", "label": "qwen-long（长文本）"},
    {"value": "qwen-long-latest", "label": "qwen-long-latest"},
    {"value": "qwen2.5-72b-instruct", "label": "qwen2.5-72b-instruct"},
    {"value": "qwen2.5-32b-instruct", "label": "qwen2.5-32b-instruct"},
    {"value": "qwen2.5-14b-instruct", "label": "qwen2.5-14b-instruct"},
    {"value": "qwen2.5-7b-instruct", "label": "qwen2.5-7b-instruct"},
    {"value": "qwen2.5-1.5b-instruct", "label": "qwen2.5-1.5b-instruct"},
    {"value": "qwen2-72b-instruct", "label": "qwen2-72b-instruct"},
    {"value": "qwen2-7b-instruct", "label": "qwen2-7b-instruct"},
    {"value": "qwen2-1.5b-instruct", "label": "qwen2-1.5b-instruct"},
    {"value": "qwen2.5-coder-32b-instruct", "label": "qwen2.5-coder-32b（代码）"},
    {"value": "qwen2.5-coder-7b-instruct", "label": "qwen2.5-coder-7b（代码）"},
    {"value": "qwen-vl-max", "label": "qwen-vl-max（视觉）"},
    {"value": "qwen-vl-plus", "label": "qwen-vl-plus（视觉）"},
    {"value": "qwen2-0.5b-instruct", "label": "qwen2-0.5b-instruct"},
]

QWEN_MODELS_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/models"


def fetch_models(token: str) -> list[dict] | None:
    """
    从 DashScope 官方接口获取可用模型列表（OpenAI 兼容格式 GET /v1/models）。
    成功返回 [{"value": str, "label": str}, ...]，失败返回 None（调用方使用 QWEN_MODELS 兜底）。
    """
    if not token or not token.strip():
        return None
    try:
        headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
        }
        req = Request(QWEN_MODELS_URL, headers=headers, method="GET")
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        items = data.get("data") or []
        if not isinstance(items, list):
            return None
        out = []
        seen = set()
        for m in items:
            mid = (m.get("id") or m.get("model") or "").strip()
            if mid and mid not in seen:
                seen.add(mid)
                out.append({"value": mid, "label": mid})
        return out if out else None
    except Exception:
        return None

def chat(token: str, user_content: str, messages: list[dict] | None = None, system_prompt: str | None = None, model: str | None = None) -> tuple[bool, str]:
    """
    调用通义千问对话接口，发送用户输入并获取模型回复。
    支持多轮对话：messages 为历史消息列表，参考阿里 Agent API 多轮对话格式。
    system_prompt: 可选，置于首条，用于角色设定或强调结合历史作答。
    返回: (成功与否, 模型回复内容或错误信息)
    """
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        cfg = QWEN_CONFIG
        headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
        }
        api_messages = build_messages(messages, user_content, system_prompt)
        model_name = (model or "").strip() or cfg["model"]
        body = json.dumps({
            "model": model_name,
            "messages": api_messages,
            "max_tokens": cfg["max_tokens"],
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
    测试通义千问 API Token 是否有效。
    发送极简请求验证连接，用于 Token 配置页的连接测试。
    返回: (成功与否, 空字符串或错误信息)
    """
    if not token or not token.strip():
        return False, "Token 为空"
    try:
        cfg = QWEN_CONFIG
        headers = {
            "Authorization": "Bearer " + token.strip(),
            "Content-Type": "application/json",
        }
        model_name = (model or "").strip() or cfg["model"]
        body = json.dumps({
            "model": model_name,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5,
        }).encode("utf-8")
        req = Request(cfg["url"], data=body, headers=headers, method="POST")
        with urlopen(req, timeout=cfg["timeout_test"]) as resp:
            data = json.loads(resp.read().decode())
            if data.get("choices") and len(data["choices"]) > 0:
                return True, ""
            return False, "接口返回异常"
    except HTTPError as e:
        try:
            err_body = e.read().decode()
            err_data = json.loads(err_body)
            msg = err_data.get("error", {}).get("message", err_body) or str(e)
        except Exception:
            msg = str(e) or "连接失败"
        return False, msg
    except (URLError, OSError, json.JSONDecodeError) as e:
        return False, str(e) or "连接失败"