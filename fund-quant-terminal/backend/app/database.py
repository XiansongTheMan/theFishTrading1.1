# =====================================================
# 数据库连接与索引初始化
# 完全异步 MongoDB - 仅使用 motor.motor_asyncio.AsyncIOMotorClient
# 无 pymongo.MongoClient 同步调用
# =====================================================

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings
from app.utils.logger import logger


_client: AsyncIOMotorClient | None = None


async def get_database() -> AsyncIOMotorDatabase:
    """获取 MongoDB 数据库实例（异步，用于 FastAPI Depends）"""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.MONGODB_URL)
    return _client[settings.MONGODB_DB_NAME]


async def close_database() -> None:
    """关闭数据库连接（Motor Client.close 为同步，在事件循环中快速完成）"""
    global _client
    if _client is not None:
        _client.close()
        _client = None


async def ensure_indexes():
    """启动时自动创建索引"""
    db = await get_database()
    try:
        # 决策日志：按时间、基金、动作查询
        await db.decision_logs.create_index("timestamp", name="ix_timestamp")
        await db.decision_logs.create_index("fund_code", name="ix_fund_code")
        await db.decision_logs.create_index("user_action", name="ix_user_action")
        await db.decision_logs.create_index([("timestamp", -1)], name="ix_timestamp_desc")
        logger.info("decision_logs 索引创建完成")
    except Exception as e:
        logger.warning("decision_logs 索引创建: %s", e)

    try:
        await db.grok_prompts.create_index("version", name="ix_version")
        await db.grok_prompts.create_index([("version", -1)], name="ix_version_desc")
        logger.info("grok_prompts 索引创建完成")
    except Exception as e:
        logger.warning("grok_prompts 索引创建: %s", e)

    try:
        # 资产：按 symbol、asset_type 查询
        await db.assets.create_index("symbol", name="ix_symbol")
        await db.assets.create_index("asset_type", name="ix_asset_type")
        await db.assets.create_index([("created_at", -1)], name="ix_created_at_desc")
        logger.info("assets 索引创建完成")
    except Exception as e:
        logger.warning("assets 索引创建: %s", e)

    try:
        await db.holding_histories.create_index([("symbol", 1), ("asset_type", 1)], unique=True, name="ix_symbol_type")
        logger.info("holding_histories 索引创建完成")
    except Exception as e:
        logger.warning("holding_histories 索引: %s", e)

    try:
        await db.holding_transactions.create_index([("symbol", 1), ("asset_type", 1)], name="ix_symbol_type")
        await db.holding_transactions.create_index("date", name="ix_date")
        logger.info("holding_transactions 索引创建完成")
    except Exception as e:
        logger.warning("holding_transactions 索引: %s", e)
