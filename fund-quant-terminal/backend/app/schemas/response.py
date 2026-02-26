# =====================================================
# 统一 API 响应模型
# 所有端点返回 {code: 200, data: {}, message: ""}
# =====================================================

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """标准 API 响应格式"""

    code: int = Field(default=200, description="状态码")
    data: T | None = Field(default=None, description="响应数据")
    message: str = Field(default="", description="提示信息")


def api_success(data: Any = None, message: str = "") -> dict:
    """构造成功响应"""
    return {"code": 200, "data": data, "message": message}


def api_error(code: int = 500, message: str = "服务器错误", data: Any = None) -> dict:
    """构造错误响应"""
    return {"code": code, "data": data, "message": message}
