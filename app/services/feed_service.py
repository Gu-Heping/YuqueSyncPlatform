import logging
from datetime import datetime
from bs4 import BeautifulSoup
from app.models.schemas import Activity, Member, Doc, Repo
from typing import Optional

logger = logging.getLogger(__name__)

class FeedService:
    """
    动态流服务：处理动态的生成、查询和删除
    """
    
    async def create_activity(self, payload_data, summary_override: Optional[str] = None):
        """
        根据 Webhook Payload 创建动态
        """
        try:
            # 1. 提取基础信息
            action_type = payload_data.action_type
            
            # 判断是否为评论相关操作
            is_comment = action_type.startswith('comment')
            
            if is_comment and payload_data.commentable:
                # 评论事件：主体是评论，关联对象是文档
                doc_id = payload_data.commentable.id
                doc_title = payload_data.commentable.title
                doc_slug = payload_data.commentable.slug
                # 评论事件中，book 信息可能在 payload_data.book (如果 webhook 包含)
                # 或者我们需要通过 doc_id 查库，或者暂时留空
                repo_id = payload_data.book.id if payload_data.book else 0 
            else:
                # 文档事件
                doc_id = payload_data.id
                doc_title = payload_data.title
                doc_slug = payload_data.slug
                repo_id = payload_data.book.id if payload_data.book else 0

            # 2. 获取知识库名称
            repo_name = "未知知识库"
            
            # 如果 repo_id 缺失 (例如评论事件)，尝试通过 doc_id 查找文档进而获取 repo_id
            if not repo_id and doc_id:
                doc = await Doc.find_one(Doc.yuque_id == doc_id)
                if doc:
                    repo_id = doc.repo_id
                    # 顺便也可以修正 doc_slug 和 doc_title，如果 payload 里缺的话
                    if not doc_slug: doc_slug = doc.slug
                    if not doc_title: doc_title = doc.title

            if repo_id:
                repo = await Repo.find_one(Repo.yuque_id == repo_id)
                if repo:
                    repo_name = repo.name
                elif payload_data.book and hasattr(payload_data.book, 'name'):
                    repo_name = payload_data.book.name

            # 3. 获取作者信息
            # 评论事件中，user_id 是评论者
            user_id = payload_data.user.id if payload_data.user else payload_data.user_id
            author_name = "未知用户"
            author_avatar = None
            
            # 优先从 payload 获取用户信息 (减少数据库查询)
            # 修正：优先使用 actor (操作者) 作为动态的 author，因为 user 可能是文档拥有者(可能是团队)
            if payload_data.actor:
                author_name = payload_data.actor.name
                author_avatar = payload_data.actor.avatar_url
            elif payload_data.user:
                author_name = payload_data.user.name
                author_avatar = payload_data.user.avatar_url
            else:
                # 查库兜底
                member = await Member.find_one(Member.yuque_id == user_id)
                if member:
                    author_name = member.name
                    author_avatar = member.avatar_url

            # 4. 生成摘要 (清洗 HTML)
            summary = ""
            if summary_override:
                summary = summary_override
            elif payload_data.body_html:
                soup = BeautifulSoup(payload_data.body_html, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                summary = text[:100] + "..." if len(text) > 100 else text
            elif payload_data.body:
                summary = payload_data.body[:100] + "..." if len(payload_data.body) > 100 else payload_data.body

            # 5. 创建 Activity
            activity = Activity(
                doc_uuid=str(doc_id), # 使用 yuque_id 作为关联键
                doc_title=doc_title or "无标题",
                doc_slug=doc_slug or "",
                repo_id=repo_id,
                repo_name=repo_name,
                author_id=user_id,
                author_name=author_name,
                author_avatar=author_avatar,
                action_type=action_type,
                summary=summary,
                created_at=datetime.utcnow()
            )
            await activity.insert()
            logger.info(f"Activity created: {author_name} {action_type} {doc_title}")
            
        except Exception as e:
            logger.error(f"Failed to create activity: {e}", exc_info=True)

    async def delete_activity(self, doc_id: int):
        """
        删除指定文档的所有动态
        """
        try:
            result = await Activity.find(Activity.doc_uuid == str(doc_id)).delete()
            if result:
                logger.info(f"Deleted activities for doc {doc_id}")
        except Exception as e:
            logger.error(f"Failed to delete activities for doc {doc_id}: {e}")
