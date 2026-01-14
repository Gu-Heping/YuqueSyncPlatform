import pytest
from httpx import AsyncClient
from app.main import app
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from app.models.schemas import User, Member, Doc, Repo, Comment, Activity, WebhookPayload
from app.core.config import settings
import os

@pytest.fixture
def anyio_backend():
    return 'asyncio'

@pytest.fixture
def app():
    from app.main import app
    return app

@pytest.fixture
async def mock_db():
    client = AsyncMongoMockClient()
    db = client[settings.MONGO_DB_NAME]
    
    # Initialize Beanie with the mock database
    await init_beanie(
        database=db,
        document_models=[
            User, Member, Doc, Repo, Comment, Activity
        ]
    )
    return db

@pytest.fixture
async def client(mock_db):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("YUQUE_TOKEN", "test_token")
    monkeypatch.setenv("MONGO_URI", "mongodb://mock")
    monkeypatch.setenv("MONGO_DB_NAME", "test_db")
