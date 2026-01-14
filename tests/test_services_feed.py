import pytest
from app.services.feed_service import FeedService
from app.models.schemas import Activity, Doc, Repo, Member
from dataclasses import dataclass
from typing import Optional

# Mocking WebhookPayload structures
@dataclass
class MockActor:
    id: int = 123
    name: str = "Test User"
    avatar_url: str = "http://avatar"

@dataclass
class MockBook:
    id: int = 456
    name: str = "Test Repo"

@dataclass
class MockPayload:
    action_type: str
    id: int = 1
    title: str = "Test Doc"
    slug: str = "test-doc"
    body: str = "Test Body"
    body_html: str = "<p>Test Body</p>"
    actor: Optional[MockActor] = None
    user: Optional[MockActor] = None
    book: Optional[MockBook] = None
    commentable: Optional[dict] = None
    user_id: int = 123

    def __post_init__(self):
        if self.actor is None:
            self.actor = MockActor()
        if self.book is None:
            self.book = MockBook()

@pytest.mark.asyncio
async def test_create_activity_doc_update(mock_db):
    service = FeedService()
    payload = MockPayload(action_type="publish")
    
    await service.create_activity(payload)
    
    activities = await Activity.find_all().to_list()
    assert len(activities) == 1
    activity = activities[0]
    assert activity.action_type == "publish"
    assert activity.doc_title == "Test Doc"
    assert activity.repo_name == "Test Repo"
    assert activity.author_name == "Test User"

@pytest.mark.asyncio
async def test_create_activity_comment(mock_db):
    service = FeedService()
    # Mock commentable structure for comment payload
    @dataclass
    class MockCommentable:
        id: int = 1
        title: str = "Test Doc"
        slug: str = "test-doc"

    payload = MockPayload(action_type="comment_create")
    payload.commentable = MockCommentable()
    
    await service.create_activity(payload)
    
    activities = await Activity.find_all().to_list()
    assert len(activities) == 1
    activity = activities[0]
    assert activity.action_type == "comment_create"
    assert activity.doc_title == "Test Doc"

@pytest.mark.asyncio
async def test_delete_activity(mock_db):
    service = FeedService()
    # Insert dummy activity
    activity = Activity(
        doc_uuid="1",
        doc_title="To Delete",
        doc_slug="del",
        repo_id=1,
        repo_name="Repo",
        author_id=1,
        author_name="Me",
        action_type="publish",
        created_at=None
    )
    await activity.insert()
    
    assert await Activity.count() == 1
    
    await service.delete_activity(1)
    
    assert await Activity.count() == 0
