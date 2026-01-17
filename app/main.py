from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.models.schemas import User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router
from app.api.auth import router as auth_router
from app.api.members import router as members_router
from app.api.feed import router as feed_router
from app.api.dashboard import router as dashboard_router
from app.api.comments import router as comments_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理：启动时连接数据库，关闭时清理
    """
    # 1. 创建 Motor 客户端
    client = AsyncIOMotorClient(settings.MONGO_URI)
    
    # 2. 初始化 Beanie (ODM)
    await init_beanie(
        database=client[settings.MONGO_DB_NAME],
        document_models=[User, Repo, Doc, Member, Comment, ChatSession, ChatMessage, Activity],
        allow_index_dropping=True
    )
    
    # 3. 启动定时任务调度器
    from app.services.scheduler import SchedulerService
    scheduler_service = SchedulerService()
    scheduler_service.start()
    
    yield
    
    # 4. 关闭清理
    scheduler_service.stop()
    # client.close()

app = FastAPI(
    title="Yuque Sync Platform",
    description="语雀知识库同步与检索平台 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(members_router, prefix="/api/v1/members")
app.include_router(feed_router, prefix="/api/v1/feed", tags=["Feed"])
app.include_router(dashboard_router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(comments_router, prefix="/api/v1/comments", tags=["Comments"])
app.include_router(webhook_router, prefix="/webhook")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
