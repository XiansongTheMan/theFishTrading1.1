# =====================================================
# 华尔街见闻 API 客户端
# 支持异步 / 同步调用，10 秒超时，3 次指数退避重试
# =====================================================

from functools import wraps
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.logger import logger

# 快讯 lives 需用 api-one.wallstcn.com；api-prod 返回空 data
BASE_URL = "https://api-one.wallstcn.com"
DEFAULT_TIMEOUT = 10.0
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://wallstreetcn.com",
}

def _retry_decorator(fn):
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)), reraise=True)
    @wraps(fn)
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)
    return wrapper

def _retry_async_decorator(fn):
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)), reraise=True)
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        return await fn(*args, **kwargs)
    return wrapper

class WallStreetCNClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = DEFAULT_TIMEOUT, headers: dict | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._headers = {**DEFAULT_HEADERS, **(headers or {})}
        self._async_client = None
        self._sync_client = None

    def _get_async_client(self):
        if self._async_client is None or (hasattr(self._async_client, 'is_closed') and self._async_client.is_closed):
            self._async_client = httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=self._timeout)
        return self._async_client

    def _get_sync_client(self):
        if self._sync_client is None or (hasattr(self._sync_client, 'is_closed') and self._sync_client.is_closed):
            self._sync_client = httpx.Client(base_url=self._base_url, headers=self._headers, timeout=self._timeout)
        return self._sync_client

    async def _get_json_async(self, path: str, params: dict | None = None):
        client = self._get_async_client()
        try:
            resp = await client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("wallstreetcn request failed %s: %s", path, e.response.status_code)
            raise
        except Exception as e:
            logger.exception("wallstreetcn async request error %s: %s", path, e)
            raise

    def _get_json_sync(self, path: str, params: dict | None = None):
        client = self._get_sync_client()
        try:
            resp = client.get(path, params=params or {})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("wallstreetcn request failed %s: %s", path, e.response.status_code)
            raise
        except Exception as e:
            logger.exception("wallstreetcn sync request error %s: %s", path, e)
            raise

    @_retry_async_decorator
    async def get_live_news(self, limit: int = 20, cursor: int = 0, channel: str = "global-channel") -> Any:
        """获取快讯 / 实时新闻，channel 如 global-channel/a-stock-channel"""
        return await self._get_json_async(
            "/apiv1/content/lives",
            params={"limit": limit, "cursor": cursor, "channel": channel},
        )

    @_retry_async_decorator
    async def get_articles(self, channel: str = "news", limit: int = 10) -> Any:
        """获取文章列表，返回原始 JSON"""
        return await self._get_json_async("/apiv1/content/articles", params={"category": channel, "limit": limit})

    @_retry_async_decorator
    async def search_stock(self, query: str, limit: int = 10) -> Any:
        """搜索股票，返回原始 JSON"""
        return await self._get_json_async("/apiv1/search/stock", params={"query": query, "limit": limit})

    @_retry_async_decorator
    async def get_quote(self, code: str) -> Any:
        """获取行情，返回原始 JSON"""
        return await self._get_json_async("/apiv1/market/quote", params={"code": code})

    @_retry_async_decorator
    async def search_by_keyword(self, keyword: str, limit: int = 10) -> Any:
        """关键词搜索，返回原始 JSON"""
        return await self._get_json_async("/apiv1/search", params={"keyword": keyword, "limit": limit})

    @_retry_decorator
    def get_live_news_sync(self, limit: int = 20, cursor: int = 0, channel: str = "global-channel"):
        return self._get_json_sync("/apiv1/content/lives", params={"limit": limit, "cursor": cursor, "channel": channel})

    @_retry_decorator
    def get_articles_sync(self, channel: str = "news", limit: int = 10):
        return self._get_json_sync("/apiv1/content/articles", params={"category": channel, "limit": limit})

    @_retry_decorator
    def search_stock_sync(self, query: str, limit: int = 10):
        return self._get_json_sync("/apiv1/search/stock", params={"query": query, "limit": limit})

    @_retry_decorator
    def get_quote_sync(self, code: str):
        return self._get_json_sync("/apiv1/market/quote", params={"code": code})

    @_retry_decorator
    def search_by_keyword_sync(self, keyword: str, limit: int = 10):
        return self._get_json_sync("/apiv1/search", params={"keyword": keyword, "limit": limit})

    def close(self):
        if self._async_client and hasattr(self._async_client, 'is_closed') and not self._async_client.is_closed:
            self._async_client.close()
        if self._sync_client and hasattr(self._sync_client, 'is_closed') and not self._sync_client.is_closed:
            self._sync_client.close()

    async def aclose(self):
        if self._async_client and hasattr(self._async_client, 'is_closed') and not self._async_client.is_closed:
            await self._async_client.aclose()
