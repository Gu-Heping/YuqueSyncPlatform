from contextlib import asynccontextmanager
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from app.core.config import settings
from app.models.schemas import User, Repo, Doc, Member, Comment, ChatSession, ChatMessage
from app.api.routes import router as api_router
from app.api.webhook import router as webhook_router

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
        document_models=[User, Repo, Doc, Member, Comment, ChatSession, ChatMessage],
        allow_index_dropping=True
    )
    
    yield
    
    # 关闭连接（可选，Motor 通常会自动管理）
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
app.include_router(webhook_router, prefix="/webhook")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
