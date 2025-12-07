from typing import Optional, List
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field, BaseModel
import pymongo

class User(Document):
    """
    语雀用户/团队模型 (Token 拥有者)
    """
    yuque_id: int = Indexed(unique=True)
    login: str
    name: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    books_count: int = 0
    public: int = 0
    created_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"

class Member(Document):
    """
    语雀团队成员模型
    """
    yuque_id: int = Indexed(unique=True)
    login: str
    name: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    hashed_password: Optional[str] = None
    role: Optional[int] = None # 0: Owner, 1: Admin, 2: Member
    status: Optional[int] = None # 1: Normal, 0: Inactive
    is_active: bool = True # 是否在职
    followers: List[int] = [] # 关注者的 yuque_id 列表
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "members"

class Repo(Document):
    """
    语雀知识库模型
    """
    yuque_id: int = Indexed(unique=True)
    name: str
    slug: str
    description: Optional[str] = None
    public: int = 0
    user_id: int  # 归属 User/Group ID
    items_count: int = 0
    watches_count: int = 0
    likes_count: int = 0
    content_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    namespace: Optional[str] = None # e.g. "group/repo"

    class Settings:
        name = "repos"

class ChatSession(Document):
    """
    对话会话模型
    """
    user_id: Optional[str] = None # 关联的用户ID (可选)
    title: Optional[str] = None # 会话标题
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_sessions"

class ChatMessage(Document):
    """
    对话消息模型
    """
    session_id: str = Indexed() # 关联的会话ID
    role: str # user / ai
    content: str
    sources: Optional[List[dict]] = None # AI 回答引用的来源
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "chat_messages"

class Doc(Document):
    """
    语雀文档模型 (合并 TOC 结构信息与 Detail 内容信息)
    """
    # --- 核心标识 ---
    uuid: str = Indexed(unique=True) # TOC 中的唯一标识，用于构建树
    yuque_id: Optional[int] = Indexed(default=None) # 文档 ID (注意：TITLE 类型的节点可能 ID 为空)
    slug: str = Indexed()
    repo_id: int = Indexed()
    
    # --- 结构信息 (来自 TOC) ---
    title: str
    type: str # DOC, TITLE, SHEET, etc.
    parent_uuid: Optional[str] = None # 父节点 UUID
    prev_uuid: Optional[str] = None   # 前一个兄弟节点 UUID
    sibling_uuid: Optional[str] = None # (API 可能会返回)
    child_uuid: Optional[str] = None   # (API 可能会返回)
    depth: int = 0 # 层级深度
    
    # --- 内容详情 (来自 Detail API) ---
    description: Optional[str] = None
    cover: Optional[str] = None
    body: Optional[str] = None # Markdown 或 Lake 格式
    body_html: Optional[str] = None # HTML 格式
    format: Optional[str] = None # lake, markdown, html
    word_count: int = 0
    
    # --- 统计数据 ---
    likes_count: int = 0
    read_count: int = 0
    comments_count: int = 0
    
    # --- 时间信息 ---
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None # 业务更新时间 (语雀 API)
    content_updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    first_published_at: Optional[datetime] = None
    last_synced_at: datetime = Field(default_factory=datetime.utcnow) # 本地同步时间
    
    # --- 作者信息 ---
    user_id: Optional[int] = None # 创建者/最后修改者 ID
    last_editor_id: Optional[int] = None

    class Settings:
        name = "docs"
        indexes = [
            [("title", pymongo.TEXT), ("description", pymongo.TEXT), ("body", pymongo.TEXT)],
            "repo_id",
            "parent_uuid",
            "slug"
        ]

class DocSummary(BaseModel):
    """
    文档列表视图模型 (排除 body/body_html)
    """
    uuid: str
    yuque_id: Optional[int] = None
    slug: str
    repo_id: int
    title: str
    type: str
    parent_uuid: Optional[str] = None
    prev_uuid: Optional[str] = None
    sibling_uuid: Optional[str] = None
    child_uuid: Optional[str] = None
    depth: int = 0
    description: Optional[str] = None
    cover: Optional[str] = None
    format: Optional[str] = None
    word_count: int = 0
    likes_count: int = 0
    read_count: int = 0
    comments_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    content_updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    first_published_at: Optional[datetime] = None
    user_id: Optional[int] = None
    last_editor_id: Optional[int] = None

class Comment(Document):
    """
    语雀评论模型
    """
    yuque_id: int = Indexed(unique=True)
    body_html: Optional[str] = None
    user_id: int
    doc_id: int
    created_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "comments"

# --- Webhook Pydantic Schemas ---

from pydantic import BaseModel

class WebhookUser(BaseModel):
    id: int
    login: str
    name: str
    avatar_url: Optional[str] = None

class WebhookBook(BaseModel):
    id: int
    slug: str
    name: str
    description: Optional[str] = None

class WebhookCommentable(BaseModel):
    id: int
    slug: str
    title: str
    type: Optional[str] = None

class WebhookData(BaseModel):
    action_type: str
    id: int
    user_id: Optional[int] = None # 文档作者 ID
    actor_id: Optional[int] = None # 操作者 ID
    
    # Common / Doc fields
    slug: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    body_html: Optional[str] = None
    book: Optional[WebhookBook] = None 
    user: Optional[WebhookUser] = None 
    actor: Optional[WebhookUser] = None # 操作者 (通常是文档作者/更新者)
    
    # Stats
    word_count: int = 0
    likes_count: int = 0
    read_count: int = 0
    comments_count: int = 0

    # Comment fields
    commentable: Optional[WebhookCommentable] = None 
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    content_updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    first_published_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None

class WebhookPayload(BaseModel):
    data: WebhookData

