import pytest
import os

# Set env vars BEFORE importing app modules to pass Settings validation
os.environ["YUQUE_TOKEN"] = "test_token"
os.environ["MONGO_URI"] = "mongodb://mock"
os.environ["MONGO_DB_NAME"] = "test_db"

import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from mongomock_motor import AsyncMongoMockClient
from beanie import init_beanie
from app.models.schemas import User, Member, Doc, Repo, Comment, Activity
from app.services.sync_service import SyncService
from app.core.config import settings

# Standalone Test for Repo Cleanup
@pytest.fixture
async def local_mock_db():
    client = AsyncMongoMockClient()
    db = client["test_cleanup_db"]
    await init_beanie(
        database=db,
        document_models=[User, Member, Doc, Repo, Comment, Activity]
    )
    return db

@pytest.mark.asyncio
async def test_repo_cleanup_on_404(local_mock_db):
    print(">>> Test started: Repo Cleanup")
    
    repo_id_to_delete = 404404
    
    # 1. Seed DB
    # Create the Repo to be deleted
    await Repo(
        yuque_id=repo_id_to_delete,
        name="Zombie Repo",
        slug="zombie",
        user_id=1,
        items_count=5,
        created_at=None,
        updated_at=None
    ).insert()
    
    # Create valid docs in this repo
    await Doc(
        uuid="uuid-1",
        yuque_id=101,
        repo_id=repo_id_to_delete,
        title="Doc 1",
        slug="doc-1",
        body="content",
        created_at=None
    ).insert()
    
    await Doc(
        uuid="uuid-2",
        yuque_id=102,
        repo_id=repo_id_to_delete,
        title="Doc 2",
        slug="doc-2",
        body="content",
        created_at=None
    ).insert()

    # Create a doc in ANOTHER repo (should NOT be deleted)
    safe_repo_id = 100100
    await Repo(yuque_id=safe_repo_id, name="Safe Repo", slug="safe", user_id=1, created_at=None, updated_at=None).insert()
    await Doc(
        uuid="uuid-safe",
        yuque_id=200, 
        repo_id=safe_repo_id, 
        title="Safe Doc", 
        slug="safe-doc",
        body="content",
        created_at=None
    ).insert()
    
    print(">>> DB Seeded")
    
    # 2. Mock Yuque Client to raise 404
    with patch("app.services.sync_service.YuqueClient") as MockClient:
        mock_instance = MockClient.return_value
        
        # Construct a 404 exception
        request = httpx.Request("GET", "http://test")
        response = httpx.Response(404, request=request)
        error_404 = httpx.HTTPStatusError("404 Not Found", request=request, response=response)
        
        mock_instance.get_repo_toc = AsyncMock(side_effect=error_404)
        
        # Mock RAG service to avoid external calls
        repo_count_before = await Repo.count()
        doc_count_before = await Doc.count()
        print(f">>> Before: Repos={repo_count_before}, Docs={doc_count_before}")

        service = SyncService()
        # Mock the internal RAG service delete call
        service.rag_service.delete_doc = AsyncMock()
        
        # 3. Trigger Sync Structure
        await service.sync_repo_structure(repo_id_to_delete)
        print(">>> Sync Structure called")
        
        # 4. Verify Cleanup
        # Verify Repo deleted
        assert await Repo.find_one(Repo.yuque_id == repo_id_to_delete) is None
        assert await Repo.find_one(Repo.yuque_id == safe_repo_id) is not None
        
        # Verify Docs deleted
        assert await Doc.find_one(Doc.yuque_id == 101) is None
        assert await Doc.find_one(Doc.yuque_id == 102) is None
        assert await Doc.find_one(Doc.yuque_id == 200) is not None # Safe doc remains
        
        print(">>> Cleanup Verified: Repo and its Docs are gone, others remain.")
