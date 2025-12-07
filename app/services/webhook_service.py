import logging
from datetime import datetime
from app.models.schemas import WebhookPayload, Doc, Comment
from app.services.sync_service import SyncService
from typing import Optional

logger = logging.getLogger(__name__)

class WebhookService:
    """
    处理语雀 Webhook 事件的服务
    """
    async def handle_event(self, payload: WebhookPayload):
        data = payload.data
        action_type = data.action_type
        
        logger.info(f"Received Webhook Event: {action_type} (ID: {data.id})")
        
        if action_type in ["publish", "update"]:
            await self._handle_doc_upsert(data)
        elif action_type == "delete":
            await self._handle_doc_delete(data)
        elif action_type in ["comment_create", "comment_update", "comment_reply_create"]:
            await self._handle_comment_upsert(data)
        else:
            logger.warning(f"Ignored unknown action_type: {action_type}")

    async def _handle_doc_upsert(self, data):
        """处理文档发布/更新事件"""
        if not data.book:
            logger.error("Doc event missing 'book' info")
            return

        # 1. 同步作者信息 (Actor)
        # Webhook 中的 actor 通常是文档的作者/最后修改者
        user_id = data.user_id # 直接使用 payload 中的 user_id (对应作者)
        
        if data.actor and data.actor.id == user_id:
            try:
                from app.models.schemas import Member
                member = await Member.find_one(Member.yuque_id == user_id)
                if not member:
                    new_member = Member(
                        yuque_id=data.actor.id,
                        login=data.actor.login,
                        name=data.actor.name,
                        avatar_url=data.actor.avatar_url,
                        role=0, # 默认
                        status=1, # 默认
                        updated_at=datetime.utcnow()
                    )
                    await new_member.insert()
                    logger.info(f"Auto-synced new member from webhook actor: {data.actor.name} ({user_id})")
            except Exception as e:
                logger.error(f"Failed to sync actor {user_id}: {e}")

        # 尝试查找现有文档
        doc = await Doc.find_one(Doc.yuque_id == data.id)
        
        # 2. 准备更新的数据
        # 直接使用 Webhook Payload 中的数据，不再额外调用 API
        update_dict = {
            "title": data.title,
            "slug": data.slug,
            "repo_id": data.book.id,
            "user_id": user_id,
            "body": data.body,
            "body_html": data.body_html,
            "updated_at": data.updated_at or datetime.utcnow(),
            "content_updated_at": data.content_updated_at,
            "published_at": data.published_at,
            "first_published_at": data.first_published_at,
            
            # 统计信息
            "word_count": data.word_count,
            "likes_count": data.likes_count,
            "read_count": data.read_count,
            "comments_count": data.comments_count,
        }
        
        if doc:
            await doc.update({"$set": update_dict})
            logger.info(f"Doc updated: {data.title} ({data.id})")
        else:
            # 如果是新文档，由于缺少 TOC 中的 UUID，我们生成一个临时的
            # 在下次全量同步时，这个文档可能会被更新或合并
            update_dict["uuid"] = f"webhook-{data.id}"
            update_dict["yuque_id"] = data.id
            update_dict["type"] = "DOC" # 默认为文档
            
            new_doc = Doc(**update_dict)
            await new_doc.insert()
            logger.info(f"Doc created (from webhook): {data.title} ({data.id})")

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
