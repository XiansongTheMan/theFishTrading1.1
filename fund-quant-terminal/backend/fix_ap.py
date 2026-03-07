import re
p = "app/routers/agent_prompts.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()
# Remove _build_messages, _chat_grok, _chat_qwen (from def _build_messages to end of _chat_qwen)
c = re.sub(r'\n\ndef _build_messages\(.*?\n    return msgs\n\n', '\n\n', c, flags=re.DOTALL)
c = re.sub(r'\ndef _chat_grok\(.*?\n    except \(URLError, OSError, json\.JSONDecodeError\) as e:\n        return False, str\(e\) or "\u8fde\u63a5\u5931\u8d25"\n\n', '\n', c, flags=re.DOTALL)
c = re.sub(r'\ndef _chat_qwen\(.*?\n    except \(URLError, OSError, json\.JSONDecodeError\) as e:\n        return False, str\(e\) or "\u8fde\u63a5\u5931\u8d25"\n\n', '\n', c, flags=re.DOTALL)
# Add import
c = c.replace("from app.agent_config import get_agent_config", "from app.agent_config import get_agent_config, chat_grok, chat_qwen")
# Remove unused imports
c = c.replace("import json\nfrom datetime import datetime\nfrom urllib.request import Request, urlopen\nfrom urllib.error import HTTPError, URLError\n\n", "from datetime import datetime\n\n")
# Replace _chat_grok with chat_grok, _chat_qwen with chat_qwen
c = c.replace("_chat_grok", "chat_grok").replace("_chat_qwen", "chat_qwen")
with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("done")
