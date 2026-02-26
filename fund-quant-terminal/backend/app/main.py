# =====================================================
# FastAPI 主应用入口
# 配置 CORS、路由、生命周期、日志
# =====================================================

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import close_database, get_database
from app.routers import assets, config_router, data, decisions, grok, mongo
from app.schemas.response import api_success
from app.utils.logger import logger


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
        path.write_text(doc["content"], encoding="utf-8")
        logger.info("已从数据库同步 Grok 角色设定至 %s (v%s)", path, doc.get("version", "?"))
    except Exception as e:
        logger.warning("同步 GROK_ROLE_PROMPT.md 失败: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：连接、创建索引"""
    try:
        from app.database import ensure_indexes

        db = await get_database()
        await db.command("ping")
        logger.info("MongoDB 连接成功, 数据库: %s", settings.MONGODB_DB_NAME)
        await ensure_indexes()

        doc = await db["config"].find_one({"_id": "tokens"})
        if doc and doc.get("tokens", {}).get("tushare"):
            from app.routers.data import data_service
            data_service.update_tushare_token(doc["tokens"]["tushare"])
            logger.info("已从配置加载 Tushare Token")

        await _sync_grok_prompt_to_file()
    except Exception as e:
        logger.error("MongoDB 连接失败: %s", e)
        raise
    yield
    await close_database()
    logger.info("应用关闭，已断开数据库")


app = FastAPI(
    title="Fund Quant Terminal API",
    description="基金量化终端 - 数据与决策管理后端",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据路由：/api/data/fetch, /api/data/history, /api/data/funds 等
app.include_router(data.router, prefix="/api/data", tags=["数据"])
# 决策路由：/api/decisions
app.include_router(decisions.router, prefix="/api/decisions", tags=["决策"])
# 资产路由：/api/assets
app.include_router(assets.router, prefix="/api/assets", tags=["资产"])
app.include_router(mongo.router, prefix="/api/mongo", tags=["MongoDB"])
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
