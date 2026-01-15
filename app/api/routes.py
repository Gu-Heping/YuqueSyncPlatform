# -*- coding: utf-8 -*-
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from app.services.sync_service import SyncService
from app.services.rag_service import RAGService
from app.services.email_service import EmailService
from app.models.schemas import Doc, Repo, Member, DocSummary, Activity
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

async def run_sync_task():
    """后台同步任务包装器"""
    service = SyncService()
    await service.sync_all()

async def run_member_sync_task(group_id: Optional[int] = None):
    """后台成员同步任务包装器"""
    service = SyncService()
    try:
        if group_id is None:
             # 获取当前用户信息作为 group_id (假设 Token 属于该 Group/User)
            user_data = await service.client.get_user_info()
            if user_data:
                group_id = user_data['id']
        
        if group_id:
            await service.sync_team_members(group_id)
    except Exception as e:
        print(f"Member sync failed: {e}")
    finally:
        await service.client.close()

@router.post("/sync", summary="触发全量同步")
async def trigger_sync(background_tasks: BackgroundTasks):
    """
    触发后台同步任务，从语雀拉取最新数据
    """
    background_tasks.add_task(run_sync_task)
    return {"message": "同步任务已在后台启动"}

@router.post("/sync/members", summary="触发成员同步")
async def trigger_member_sync(background_tasks: BackgroundTasks, group_id: Optional[int] = Query(None, description="团队/用户 ID，不传则使用 Token 所属 ID")):
    """
    触发后台成员同步任务
    """
    background_tasks.add_task(run_member_sync_task, group_id)
    return {"message": "成员同步任务已在后台启动"}

async def run_structure_sync_task(repo_id: int):
    """后台结构同步任务包装器"""
    service = SyncService()
    try:
        await service.sync_repo_structure(repo_id)
    except Exception as e:
        print(f"Structure sync failed: {e}")
    finally:
        await service.client.close()

@router.post("/sync/repos/{repo_id}/structure", summary="触发知识库结构同步(含清理)")
async def trigger_structure_sync(repo_id: int, background_tasks: BackgroundTasks):
    """
    触发后台知识库结构同步任务。
    该任务会拉取最新的 TOC 目录结构，并自动清理本地存在但远程已删除的文档（包括向量库数据）。
    适用于快速修复文档结构或清理脏数据。
    """
    background_tasks.add_task(run_structure_sync_task, repo_id)
    return {"message": f"知识库 {repo_id} 结构同步任务已在后台启动"}

@router.get("/repos", response_model=List[Repo], summary="获取知识库列表")
async def get_repos():
    """
    获取所有已同步的知识库
    """
    return await Repo.find_all().to_list()

@router.get("/members", response_model=List[Member], summary="获取成员列表")
async def get_members(repo_id: Optional[int] = None):
    """
    获取所有已同步的成员，可按知识库筛选
    """
    if repo_id:
        # 如果指定了 repo_id，先从文档中查找贡献者 ID
        # 使用 pymongo 直接查询 distinct user_id
        db_docs = Doc.get_pymongo_collection()
        contributor_ids = await db_docs.distinct("user_id", {"repo_id": repo_id})
        
        if not contributor_ids:
            return []
            
        return await Member.find({"yuque_id": {"$in": contributor_ids}}).to_list()
        
    return await Member.find_all().to_list()

@router.get("/docs", response_model=List[DocSummary], summary="获取文档列表")
async def get_docs(
    repo_id: Optional[int] = None,
    user_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 20
):
    """
    分页获取文档，支持按 repo_id 或 user_id 筛选
    """
    query = Doc.find_all()
    if repo_id:
        query = query.find(Doc.repo_id == repo_id)
    if user_id:
        query = query.find(Doc.user_id == user_id)
    
    # 排除 body 内容以减少传输量，详情请单独查询
    return await query.project(DocSummary).skip(skip).limit(limit).to_list()

@router.get("/docs/{slug}", response_model=Doc, summary="获取文档详情")
async def get_doc_detail(slug: str):
    """
    根据 slug 获取文档详情
    """
    doc = await Doc.find_one(Doc.slug == slug)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.get("/search", response_model=List[Doc], summary="全文搜索")
