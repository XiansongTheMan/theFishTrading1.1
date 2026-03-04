# -*- coding: utf-8 -*-
"""Update wallstreetcn router to use service"""
p = "app/routers/wallstreetcn.py"
with open(p, "r", encoding="utf-8") as f:
    c = f.read()

# Add save_to_db
c = c.replace(
    '    cursor: int = Field(default=0, ge=0, description="分页游标，type=lives 时使用")\n\n    @model_validator',
    '    cursor: int = Field(default=0, ge=0, description="分页游标，type=lives 时使用")\n    save_to_db: bool = Field(default=False, description="是否将解析结果保存至 decision_logs")\n\n    @model_validator'
)

# Replace endpoint body - from "async def wallstreetcn_test(req:" to end of function
import re
old = r'async def wallstreetcn_test\(req: WallStreetCNTestRequest\) -> dict:\s+"""\s+测试华尔街见闻接口\s+"""\s+try:.*?raise HTTPException\(status_code=500, detail=str\(e\)\)'
new = '''async def wallstreetcn_test(
    req: WallStreetCNTestRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
) -> dict:
    """测试华尔街见闻接口。通过 service 拉取并解析，可选保存至 decision_logs。"""
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
        raise HTTPException(status_code=500, detail=str(e))'''

c = re.sub(r'async def wallstreetcn_test\(req: WallStreetCNTestRequest\) -> dict:.*?raise HTTPException\(status_code=500, detail=str\(e\)\)', new, c, flags=re.DOTALL)

with open(p, "w", encoding="utf-8") as f:
    f.write(c)
print("Updated")
