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
    limit: int = 20,
    current_user: Member = Depends(get_current_user)
):
    """
    获取动态列表
    """
    query = Activity.find()
    
    if filter_type == "following":
        if not current_user.followers: # 注意：Member.followers 存的是"关注我的人"，我们需要"我关注的人"
            # Member 模型中 followers 字段定义是 List[int] = [] # 关注者的 yuque_id 列表
            # 这是一个被动关系。我们需要查询 Member 表中 followers 包含 current_user.yuque_id 的人
            # 或者我们需要在 Member 模型中增加 following 字段。
            # 让我们检查 Member 模型定义。
            # Member.followers 是 "关注者的 yuque_id 列表"。
            # 所以 "我关注的人" 是那些 followers 列表中包含 current_user.yuque_id 的 Member。
            
            # 查询我关注的所有 Member 的 yuque_id
            following_members = await Member.find({"followers": current_user.yuque_id}).to_list()
            following_ids = [m.yuque_id for m in following_members]
            
            if not following_ids:
                return []
                
            query = Activity.find(In(Activity.author_id, following_ids))
    
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
