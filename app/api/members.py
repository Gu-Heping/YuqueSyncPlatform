from fastapi import Query
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import Member
from app.api.auth import get_current_user


router = APIRouter()

@router.get("/count_with_email", summary="统计所有绑定邮箱的用户数")
async def count_members_with_email():
    """
    返回所有绑定邮箱的用户数量
    """
    members = await Member.find({"email": {"$ne": None}}).to_list()
    count = sum(1 for m in members if m.email and m.email.strip())
    return {"count": count}


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

@router.post("/follow/all", summary="一键关注所有成员")
async def follow_all_members(repo_id: int = Query(None), current_user: Member = Depends(get_current_user)):
    """
    当前用户一键关注所有其他用户 (支持按知识库筛选)
    """
    query = {"yuque_id": {"$ne": current_user.yuque_id}}
    
    if repo_id:
        from app.models.schemas import Doc
        # 查找该知识库下的贡献者
        db_docs = Doc.get_pymongo_collection()
        contributor_ids = await db_docs.distinct("user_id", {"repo_id": repo_id})
        if not contributor_ids:
             return {"message": "No members found for this repo", "count": 0}
        
        # 增加 ID 过滤条件
        query["yuque_id"] = {"$in": contributor_ids}

    # 查找符合条件的用户
    target_members = await Member.find(query).to_list()
    
    count = 0
    for member in target_members:
        # 使用 atomic update $addToSet 防止重复
        # 直接使用 Motor collection 的 update_one 以获取准确的 modified_count
        result = await Member.get_pymongo_collection().update_one(
            {"_id": member.id},
            {"$addToSet": {"followers": current_user.yuque_id}}
        )
        
        if result.modified_count > 0:
            count += 1
            
    return {"message": f"Successfully followed {count} new members", "count": count}

@router.post("/unfollow/all", summary="一键取消关注所有成员")
async def unfollow_all_members(repo_id: int = Query(None), current_user: Member = Depends(get_current_user)):
    """
    当前用户一键取消关注所有其他用户 (支持按知识库筛选)
    """
    # 基础查询：被当前用户关注的用户
    query = {"followers": current_user.yuque_id}
    
    if repo_id:
        from app.models.schemas import Doc
        # 查找该知识库下的贡献者
        db_docs = Doc.get_pymongo_collection()
        contributor_ids = await db_docs.distinct("user_id", {"repo_id": repo_id})
        if not contributor_ids:
             return {"message": "No members found for this repo", "count": 0}
        
        # 增加 ID 过滤条件 (必须在贡献者列表中)
        query["yuque_id"] = {"$in": contributor_ids}

    # 查找符合条件的用户
    followed_members = await Member.find(query).to_list()
    
    count = 0
    for member in followed_members:
        # 使用 atomic update $pull 移除
        # 直接使用 Motor collection 的 update_one 以获取准确的 modified_count
        result = await Member.get_pymongo_collection().update_one(
            {"_id": member.id},
            {"$pull": {"followers": current_user.yuque_id}}
        )
        
        if result.modified_count > 0:
            count += 1
            
    return {"message": f"Successfully unfollowed {count} members", "count": count}
