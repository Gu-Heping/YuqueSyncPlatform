import logging
from datetime import datetime
from app.models.schemas import WebhookPayload, Doc, Comment, Member, Repo
from app.services.sync_service import SyncService
from app.services.email_service import EmailService
from app.services.feed_service import FeedService
from app.core.config import settings
from typing import Optional
from fastapi import BackgroundTasks

from app.services.comment_service import CommentService

logger = logging.getLogger(__name__)

class WebhookService:
    """
    处理语雀 Webhook 事件的服务
    """
    def __init__(self):
        self.email_service = EmailService()
        self.feed_service = FeedService()
        self.comment_service = CommentService()

    async def handle_event(self, payload: WebhookPayload, background_tasks: Optional[BackgroundTasks] = None):
        data = payload.data
        action_type = data.action_type
        
        logger.info(f"Received Webhook Event: {action_type} (ID: {data.id})")
        
        if action_type in ["publish", "update"]:
            await self._handle_doc_upsert(data, background_tasks)
            # 记录动态 (仅当操作者是文档作者本人时，避免协同编辑导致的刷屏或误报)
            if data.user_id == data.actor_id:
                await self.feed_service.create_activity(data)
            else:
                logger.info(f"Skipped activity creation: actor_id ({data.actor_id}) != user_id ({data.user_id})")
        elif action_type == "delete":
            await self._handle_doc_delete(data)
            # 删除动态
            await self.feed_service.delete_activity(data.id)
        elif action_type in ["comment_create", "comment_update", "comment_reply_create"]:
            await self.comment_service.handle_comment_webhook(data, background_tasks)
        else:
            logger.warning(f"Ignored unknown action_type: {action_type}")

    async def _handle_doc_upsert(self, data, background_tasks: Optional[BackgroundTasks] = None):
        """处理文档发布/更新事件"""
        if not data.book:
            logger.error("Doc event missing 'book' info")
            return

        # 0. 检查并自动创建知识库 (Repo)
        sync_service = SyncService()
        try:
            repo_id = data.book.id
            repo = await Repo.find_one(Repo.yuque_id == repo_id)
            if not repo:
                # 获取完整 Repo 详情，确保 Namespace 等关键字段存在
                repo_detail = await sync_service.client.get_repo_detail(repo_id)
                if repo_detail:
                    await sync_service._upsert_repo(repo_detail)
                    logger.info(f"Auto-synced new repo from webhook: {repo_detail.get('name')} ({repo_id})")
                else:
                    logger.error(f"Failed to fetch repo detail for {repo_id}, skipping auto-create")
        except Exception as e:
            logger.error(f"Failed to auto-create repo {data.book.id}: {e}")

        # 1. 同步作者信息 (Actor)
        # ... (keep existing actor sync logic) ...
        user_id = data.user_id 
        
        author_member = None
        if data.actor and data.actor.id == user_id:
            try:
                author_member = await Member.find_one(Member.yuque_id == user_id)
                if not author_member:
                    new_member = Member(
                        yuque_id=data.actor.id,
                        login=data.actor.login,
                        name=data.actor.name,
                        avatar_url=data.actor.avatar_url,
                        role=0, # 默认
                        status=1, # 默认
                        updated_at=datetime.utcnow()
                    )
                    author_member = await new_member.insert()
                    logger.info(f"Auto-synced new member from webhook actor: {data.actor.name} ({user_id})")
            except Exception as e:
                logger.error(f"Failed to sync actor {user_id}: {e}")
        
        if not author_member:
             author_member = await Member.find_one(Member.yuque_id == user_id)

        # 2. 强一致性同步：拉取文档详情
        # 不再依赖 Webhook Payload 中的部分数据，而是直接从 API 获取最新最全的数据
        try:
            detail = await sync_service.client.get_doc_detail(data.book.id, data.slug)
            if detail:
                # 构造符合 Doc 模型的数据字典
                # 注意：Webhook 通常只触发单个文档更新，所以 struct 信息 (prev_uuid, parent_uuid 等) 
                # 可能需要通过 sync_repo_structure 来修复，这里主要关注内容和元数据
                
                # 尝试获取现有的 doc 以保留 uuid (如果存在)
                existing_doc = await Doc.find_one(Doc.yuque_id == data.id)
                uuid = existing_doc.uuid if existing_doc else f"webhook-{data.id}"

                doc_data = {
                    "uuid": uuid,
                    "yuque_id": detail.get('id'),
                    "repo_id": detail.get('book_id', data.book.id),
                    "slug": detail.get('slug'),
                    "title": detail.get('title'),
                    "description": detail.get('description'),
                    "cover": detail.get('cover'),
                    "body": detail.get('body'),
                    "body_html": detail.get('body_html'),
                    "format": detail.get('format'),
                    "word_count": detail.get('word_count', 0),
                    "likes_count": detail.get('likes_count', 0),
                    "read_count": detail.get('read_count', 0),
                    "comments_count": detail.get('comments_count', 0),
                    "created_at": sync_service._parse_time(detail.get('created_at')),
                    "updated_at": sync_service._parse_time(detail.get('updated_at')),
                    "content_updated_at": sync_service._parse_time(detail.get('content_updated_at')),
                    "published_at": sync_service._parse_time(detail.get('published_at')),
                    "first_published_at": sync_service._parse_time(detail.get('first_published_at')),
                    "user_id": detail.get('user_id'),
                    "last_editor_id": detail.get('last_editor_id'),
                    "type": "DOC", # Webhook 推送的通常是文档
                    "last_synced_at": datetime.utcnow()
                }

                # 使用 SyncService 的 _upsert_doc (它会自动处理 created_at 保护)
                # 但 _upsert_doc 期望的是 struct 字段齐全的，这里可能缺 parent_uuid 等
                # 我们复用 _upsert_doc 的逻辑，或者直接在这里 upsert
                # 为了简单直接，我们在这里从 detail 构造并 upsert，
                # 结构修正交给最后的 sync_repo_structure

                doc_obj = Doc(**doc_data)
                update_data = doc_obj.model_dump(exclude={"id"})
                if update_data.get("created_at") is None:
                    update_data.pop("created_at", None)

                await Doc.find_one(Doc.yuque_id == doc_obj.yuque_id).upsert(
                    {"$set": update_data},
                    on_insert=doc_obj
                )
                logger.info(f"Doc full-synced from API: {doc_data['title']} ({doc_data['yuque_id']})")
                
                # 触发向量化
                if doc_obj.body:
                     await sync_service.rag_service.upsert_doc_to_vector_db(doc_obj)

            else:
                 logger.warning(f"Failed to fetch doc detail for {data.slug}, falling back to webhook payload")
                 # Fallback logic if API fails? Or just skip? 
                 # Given user request for "strong consistency", maybe we should skip if verify fails, 
                 # but to be safe let's keep the fallback or just return error.
                 # Let's return here to avoid partial data if user insists on full sync.
                 return 
                 
        except Exception as e:
            logger.error(f"Failed to fetch/sync doc detail: {e}")
        finally:
            await sync_service.client.close()

        # 3. 触发邮件通知 (仅当有后台任务且作者存在且有粉丝时)
        # 仅当操作者是文档作者本人时才发送通知 (防止误报)
        should_notify = (
            background_tasks 
            and author_member 
            and author_member.followers 
            and data.user_id == data.actor_id
        )

        if should_notify:
            try:
                # 查找所有粉丝的邮箱
                followers = await Member.find(
                    {"yuque_id": {"$in": author_member.followers}, "email": {"$ne": None}}
                ).to_list()
                
                if followers:
                    to_emails = [f.email for f in followers if f.email]
                    if to_emails:
                        # 构造 YuqueSync 平台内部链接
                        # 格式: {FRONTEND_URL}/repos/{repo_id}/docs/{slug}
                        base_url = settings.FRONTEND_URL.rstrip('/')
                        doc_url = f"{base_url}/repos/{data.book.id}/docs/{data.slug}"
                        
                        background_tasks.add_task(
                            self.email_service.send_doc_update_email,
                            to_emails=to_emails,
                            doc_title=data.title,
                            author_name=author_member.name,
                            doc_url=doc_url
                        )
                        logger.info(f"Queued email notification for {len(to_emails)} followers")
            except Exception as e:
                logger.error(f"Failed to queue email notification: {e}")
        elif background_tasks and author_member and author_member.followers:
             logger.info(f"Skipped email notification: actor_id ({data.actor_id}) != user_id ({data.user_id})")

        # 如果是新增文档 (publish)，触发目录结构同步
        if data.action_type == "publish":
            sync_service = SyncService()
            try:
                await sync_service.sync_repo_structure(data.book.id)
            finally:
                await sync_service.client.close()

    async def _handle_doc_delete(self, data):
        """处理文档删除事件"""
        result = await Doc.find_one(Doc.yuque_id == data.id).delete()
        if result and result.deleted_count > 0:
            logger.info(f"Doc deleted: {data.id}")
        else:
            logger.info(f"Doc not found for deletion: {data.id}")
        
        # 删除文档后，触发目录结构同步 (修复兄弟节点的 prev_uuid 等)
        sync_service = SyncService()
        try:
            await sync_service.sync_repo_structure(data.book.id)
        finally:
            await sync_service.client.close()

    async def _handle_comment_upsert(self, data):
        """处理评论创建/更新事件"""
        if not data.commentable:
            logger.warning("Comment event missing 'commentable' info")
            return

        comment = Comment(
            yuque_id=data.id,
            body_html=data.body_html,
            user_id=data.user.id if data.user else 0,
            doc_id=data.commentable.id,
            created_at=data.created_at,
            updated_at=data.updated_at or datetime.utcnow()
        )
        
        await Comment.find_one(Comment.yuque_id == comment.yuque_id).upsert(
            {"$set": comment.model_dump(exclude={"id"})},
            on_insert=comment
        )
        logger.info(f"Comment upserted: {data.id} on Doc {data.commentable.id}")
