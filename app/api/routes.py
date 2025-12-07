# -*- coding: utf-8 -*-
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from app.services.sync_service import SyncService
from app.services.rag_service import RAGService
from app.models.schemas import Doc, Repo, Member, DocSummary

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

@router.get("/repos", response_model=List[Repo], summary="获取知识库列表")
async def get_repos():
    """
    获取所有已同步的知识库
    """
    return await Repo.find_all().to_list()

@router.get("/members", response_model=List[Member], summary="获取成员列表")
async def get_members():
    """
    获取所有已同步的成员
    """
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
