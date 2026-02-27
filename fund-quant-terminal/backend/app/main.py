# =====================================================
# FastAPI 主应用入口
# 配置 CORS、路由、生命周期（@asynccontextmanager）、全局异常处理、日志
# APScheduler 定时新闻采集（每 4 小时）
# =====================================================

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_database, get_database
from app.utils.logger import logger
from app.routers import assets, config_router, data, decisions, grok, mongo, news
from app.schemas.response import api_success

WATCHED_FUNDS_CONFIG_ID = "watched_funds"
_scheduler: AsyncIOScheduler | None = None


async def _scheduled_news_fetch() -> None:
    """定时任务：从 config 读取关注的基金，抓取 RSS 新闻并写入 news_raw"""
    try:
        db = await get_database()
        doc = await db["config"].find_one({"_id": WATCHED_FUNDS_CONFIG_ID})
        fund_codes = list(doc.get("fund_codes", [])) if doc else []
        fund_codes = [str(c).strip().split(".")[0].zfill(6) for c in fund_codes if c]

        from app.services.news_fetch import NewsFetchService
        news_service = NewsFetchService()
        total = 0

        for fc in fund_codes:
            try:
                items = await news_service.fetch_and_save(db, fund_code=fc, days=3)
                total += len(items)
            except Exception as e:
                logger.warning("定时新闻采集 单只基金 %s 失败: %s", fc, e)

        general = await news_service.fetch_and_save(db, fund_code=None, days=3)
        total += len(general)

        logger.info("新闻采集完成，共%d条", total)
    except Exception as e:
        logger.exception("定时新闻采集失败: %s", e)


def _get_grok_prompt_path() -> Path:
    """项目根目录下的 GROK_ROLE_PROMPT.md（backend/app 往上两级为 backend，再两级为项目根）"""
    return Path(__file__).resolve().parent.parent.parent.parent / "GROK_ROLE_PROMPT.md"


async def _sync_grok_prompt_to_file():
    """从数据库读取最新 Grok 角色设定，覆盖写入 GROK_ROLE_PROMPT.md"""
    try:
        db = await get_database()
        doc = await db["grok_prompts"].find_one({}, sort=[("version", -1)])
        if not doc or not doc.get("content"):
            logger.info("数据库中暂无 Grok 角色设定，跳过 GROK_ROLE_PROMPT.md 同步")
            return
        path = _get_grok_prompt_path()
        await asyncio.to_thread(path.write_text, doc["content"], encoding="utf-8")
        logger.info("已从数据库同步 Grok 角色设定至 %s (v%s)", path, doc.get("version", "?"))
    except Exception as e:
        logger.warning("同步 GROK_ROLE_PROMPT.md 失败: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：startup 创建索引，shutdown 关闭 Motor 客户端"""
    global _scheduler
    from app.database import create_indexes

    # ----- Startup -----
    try:
        db = await get_database()
        await db.command("ping")
        logger.info("MongoDB 连接成功, 数据库: %s", settings.MONGODB_DB_NAME)

        await create_indexes()
        logger.info("Database indexes created successfully")

        doc = await db["config"].find_one({"_id": "tokens"})
        if doc and doc.get("tokens", {}).get("tushare"):
            from app.routers.data import data_service
            data_service.update_tushare_token(doc["tokens"]["tushare"])
            logger.info("已从配置加载 Tushare Token")

        await _sync_grok_prompt_to_file()

        _scheduler = AsyncIOScheduler()
        _scheduler.add_job(_scheduled_news_fetch, "interval", hours=4, id="news_fetch")
        _scheduler.start()
        logger.info("APScheduler 已启动，新闻采集每 4 小时执行")
    except Exception as e:
        logger.error("MongoDB 连接失败: %s", e)
        raise

    yield

    # ----- Shutdown -----
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("APScheduler 已关闭")
    await close_database()
    logger.info("Motor client closed")


app = FastAPI(
    title="Fund Quant Terminal API",
    description="基金量化终端 - 数据与决策管理后端",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

def _error_response(code: int, message: str, detail: Any = None) -> JSONResponse:
    """统一错误响应格式: {code, message, detail}"""
    body = {"code": code, "message": message}
    if detail is not None:
        body["detail"] = detail
    return JSONResponse(status_code=code if 400 <= code < 600 else 500, content=body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Pydantic 校验错误 -> 422"""
    errors = exc.errors()
    return _error_response(422, "Request validation failed", errors)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException -> 统一 JSON 格式"""
    detail = exc.detail
    if isinstance(detail, dict):
        return _error_response(exc.status_code, detail.get("message", str(detail)), detail.get("detail"))
    return _error_response(exc.status_code, str(detail))


@app.exception_handler(Exception)
async def generic_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    """未捕获异常 -> 500"""
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(500, "Internal server error", str(exc))


# CORS：若 CORS_ORIGINS=* 则允许所有源；否则用列表+正则匹配 localhost 任意端口
_cors_origins = settings.cors_origins_list
_allow_all = "*" in _cors_origins or not _cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors_origins,
    allow_origin_regex=None if _allow_all else r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=False if _allow_all else True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 数据路由：/api/data/fetch, /api/data/history, /api/data/funds 等
app.include_router(data.router, prefix="/api/data", tags=["数据"])
# 决策路由：/api/decisions
app.include_router(decisions.router, prefix="/api/decisions", tags=["决策"])
# 资产路由：/api/assets
app.include_router(assets.router, prefix="/api/assets", tags=["资产"])
app.include_router(mongo.router, prefix="/api/mongo", tags=["MongoDB"])
app.include_router(news.router, prefix="/api/news", tags=["新闻"])
app.include_router(grok.router, prefix="/api", tags=["Grok"])
app.include_router(config_router.router, prefix="/api", tags=["配置"])

# 兼容旧版 v1 路径
app.include_router(data.router, prefix="/api/v1/data", tags=["数据-v1"])
app.include_router(decisions.router, prefix="/api/v1/decisions", tags=["决策-v1"])
app.include_router(assets.router, prefix="/api/v1/assets", tags=["资产-v1"])


@app.get("/")
async def root():
    """根路径健康检查"""
    return api_success(data={"message": "Fund Quant Terminal API", "status": "ok"})


@app.get("/health")
async def health():
    """健康检查"""
    return api_success(data={"status": "healthy"})
