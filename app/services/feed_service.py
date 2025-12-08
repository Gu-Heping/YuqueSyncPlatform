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
    
    async def create_activity(self, payload_data):
        """
        根据 Webhook Payload 创建动态
        """
        try:
            # 1. 提取基础信息
            doc_id = payload_data.id
            doc_title = payload_data.title
            repo_id = payload_data.book.id
            action_type = payload_data.action_type
            
            # 2. 获取知识库名称
            repo_name = "未知知识库"
            repo = await Repo.find_one(Repo.yuque_id == repo_id)
            if repo:
                repo_name = repo.name
            else:
                # 尝试从 payload 中获取 (如果 payload 结构中有)
                # payload.book 通常包含 name
                if hasattr(payload_data.book, 'name'):
                    repo_name = payload_data.book.name

            # 3. 获取作者信息
            user_id = payload_data.user_id
            author_name = "未知用户"
            author_avatar = None
            
            member = await Member.find_one(Member.yuque_id == user_id)
            if member:
                author_name = member.name
                author_avatar = member.avatar_url
            elif payload_data.actor: # 尝试从 actor 获取
                author_name = payload_data.actor.name
                author_avatar = payload_data.actor.avatar_url

            # 4. 生成摘要 (清洗 HTML)
            summary = ""
            if payload_data.body_html:
                soup = BeautifulSoup(payload_data.body_html, "html.parser")
                text = soup.get_text(separator=" ", strip=True)
                summary = text[:100] + "..." if len(text) > 100 else text
            elif payload_data.body:
                summary = payload_data.body[:100] + "..." if len(payload_data.body) > 100 else payload_data.body

            # 5. 创建 Activity
            # 检查是否已存在相同 doc_id 和 action_type 的最近记录 (防止重复)
            # 这里简化处理，直接插入
            
            activity = Activity(
                doc_uuid=str(doc_id), # 使用 yuque_id 作为关联键
                doc_title=doc_title,
                doc_slug=payload_data.slug,
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
            logger.error(f"Failed to create activity: {e}")

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
