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

        # 尝试从语雀 API 获取完整的文档详情 (包含字数、点赞、作者等统计信息)
        # Webhook 推送的数据通常不包含统计信息，需要主动拉取
        from app.services.yuque_client import YuqueClient
        client = YuqueClient()
        detail = {}
        try:
            # 使用 slug 或 id 获取详情
            slug_or_id = data.slug or str(data.id)
            detail = await client.get_doc_detail(data.book.id, slug_or_id)
            logger.info(f"Fetched full doc detail for {data.title} ({data.id})")
        except Exception as e:
            logger.error(f"Failed to fetch doc detail for {data.id}: {e}")
        finally:
            await client.close()

        # 尝试查找现有文档
        doc = await Doc.find_one(Doc.yuque_id == data.id)
        
        # 准备更新的数据
        # 优先使用 API 详情中的数据 (统计信息等)，如果获取失败则回退到 Webhook 数据
        update_dict = {
            "title": detail.get("title") or data.title,
            "slug": detail.get("slug") or data.slug,
            "repo_id": data.book.id,
            "user_id": detail.get("user_id") or (data.user.id if data.user else None),
            "body": detail.get("body") or data.body,
            "body_html": detail.get("body_html") or data.body_html,
            "updated_at": data.updated_at or datetime.utcnow(),
            "content_updated_at": data.content_updated_at,
            "published_at": data.published_at,
            "first_published_at": data.first_published_at,
            # 补充统计信息
            "word_count": detail.get("word_count", 0),
            "likes_count": detail.get("likes_count", 0),
            "read_count": detail.get("read_count", 0),
            "comments_count": detail.get("comments_count", 0),
            "description": detail.get("description"),
            "cover": detail.get("cover"),
        }
        
        if doc:
            await doc.update({"$set": update_dict})
            logger.info(f"Doc updated: {update_dict['title']} ({data.id})")
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
