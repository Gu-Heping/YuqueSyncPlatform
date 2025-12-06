import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import List, Dict, Any, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class YuqueClient:
    """
    语雀 API 客户端
    """
    def __init__(self):
        self.base_url = settings.YUQUE_BASE_URL
        self.headers = {
            "X-Auth-Token": settings.YUQUE_TOKEN,
            "User-Agent": "YuqueSyncPlatform/1.0",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)

    async def close(self):
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.ConnectTimeout, httpx.ReadTimeout))
    )
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        url = f"{self.base_url}{endpoint}"
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def get_user_info(self) -> Dict:
        """获取当前认证用户信息"""
        data = await self._get("/user")
        return data.get("data", {})

    async def get_user_repos(self, user_id: int) -> List[Dict]:
        """获取用户的知识库列表"""
        data = await self._get(f"/users/{user_id}/repos")
        return data.get("data", [])
    
    async def get_group_repos(self, group_id: int) -> List[Dict]:
        """获取团队的知识库列表"""
        data = await self._get(f"/groups/{group_id}/repos")
        return data.get("data", [])

    async def get_repo_toc(self, repo_id: int) -> List[Dict]:
        """获取知识库目录结构 (TOC)"""
        # API: GET /repos/:id/toc
        data = await self._get(f"/repos/{repo_id}/toc")
        return data.get("data", [])

    async def get_doc_detail(self, repo_id: int, slug: str) -> Dict:
        """获取文档详情 (含正文)"""
        # API: GET /repos/:id/docs/:slug
        # 增加 raw=1 参数可能获取源码，视需求而定，这里使用默认
        data = await self._get(f"/repos/{repo_id}/docs/{slug}")
        return data.get("data", {})
