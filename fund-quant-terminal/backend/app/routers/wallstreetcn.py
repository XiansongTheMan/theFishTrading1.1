# =====================================================
# 华尔街见闻 API 路由
# POST /api/wallstreetcn/test 测试各类接口
# =====================================================

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.database import get_database
from app.schemas.response import api_success
from app.services.wallstreetcn_service import WallStreetCNService
from app.utils.logger import logger

router = APIRouter()
_wscn_service: Optional[WallStreetCNService] = None


def _get_service() -> WallStreetCNService:
    global _wscn_service
    if _wscn_service is None:
        _wscn_service = WallStreetCNService()
    return _wscn_service


class WallStreetCNTestRequest(BaseModel):
    """华尔街见闻测试请求"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"type": "lives", "limit": 10},
                {"type": "articles", "channel": "news", "limit": 10},
                {"type": "search", "keyword": "贵州茅台", "limit": 10},
                {"type": "quote", "code": "600519", "limit": 10},
                {"type": "keyword", "keyword": "美联储", "limit": 10},
            ]
        }
    )

    type: Literal["lives", "articles", "search", "quote", "keyword"] = Field(
        ...,
        description="接口类型: lives=快讯, articles=文章, search=股票搜索, quote=行情, keyword=关键词搜索",
    )
    code: Optional[str] = Field(None, description="股票/标的代码，type=quote 时必填")
    keyword: Optional[str] = Field(None, description="关键词/搜索词，type=search/keyword 时必填")
    limit: int = Field(default=10, ge=1, le=100, description="返回条数")
    channel: Optional[str] = Field(default="news", description="文章频道，type=articles 时使用")
    cursor: int = Field(default=0, ge=0, description="分页游标，type=lives 时使用")
    save_to_db: bool = Field(default=False, description="是否将解析结果保存至 decision_logs（仅 lives/articles/keyword）")

    @model_validator(mode="after")
    def validate_code_or_keyword(self):
        if self.type == "quote" and not (self.code and self.code.strip()):
            raise ValueError("type=quote 时需提供 code")
        if self.type in ("search", "keyword") and not (self.keyword and self.keyword.strip()):
            raise ValueError("type=search 或 keyword 时需提供 keyword")
        return self


@router.post(
    "/test",
    summary="华尔街见闻接口测试",
    description="""测试华尔街见闻 API 各类接口，根据 type 调用对应方法并返回原始 JSON。

**type 说明：**
- **lives**: 快讯/实时新闻，无需 code/keyword
- **articles**: 文章列表，可选 channel（默认 news）
- **search**: 股票搜索，需提供 keyword 作为搜索词
- **quote**: 行情查询，需提供 code（股票代码）
- **keyword**: 关键词搜索，需提供 keyword
""",
    responses={
        200: {"description": "成功，返回华尔街见闻 API 原始数据"},
        400: {"description": "参数校验失败"},
        500: {"description": "服务异常"},
    },
)
async def wallstreetcn_test(
    req: WallStreetCNTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """
    测试华尔街见闻接口。通过 service 拉取并解析，可选保存至 decision_logs。
    """
    try:
        service = _get_service()
        t = req.type
        limit = req.limit
        channel = (req.channel or "news").strip() or "news"
        keyword = (req.keyword or "").strip() or None
        code = (req.code or "").strip() or None

        raw, parsed = await service.fetch_and_parse(
            type_=t,
            limit=limit,
            cursor=req.cursor,
            channel=channel,
            keyword=keyword,
            code=code,
        )

        saved_count = 0
        if req.save_to_db and parsed:
            saved_count = await service.save_to_decision_logs(db, parsed, type_=t)

        data = {"type": t, "data": raw}
        if parsed:
            data["parsed"] = parsed
        if saved_count > 0:
            data["saved_count"] = saved_count

        return api_success(data=data)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("wallstreetcn_test 异常: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
