# =====================================================
# 日志配置模块
# =====================================================

import logging
import sys

from app.config import settings


def setup_logging() -> logging.Logger:
    """配置应用日志，返回 root logger"""
    log_level = logging.DEBUG if settings.APP_DEBUG else logging.INFO

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    logger = logging.getLogger("app")
    logger.setLevel(log_level)
    return logger


# 应用级 logger
logger = setup_logging()