async def search_docs(q: str = Query(..., min_length=1)):
    """
    基于 MongoDB 文本索引进行全文搜索
    """
    # 使用 $text 操作符进行搜索
    # 注意：需要在 Doc 模型中定义 text 索引
    return await Doc.find({"$text": {"$search": q}}).project(exclude=Doc.body).to_list()

# --- AI / RAG Endpoints ---

@router.post("/search", summary="语义搜索")
async def search_docs_semantic(query: str = Body(..., embed=True), limit: int = 20, repo_id: Optional[int] = None):
    """
    基于向量的语义搜索
    """
    rag = RAGService()
    return await rag.search(query, limit=limit, repo_id=repo_id)

@router.post("/chat/rag", summary="RAG 智能问答")
async def chat_rag(
    query: str = Body(..., embed=True), 
    repo_id: Optional[int] = Body(None, embed=True),
    session_id: Optional[str] = Body(None, embed=True)
):
    """
    基于知识库的智能问答 (支持多轮对话)
    """
    rag = RAGService()
    return await rag.chat(query, repo_id=repo_id, session_id=session_id)

@router.post("/ai/explain", summary="AI 助读/解释")
async def ai_explain(text: str = Body(..., embed=True)):
    """
    解释选中的文本或代码
    """
    rag = RAGService()
    return await rag.explain(text)

@router.post("/email/test", summary="发送测试邮件")
async def send_test_email(to_email: str = Body(..., embed=True)):
    """
    向指定邮箱发送测试邮件
    """
    email_service = EmailService()
    try:
        await email_service.send_test_email(to_email)
        return {"message": f"测试邮件已发送至 {to_email}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"发送邮件失败: {str(e)}")

async def run_repair_created_at_task():
    """
    后台任务：修复文档的 created_at 字段
    """
    logger.info("开始修复文档 created_at 字段...")
    try:
        # 使用 motor collection 直接操作
        db_docs = Doc.get_pymongo_collection()
        db_activities = Activity.get_pymongo_collection()
        
        # 查找 created_at 为空的文档
        cursor = db_docs.find({"created_at": None})
        docs_to_fix = await cursor.to_list(None)
        
        logger.info(f"发现 {len(docs_to_fix)} 个文档缺少 created_at")
        
        fixed_count = 0
        for doc in docs_to_fix:
            uuid = doc.get("uuid")
            title = doc.get("title")
            doc_id = doc.get("_id")
            
            # 1. 尝试从 Activity 中查找 'publish' 记录
            activity = await db_activities.find_one({
                "doc_uuid": uuid,
                "action_type": "publish"
            })
            
            # 尝试通过标题查找 (Fallback)
            if not activity and title:
                activity = await db_activities.find_one({
                    "doc_title": title,
                    "action_type": "publish"
                })
                
            new_created_at = None
            if activity:
                new_created_at = activity.get("created_at")
                logger.info(f"通过 Activity 找到时间: {title} -> {new_created_at}")
            
            # 2. 如果没找到 Activity，尝试使用 first_published_at
            if not new_created_at:
                new_created_at = doc.get("first_published_at")
                if new_created_at:
                    logger.info(f"使用 first_published_at: {title} -> {new_created_at}")
            
            # 3. 执行更新
            if new_created_at:
                await db_docs.update_one(
                    {"_id": doc_id},
                    {"$set": {"created_at": new_created_at}}
                )
                fixed_count += 1
            else:
                logger.warning(f"无法找到文档创建时间: {title} ({uuid})")
                
        logger.info(f"修复完成，共修复 {fixed_count} 个文档")
        
    except Exception as e:
        logger.error(f"修复任务失败: {e}", exc_info=True)

@router.post("/repair/created-at", summary="修复文档创建时间")
async def trigger_repair_created_at(background_tasks: BackgroundTasks):
    """
    触发后台任务，修复文档中缺失的 created_at 字段。
    逻辑：
    1. 查找 created_at 为空的文档
    2. 在 Activity 表中查找对应的 publish 记录
    3. 或使用 first_published_at 字段
    4. 更新文档
    """
    background_tasks.add_task(run_repair_created_at_task)
    return {"message": "文档创建时间修复任务已在后台启动，请查看日志关注进度"}
