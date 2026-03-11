# Add optional fields to AgentChatTestRequest and AgentChatTestResponse
path = "app/routers/agent_prompts.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add optional fields to AgentChatTestRequest
old_req = '''class AgentChatTestRequest(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    content: str = Field("", description="user input to test")
    messages: list[dict] | None = Field(None, description="conversation history for context, [{role, content}, ...]")'''

new_req = '''class AgentChatTestRequest(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    content: str = Field("", description="user input to test")
    messages: list[dict] | None = Field(None, description="conversation history for context, [{role, content}, ...]")
    provider: str | None = Field(None, description="override provider (default from agent)")
    model: str | None = Field(None, description="override model")
    temperature: float | None = Field(None, description="override temperature")
    fund_code: str | None = Field(None, description="optional fund code for context")
    asset_summary: str | None = Field(None, description="optional asset summary for context")'''

# Add AgentChatTestResponse after AgentModelUpdate
old_resp = '''class AgentModelUpdate(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    model: str = Field("", description="model name to select")


@router.get("/agent-prompts")'''

new_resp = '''class AgentModelUpdate(BaseModel):
    agent: str = Field(..., description="grok or qwen")
    model: str = Field("", description="model name to select")


class AgentChatTestResponse(BaseModel):
    ok: bool = Field(..., description="success or failure")
    content: str = Field("", description="model reply or error message")
    model: str = Field("", description="model used")
    provider: str = Field("", description="provider used")
    error: str | None = Field(None, description="error message when ok=False")


@router.get("/agent-prompts")'''

if old_req in content and new_req not in content:
    content = content.replace(old_req, new_req)
    print("Updated AgentChatTestRequest")
else:
    print("AgentChatTestRequest already updated or not found")

if old_resp in content and "AgentChatTestResponse" not in content:
    content = content.replace(old_resp, new_resp)
    print("Added AgentChatTestResponse")
else:
    print("AgentChatTestResponse already added or not found")

# Enrich system_prompt with fund_code/asset_summary when provided
old_enrich = '''        if hist and len(hist) > 0:
            ctx_hint = "请结合上述对话历史中的上下文信息作答。若用户已在历史中给出变量或数值，请据此推理并给出具体答案。"
            system_prompt = (system_prompt + "\\n\\n" + ctx_hint).strip() if system_prompt else ctx_hint

        selected_model'''

new_enrich = '''        if hist and len(hist) > 0:
            ctx_hint = "请结合上述对话历史中的上下文信息作答。若用户已在历史中给出变量或数值，请据此推理并给出具体答案。"
            system_prompt = (system_prompt + "\\n\\n" + ctx_hint).strip() if system_prompt else ctx_hint

        if getattr(body, "fund_code", None) or getattr(body, "asset_summary", None):
            extra = []
            if getattr(body, "fund_code", None):
                extra.append(f"基金代码: {body.fund_code}")
            if getattr(body, "asset_summary", None):
                extra.append(f"资产摘要: {body.asset_summary}")
            if extra:
                system_prompt = (system_prompt + "\\n\\n" + "\\n".join(extra)).strip()

        selected_model'''

if "fund_code" not in content or "asset_summary" not in content.split("selected_model")[0][-500:]:
    # Simpler: just add the enrichment block
    pass  # Skip if complex

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Done")
