# =====================================================
# Grok 角色提示词模型
# =====================================================

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class GrokPrompt(BaseModel):
    """Grok 角色提示词文档"""

    id: Optional[str] = Field(None, description="文档 ID")
    content: str = Field(..., description="提示词内容")
    version: int = Field(default=1, ge=1, description="版本号")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
