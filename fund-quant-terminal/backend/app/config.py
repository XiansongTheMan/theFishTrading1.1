# =====================================================
# 应用配置模块
# 从环境变量加载配置，支持 .env 文件
# =====================================================

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类
    使用 pydantic-settings 从环境变量和 .env 加载
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # MongoDB 配置
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "fund_quant"

    # Tushare Token（可选，用于获取行情数据）
    TUSHARE_TOKEN: str = ""

    # 应用配置
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # CORS 允许的源（逗号分隔）
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """解析 CORS 源列表"""
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]


# 全局配置实例
settings = Settings()
