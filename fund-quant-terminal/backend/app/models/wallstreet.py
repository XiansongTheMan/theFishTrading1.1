# =====================================================
# 华尔街见闻 API 响应模型
# =====================================================

from typing import Any

from pydantic import BaseModel, Field


class WallStreetResponse(BaseModel):
    """华尔街见闻测试接口响应数据"""

    type: str = Field(..., description="请求类型: lives|articles|search|quote|keyword")
    data: Any = Field(..., description="华尔街见闻 API 原始 JSON 响应")
