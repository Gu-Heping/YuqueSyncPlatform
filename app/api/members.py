from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import Member
from app.api.auth import get_current_user

router = APIRouter()

@router.post("/{target_yuque_id}/follow", summary="关注成员")
async def follow_member(target_yuque_id: int, current_user: Member = Depends(get_current_user)):
    """
    关注指定成员，接收其文档更新通知
    """
    if current_user.yuque_id == target_yuque_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    target_user = await Member.find_one(Member.yuque_id == target_yuque_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # 初始化 followers 列表 (如果为 None)
    if target_user.followers is None:
        target_user.followers = []
        
    if current_user.yuque_id in target_user.followers:
        return {"message": "Already following"}
    
    target_user.followers.append(current_user.yuque_id)
    await target_user.save()
    
    return {"message": f"Successfully followed {target_user.name}"}

@router.post("/{target_yuque_id}/unfollow", summary="取消关注成员")
async def unfollow_member(target_yuque_id: int, current_user: Member = Depends(get_current_user)):
    """
    取消关注指定成员
    """
    target_user = await Member.find_one(Member.yuque_id == target_yuque_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    if target_user.followers and current_user.yuque_id in target_user.followers:
        target_user.followers.remove(current_user.yuque_id)
        await target_user.save()
        return {"message": f"Successfully unfollowed {target_user.name}"}
    
    return {"message": "Not following"}
