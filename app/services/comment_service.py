import logging
from datetime import datetime
from typing import Optional
from fastapi import BackgroundTasks
from app.models.schemas import Comment, Member, WebhookData
from app.services.feed_service import FeedService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

class CommentService:
    """
    评论服务：处理评论的存储、动态生成和通知
    """
    def __init__(self):
        self.feed_service = FeedService()
        self.email_service = EmailService()

    async def handle_comment_webhook(self, data: WebhookData, background_tasks: Optional[BackgroundTasks] = None):
        """
        处理评论相关的 Webhook 事件
        """
        try:
            # 1. 数据持久化 (Upsert Comment)
            await self._upsert_comment(data)

            # 2. 生成动态 (Activity)
            # 仅当操作者是评论者本人时生成动态 (防止重复)
            if data.user_id == data.actor_id:
                # 构造 Activity 摘要：去除 HTML 标签，截取前 100 字符
                summary = self._clean_html(data.body_html)
                
                # 复用 FeedService 创建动态，但需要适配数据结构
                # FeedService.create_activity 期望的是 WebhookData，我们直接传 data
                # 但需要确保 action_type 是 comment 相关
                await self.feed_service.create_activity(data, summary_override=summary)
            
            # 3. 发送邮件通知 (仅在创建评论时)
            if data.action_type in ["comment_create", "comment_reply_create"]:
                await self._handle_notification(data, background_tasks)

        except Exception as e:
            logger.error(f"Error handling comment webhook: {e}", exc_info=True)

    async def _upsert_comment(self, data: WebhookData):
        """
        保存或更新评论
        """
        if not data.commentable:
            logger.warning("Comment event missing 'commentable' info")
            return

        comment = Comment(
            yuque_id=data.id,
            parent_id=data.parent_id,
            doc_id=data.commentable.id,
            user_id=data.user.id,
            body_html=data.body_html,
            created_at=data.created_at or datetime.utcnow(),
            updated_at=data.updated_at or datetime.utcnow()
        )
        
        await Comment.find_one(Comment.yuque_id == comment.yuque_id).upsert(
            {"$set": comment.model_dump(exclude={"id"})},
            on_insert=comment
        )
        logger.info(f"Comment upserted: {data.id} on Doc {data.commentable.id}")

    async def _handle_notification(self, data: WebhookData, background_tasks: Optional[BackgroundTasks]):
        """
        处理邮件通知逻辑
        """
        if not background_tasks:
            return

        # 提取关键信息
        commenter_id = data.user.id
        commenter_name = data.user.name
        
        # 文档作者 ID (注意：WebhookPayload 中 commentable.user.id 是文档作者)
        # 但 WebhookData 定义里 commentable 是 WebhookCommentable，没有 user 字段
        # 我们需要检查 WebhookPayload 的原始结构或假设 data.commentable.user 存在
        # 根据语雀文档，commentable 对象里通常包含 user 信息
        # 这里我们需要小心，因为 Pydantic 模型 WebhookCommentable 可能没定义 user
        # 让我们先假设 WebhookData 里的 commentable 只有 id/slug/title
        # 那么我们需要通过 doc_id 查询 Doc 表来获取作者 ID
        
        doc_author_id = None
        doc_title = data.commentable.title
        doc_slug = data.commentable.slug
        
        # 尝试从本地 Doc 表查找作者
        from app.models.schemas import Doc
        doc = await Doc.find_one(Doc.yuque_id == data.commentable.id)
        if doc:
            doc_author_id = doc.user_id
            doc_title = doc.title # 使用本地标题可能更准
        
        if not doc_author_id:
            logger.warning(f"Could not find author for doc {data.commentable.id}, skipping email notification")
            return

        # 如果是自评，不发送通知
        if doc_author_id == commenter_id:
            return

        # 查找作者的邮箱
        author = await Member.find_one(Member.yuque_id == doc_author_id)
        if not author or not author.email:
            logger.info(f"Author {doc_author_id} has no email, skipping notification")
            return

        # 构造文档 URL (假设前端部署地址，或者直接跳语雀)
        # 这里我们生成跳转到我们平台的 URL
        # 假设前端路由是 /docs/:slug
        # 需要从配置中获取前端 Base URL，这里暂时硬编码或从 settings 获取
        from app.core.config import settings
        # 假设 settings.BASE_URL 是后端地址，我们需要前端地址。
        # 暂时使用相对路径，邮件里需要完整路径
        # 假设前端和后端在同一域名下，或者配置了 FRONTEND_URL
        base_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        repo_id = doc.repo_id if doc else getattr(data, "repo_id", None)
        doc_url = f"{base_url}/repos/{repo_id}/docs/{doc_slug}" if repo_id else f"{base_url}/docs/{doc_slug}"

        # 发送邮件
        background_tasks.add_task(
            self.email_service.send_comment_notification,
            to_email=author.email,
            commenter_name=commenter_name,
            doc_title=doc_title,
            comment_content=self._clean_html(data.body_html),
            doc_url=doc_url
        )
        logger.info(f"Queued comment notification email to {author.email}")

    def _clean_html(self, html_content: str) -> str:
        """
        简单的 HTML 清理，提取纯文本摘要
        """
        if not html_content:
            return ""
        import re
        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', '', html_content)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text).strip()
        # 截取前 100 字符
        return text[:100] + "..." if len(text) > 100 else text
