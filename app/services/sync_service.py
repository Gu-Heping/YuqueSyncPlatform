import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from app.services.yuque_client import YuqueClient
import math
from app.models.schemas import User, Repo, Doc, Member
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class SyncService:
    """
    数据同步服务：负责协调 YuqueClient 和 MongoDB
    实现 Discovery -> Merge -> Upsert 逻辑
    """
    def __init__(self):
        self.client = YuqueClient()
        # 限制并发请求数，防止触发语雀流控 (429 Too Many Requests)
        self.semaphore = asyncio.Semaphore(5) 
        self.rag_service = RAGService() 

    async def sync_all(self):
        """
        执行全量同步任务
        """
        try:
            logger.info("=== 开始全量同步 ===")
            
            # 1. Discovery: 获取当前用户信息
            user_data = await self.client.get_user_info()
            if not user_data:
                logger.error("无法获取用户信息，同步终止")
                return
            
            current_user = await self._upsert_user(user_data)
            logger.info(f"当前用户: {current_user.name} ({current_user.login})")

            # 2. 同步团队成员
            await self.sync_team_members(current_user.yuque_id)

            # 3. Discovery: 获取知识库列表 (这里简化为获取当前用户可见的知识库)
            # 如果是团队 Token，通常 /users/{id}/repos 也能获取到团队库，或者需要遍历 groups
            # 这里先实现获取用户个人及参与的 Repos
            repos_data = await self.client.get_user_repos(current_user.yuque_id)
            logger.info(f"发现 {len(repos_data)} 个知识库")

            for repo_data in repos_data:
                await self.sync_repo(repo_data)

            logger.info("=== 全量同步完成 ===")

        except Exception as e:
            logger.error(f"同步过程中发生未捕获异常: {str(e)}", exc_info=True)
        finally:
            await self.client.close()

    async def sync_team_members(self, group_id: int):
        """
        同步团队成员列表 (自动分页，死循环 + 终止条件)
        API: /groups/{id}/statistics/members
        """
        logger.info(f"--- 开始同步团队成员 (Group ID: {group_id}) ---")
        page = 1
        
        while True:
            # 1. 获取单页数据
            try:
                async with self.semaphore:
                    # 注意：API 返回的列表可能包含已退出的成员
                    resp = await self.client._get(f"/groups/{group_id}/statistics/members", params={"page": page})
                    members_list = resp.get('data', {}).get('members', [])
            except Exception as e:
                logger.error(f"获取第 {page} 页成员失败: {e}")
                break

            # 2. 终止条件：列表为空
            if not members_list:
                logger.info("分页数据为空，同步结束")
                break

            logger.info(f"正在处理第 {page} 页，共 {len(members_list)} 名成员")

            # 3. 处理数据
            for item in members_list:
                try:
                    # 提取嵌套的 user 对象
                    # 结构示例: { "role": 0, "status": 1, "user": { "id": 123, "name": "..." } }
                    user_info = item.get('user') or {}
                    
                    # 关键字段校验
                    yuque_id = user_info.get('id')
                    if not yuque_id:
                        # 尝试从外层获取 (兼容性处理)
                        yuque_id = item.get('user_id')
                    
                    if not yuque_id:
                        logger.warning(f"跳过无效成员数据: {item}")
                        continue

                    # 状态判断 (根据语雀 API，status=1 通常为正常)
                    raw_status = item.get('status')
                    is_active = (raw_status == 1)

                    member = Member(
                        yuque_id=yuque_id,
                        login=user_info.get('login') or f"u_{yuque_id}", # Fallback
                        name=user_info.get('name') or "Unknown",
                        avatar_url=user_info.get('avatar_url'),
                        description=user_info.get('description'),
                        email=user_info.get('email') or item.get('email'), # 尝试多处获取
                        role=item.get('role'),
                        status=raw_status,
                        is_active=is_active,
                        updated_at=datetime.utcnow()
                    )

                    await Member.find_one(Member.yuque_id == member.yuque_id).upsert(
                        {"$set": member.model_dump(exclude={"id"})},
                        on_insert=member
                    )
                except Exception as e:
                    logger.error(f"处理成员数据出错: {e}, 数据: {item}")

            # 4. 下一页
            page += 1
            await asyncio.sleep(0.2)

        logger.info("--- 团队成员同步完成 ---")

    async def sync_repo(self, repo_data: Dict):
        """
        同步单个知识库：Upsert Repo -> Fetch TOC -> Merge Details -> Upsert Docs
        """
        try:
            # 1. Upsert Repo
            repo = await self._upsert_repo(repo_data)
            logger.info(f"正在同步知识库: {repo.name} (ID: {repo.yuque_id})")

            # 2. Fetch TOC (Structure)
            toc_list = await self.client.get_repo_toc(repo.yuque_id)
            logger.info(f"  - 获取到 {len(toc_list)} 个目录节点")

            # 3. Process Docs (Concurrency controlled)
            tasks = []
            for item in toc_list:
                tasks.append(self._process_toc_item(repo.yuque_id, item))
            
            # 并发执行所有文档同步任务
            await asyncio.gather(*tasks)
            logger.info(f"  - 知识库 {repo.name} 同步完毕")

        except Exception as e:
            logger.error(f"同步知识库 {repo_data.get('name')} 失败: {e}")

    async def sync_repo_structure(self, repo_id: int):
        """
        仅同步知识库目录结构 (TOC)，不拉取文档详情。
        用于 Webhook 新增/删除文档后快速修复树状结构。
        包含 Pruning 机制：删除本地存在但远程 TOC 中不存在的文档。
        """
        try:
            logger.info(f"正在同步知识库结构 (Repo ID: {repo_id})")
            toc_list = await self.client.get_repo_toc(repo_id)
            
            # 1. 收集活跃 UUID
            active_uuids = [item['uuid'] for item in toc_list]
            
            # 2. 并行更新结构
            tasks = []
            for item in toc_list:
                tasks.append(self._update_toc_structure(repo_id, item))
            
            await asyncio.gather(*tasks)
            
            # 3. Pruning: 删除过期文档
            # 删除条件: repo_id 匹配 且 uuid 不在 active_uuids 中
            if active_uuids:
                # 使用原生 MongoDB 查询语法 $nin
                delete_result = await Doc.find(
                    Doc.repo_id == repo_id,
                    {"uuid": {"$nin": active_uuids}}
                ).delete()
                
                if delete_result and delete_result.deleted_count > 0:
                    logger.info(f"清理过期文档: {delete_result.deleted_count} 个 (Repo ID: {repo_id})")
            else:
                # 如果 TOC 为空，说明知识库被清空了，删除该库下所有文档
                delete_result = await Doc.find(Doc.repo_id == repo_id).delete()
                if delete_result and delete_result.deleted_count > 0:
                    logger.info(f"知识库为空，清理所有文档: {delete_result.deleted_count} 个 (Repo ID: {repo_id})")

            logger.info(f"知识库结构同步完成 (Repo ID: {repo_id})")
        except Exception as e:
            logger.error(f"同步知识库结构失败: {e}")

    async def _update_toc_structure(self, repo_id: int, toc_item: Dict):
        """
        更新单个 TOC 节点的结构信息 (不拉取详情)
        """
        async with self.semaphore:
            try:
                # 构造更新数据 (仅结构相关)
                update_data = {
                    "uuid": toc_item['uuid'],
                    "repo_id": repo_id,
                    "title": toc_item['title'],
                    "type": toc_item['type'],
                    "slug": toc_item.get('url') or toc_item['uuid'],
                    "parent_uuid": toc_item.get('parent_uuid'),
                    "prev_uuid": toc_item.get('prev_uuid'),
                    "sibling_uuid": toc_item.get('sibling_uuid'),
                    "child_uuid": toc_item.get('child_uuid'),
                    "depth": toc_item.get('depth', 0),
                    "updated_at": self._parse_time(toc_item.get('updated_at')), # 优先使用 API 返回的时间
                    "last_synced_at": datetime.utcnow() # 记录本次同步时间
                }
                
                # 处理 yuque_id
                raw_id = toc_item.get('id')
                if isinstance(raw_id, int):
                    update_data["yuque_id"] = raw_id
                elif isinstance(raw_id, str) and raw_id.isdigit():
                    update_data["yuque_id"] = int(raw_id)

                # Upsert: 如果存在则更新结构，不存在则插入 (此时 body 为空)
                doc_obj = Doc(**update_data)
                
                await Doc.find_one(Doc.uuid == update_data['uuid']).upsert(
                    {"$set": update_data},
                    on_insert=doc_obj
                )
            except Exception as e:
                logger.error(f"更新 TOC 结构失败 (uuid: {toc_item.get('uuid')}): {e}")

    async def _process_toc_item(self, repo_id: int, toc_item: Dict):
        """
        处理单个 TOC 节点：
        - 如果是 DOC 类型，拉取详情并合并
        - 如果是 TITLE 类型，仅保存结构
        - Upsert 到数据库
        """
        async with self.semaphore: # 限制并发
            try:
                doc_type = toc_item.get('type')
                slug = toc_item.get('url') # TOC 中的 url 字段通常存储 slug
                
                # 清洗 ID 字段 (防止空字符串报错)
                raw_id = toc_item.get('id')
                yuque_id = None
                if isinstance(raw_id, int):
                    yuque_id = raw_id
                elif isinstance(raw_id, str) and raw_id.isdigit():
                    yuque_id = int(raw_id)

                # 基础结构信息
                doc_data = {
                    "uuid": toc_item['uuid'],
                    "yuque_id": yuque_id,
                    "repo_id": repo_id,
                    "slug": slug if slug else toc_item['uuid'], # Fallback
                    "title": toc_item['title'],
                    "type": doc_type,
                    "parent_uuid": toc_item.get('parent_uuid') or None,
                    "prev_uuid": toc_item.get('prev_uuid') or None,
                    "sibling_uuid": toc_item.get('sibling_uuid') or None,
                    "child_uuid": toc_item.get('child_uuid') or None,
                    "depth": toc_item.get('depth', 0),
                    "updated_at": self._parse_time(toc_item.get('updated_at')), # 优先使用 API 返回的时间
                    "last_synced_at": datetime.utcnow() # 记录本次同步时间
                }

                # 如果是文档且有 slug，拉取详情 (Data Merging)
                if doc_type == 'DOC' and slug:
                    try:
                        detail = await self.client.get_doc_detail(repo_id, slug)
                        # 合并详情数据
                        doc_data.update({
                            "yuque_id": detail.get('id', doc_data['yuque_id']), # 以详情中的 ID 为准
                            "title": detail.get('title', doc_data['title']),    # 以详情中的标题为准
                            "description": detail.get('description'),
                            "cover": detail.get('cover'),
                            "body": detail.get('body'),
                            "body_html": detail.get('body_html'),
                            "format": detail.get('format'),
                            "word_count": detail.get('word_count', 0),
                            "likes_count": detail.get('likes_count', 0),
                            "read_count": detail.get('read_count', 0),
                            "comments_count": detail.get('comments_count', 0),
                            "created_at": self._parse_time(detail.get('created_at')),
                            "content_updated_at": self._parse_time(detail.get('content_updated_at')),
                            "published_at": self._parse_time(detail.get('published_at')),
                            "first_published_at": self._parse_time(detail.get('first_published_at')),
                            "user_id": detail.get('user_id'),
                            "last_editor_id": detail.get('last_editor_id'),
                        })
                        # 更新时间以 API 为准，优先使用 content_updated_at (内容更新时间)，其次是 updated_at
                        api_content_updated_at = self._parse_time(detail.get('content_updated_at'))
                        api_updated_at = self._parse_time(detail.get('updated_at'))
                        
                        if api_content_updated_at:
                            doc_data['updated_at'] = api_content_updated_at
                        elif api_updated_at:
                            doc_data['updated_at'] = api_updated_at

                    except Exception as e:
                        logger.warning(f"    - 拉取文档详情失败 (slug: {slug}): {e}，将仅保存目录结构")

                # Upsert 到 MongoDB
                doc_obj = await self._upsert_doc(doc_data)
                
                # 触发向量化 (仅当有正文内容时)
                if doc_obj and doc_obj.body:
                    try:
                        # 异步触发，不阻塞主流程 (或者使用 BackgroundTasks，但这里在 Service 层直接调用)
                        # 为了保证实时性，这里 await，但加上 try-except
                        await self.rag_service.upsert_doc_to_vector_db(doc_obj)
                    except Exception as e:
                        logger.error(f"    - 向量化失败 (slug: {slug}): {e}")

                # logger.debug(f"    - 已保存: {doc_data['title']} ({doc_type})")

            except Exception as e:
                logger.error(f"处理 TOC 节点失败 (uuid: {toc_item.get('uuid')}): {e}")

    async def _upsert_user(self, data: Dict) -> User:
        user = User(
            yuque_id=data['id'],
            login=data['login'],
            name=data['name'],
            avatar_url=data.get('avatar_url'),
            description=data.get('description'),
            books_count=data.get('books_count', 0),
            public=data.get('public', 0),
            created_at=self._parse_time(data.get('created_at')),
            updated_at=datetime.utcnow()
        )
        await User.find_one(User.yuque_id == user.yuque_id).upsert(
            {"$set": user.model_dump(exclude={"id"})},
            on_insert=user
        )
        return user

    async def _upsert_repo(self, data: Dict) -> Repo:
        repo = Repo(
            yuque_id=data['id'],
            name=data['name'],
            slug=data['slug'],
            description=data.get('description'),
            public=data.get('public', 0),
            user_id=data['user_id'],
            items_count=data.get('items_count', 0),
            watches_count=data.get('watches_count', 0),
            likes_count=data.get('likes_count', 0),
            namespace=data.get('namespace'),
            content_updated_at=self._parse_time(data.get('content_updated_at')),
            created_at=self._parse_time(data.get('created_at')),
            updated_at=datetime.utcnow()
        )
        await Repo.find_one(Repo.yuque_id == repo.yuque_id).upsert(
            {"$set": repo.model_dump(exclude={"id"})},
            on_insert=repo
        )
        return repo

    async def _upsert_doc(self, data: Dict) -> Optional[Doc]:
        # 使用 uuid 作为唯一键进行 upsert
        doc = Doc(**data)
        await Doc.find_one(Doc.uuid == doc.uuid).upsert(
            {"$set": doc.model_dump(exclude={"id"})},
            on_insert=doc
        )
        return await Doc.find_one(Doc.uuid == doc.uuid)

    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        if not time_str:
            return None
        try:
            # 处理 ISO 8601 格式: 2023-01-01T12:00:00.000Z
            return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        except ValueError:
            return None
