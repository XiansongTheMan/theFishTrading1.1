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

    # CORS 允许的源（逗号分隔）。设为 * 表示允许所有源（开发方便，生产慎用）
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176,http://127.0.0.1:5174,http://127.0.0.1:5175,http://127.0.0.1:5176"

    # 新闻 RSS 源（逗号分隔，URL 中 {fund_code} 会替换为基金代码）
    NEWS_FEED_URLS: str = "https://rsshub.app/finance/eastmoney/roll,https://rsshub.app/finance/eastmoney/fund/{fund_code},https://rsshub.app/finance/sina/roll"

    # 华尔街见闻 API 基地址。快讯 lives 需用 api-one.wallstcn.com（api-prod 返回空）
    WALLSTREETCN_BASE_URL: str = "https://api-one.wallstcn.com"

    # 东方财富 7*24 数据源：guigui（鬼鬼API，国内可用）或 rsshub（RSSHub，需代理）
    EASTMONEY_SOURCE: str = "guigui"
    EASTMONEY_GUIGUI_URL: str = "https://api.guiguiya.com/api/hotlist/eastmoney"
    EASTMONEY_RSS_URL: str = "https://rsshub.app/finance/eastmoney/roll"

    # 财联社数据源：cls（财联社原生 API，国内可用）或 rsshub（RSSHub，可能需代理）
    CAILIANSHERSS_SOURCE: str = "cls"
    # 财联社 RSS 基地址（RSSHub），当 CAILIANSHERSS_SOURCE=rsshub 时使用
    CAILIANSHERSS_RSS_BASE_URL: str = "https://rsshub.app"

    @property
    def cors_origins_list(self) -> List[str]:
        """解析 CORS 源列表"""
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]


class LLMSettings(BaseSettings):
    """
    LLM 多模型配置类（Grok、Qwen 等）
    从环境变量和 .env 加载，用于 MultiLLMClient 统一调用
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Grok (x.ai) API
    GROK_API_KEY: str = ""
    GROK_BASE_URL: str = "https://api.x.ai/v1"

    # Qwen / 通义千问 (DashScope OpenAI 兼容接口)
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # Qwen 最强推理模型（2026 旗舰版），支持复杂基金分析与 grounding
    DEFAULT_MODEL: str = "qwen3-max"
    DEFAULT_TEMPERATURE: float = 0.2
    MAX_TOKENS: int = 2000

    # 默认 LLM 提供商：grok 或 qwen
    LLM_PROVIDER: str = "qwen"

    # 代理支持，留空则使用系统/环境变量
    HTTP_PROXY: str = ""
    HTTPS_PROXY: str = ""


# 全局配置实例
settings = Settings()
llm_settings = LLMSettings()
