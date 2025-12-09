from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Optional
from datetime import datetime
from app.models.schemas import Comment, Member, Doc, Repo
from app.api.auth import get_current_user
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", summary="获取评论列表")
async def get_comments(
    doc_id: int = None, 
    limit: int = 20, 
    skip: int = 0,
    filter_type: str = Query('all', enum=['all', 'me']),
    current_user: Member = Depends(get_current_user)
):
    """
    获取评论列表，支持按文档 ID 筛选，以及筛选"与我相关"的评论
    """
    query = {}
    if doc_id:
        query["doc_id"] = doc_id
        
    if filter_type == 'me':
        logger.info(f"Fetching comments for user: {current_user.name} ({current_user.yuque_id})")
        
        # 筛选与我相关的评论：
        # 1. 我发布的文档下的评论
        # 2. 我拥有的知识库下的文档的评论
        
        # 查找我拥有的文档 ID
        my_docs = await Doc.find(Doc.user_id == current_user.yuque_id).to_list()
        my_doc_ids = set(d.yuque_id for d in my_docs if d.yuque_id)
        logger.info(f"User owns {len(my_doc_ids)} docs directly")
        
        # 查找我拥有的知识库 ID
        my_repos = await Repo.find(Repo.user_id == current_user.yuque_id).to_list()
        my_repo_ids = [r.yuque_id for r in my_repos if r.yuque_id]
        logger.info(f"User owns {len(my_repo_ids)} repos")
        
        if my_repo_ids:
            # 查找这些知识库下的所有文档
            repo_docs = await Doc.find(Doc.repo_id << my_repo_ids).to_list()
            my_doc_ids.update(d.yuque_id for d in repo_docs if d.yuque_id)
        
        # 构建 OR 查询：(评论在我的文档下) OR (评论是我发的)
        or_conditions = []
        if my_doc_ids:
            or_conditions.append({"doc_id": {"$in": list(my_doc_ids)}})
        
        or_conditions.append({"user_id": current_user.yuque_id})
        
        query["$or"] = or_conditions
        logger.info(f"Query conditions: {query}")

    comments = await Comment.find(query).sort("-created_at").skip(skip).limit(limit).to_list()
    logger.info(f"Found {len(comments)} comments")
    
    # 收集所有评论者的 ID
    user_ids = list(set(c.user_id for c in comments))
    
    # 批量查询用户信息
    if user_ids:
        users = await Member.find({"yuque_id": {"$in": user_ids}}).to_list()
    else:
        users = []
    user_map = {u.yuque_id: u for u in users}
    
    # 收集所有文档 ID (为了返回文档标题)
    doc_ids = list(set(c.doc_id for c in comments))
    if doc_ids:
        docs = await Doc.find({"yuque_id": {"$in": doc_ids}}).to_list()
    else:
        docs = []
    doc_map = {d.yuque_id: d for d in docs}

    # 组装结果
    result = []
    for c in comments:
        c_dict = c.model_dump()
        
        # 填充用户信息
        user = user_map.get(c.user_id)
        if user:
            c_dict['user'] = {
                'name': user.name,
                'avatar_url': user.avatar_url,
                'login': user.login
            }
        else:
            c_dict['user'] = {
                'name': f"User {c.user_id}",
                'avatar_url': None,
                'login': str(c.user_id)
            }
            
        # 填充文档信息
        doc = doc_map.get(c.doc_id)
        if doc:
            c_dict['doc_title'] = doc.title
            c_dict['doc_slug'] = doc.slug
            c_dict['repo_id'] = doc.repo_id
            
        result.append(c_dict)
        
    return result

@router.get("/status", summary="检查是否有新评论")
async def check_new_comments(current_user: Member = Depends(get_current_user)):
    """
    检查是否有晚于用户上次阅读时间的评论
    仅统计当前用户创建的文档下的新评论
    """
    last_read = current_user.last_read_comments_at or datetime(1970, 1, 1)
    
    # 1. 找到当前用户创建的所有文档 ID
    # 注意：Doc.user_id 是文档创建者/拥有者
    user_docs = await Doc.find(Doc.user_id == current_user.yuque_id).to_list()
    user_doc_ids = [d.yuque_id for d in user_docs]
    
    if not user_doc_ids:
        return {"has_new": False, "count": 0}

    # 2. 查找这些文档下的新评论
    # 排除用户自己发的评论 (可选，但通常提醒是给别人的评论)
    # 这里严格按照需求：有人评论了我的文档 -> 提醒
    count = await Comment.find(
        {"doc_id": {"$in": user_doc_ids}},
        Comment.created_at > last_read
    ).count()
    
    return {"has_new": count > 0, "count": count}

@router.get("/doc/{doc_yuque_id}", summary="获取特定文档的评论")
async def get_doc_comments(doc_yuque_id: int):
    """
    获取指定文档的评论列表
    """
    comments = await Comment.find(Comment.doc_id == doc_yuque_id).sort("-created_at").to_list()
    
    # 收集所有评论者的 ID
    user_ids = list(set(c.user_id for c in comments))
    
    # 批量查询用户信息
    if user_ids:
        users = await Member.find({"yuque_id": {"$in": user_ids}}).to_list()
    else:
        users = []
    user_map = {u.yuque_id: u for u in users}
    
    # 组装结果
    result = []
    for c in comments:
        c_dict = c.model_dump()
        
        # 填充用户信息
        user = user_map.get(c.user_id)
        if user:
            c_dict['user'] = {
                'name': user.name,
                'avatar_url': user.avatar_url,
                'login': user.login
            }
        else:
            c_dict['user'] = {
                'name': f"User {c.user_id}",
                'avatar_url': None,
                'login': str(c.user_id)
            }
        result.append(c_dict)
        
    return result

@router.post("/read", summary="标记评论已读")
async def mark_comments_read(current_user: Member = Depends(get_current_user)):
    """
    更新用户的 last_read_comments_at
    """
    current_user.last_read_comments_at = datetime.utcnow()
    await current_user.save()
    return {"message": "Marked as read"}
