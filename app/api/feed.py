from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime
from app.models.schemas import Activity, Member
from app.api.auth import get_current_user
from beanie.operators import In

router = APIRouter()

@router.get("/", response_model=List[Activity])
async def get_feed(
    filter_type: str = Query("all", alias="filter"), # all or following
    repo_id: Optional[int] = None,
    limit: int = 20,
    current_user: Member = Depends(get_current_user)
):
    """
    获取动态列表
    """
    # 构建查询条件
    criteria = []
    
    if repo_id:
        criteria.append(Activity.repo_id == repo_id)
    
    if filter_type == "following":
        # 查询我关注的所有 Member 的 yuque_id
        following_members = await Member.find({"followers": current_user.yuque_id}).to_list()
        following_ids = [m.yuque_id for m in following_members]
        
        if not following_ids:
            return []
            
        criteria.append(In(Activity.author_id, following_ids))
    
    # 使用 find(*criteria) 展开参数
    query = Activity.find(*criteria)
    
    return await query.sort("-created_at").limit(limit).to_list()

@router.get("/status")
async def get_feed_status(current_user: Member = Depends(get_current_user)):
    """
    检查是否有新动态
    """
    latest_activity = await Activity.find().sort("-created_at").first_or_none()
    
    has_new = False
    if latest_activity:
        # 如果从未读过 (1970年)，且有动态，则为 true
        # 或者最新动态时间 > 最后阅读时间
        if latest_activity.created_at > current_user.last_read_feed_at:
            has_new = True
            
    return {"has_new": has_new}

@router.post("/read")
async def mark_feed_read(current_user: Member = Depends(get_current_user)):
    """
    标记动态已读
    """
    current_user.last_read_feed_at = datetime.utcnow()
    await current_user.save()
    return {"status": "ok"}
