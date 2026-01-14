import pytest
from app.services.comment_service import CommentService
from app.models.schemas import Comment, WebhookData, WebhookCommentable, WebhookUser, Doc, Member
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# Define MockEmailService to prevent actual email sending attempts
class MockEmailService:
    async def send_comment_notification(self, to_email, commenter_name, doc_title, comment_content, doc_url):
        pass

@pytest.mark.asyncio
async def test_handle_comment_webhook(mock_db, monkeypatch):
    # Mock EmailService
    monkeypatch.setattr("app.services.comment_service.EmailService", MockEmailService)
    
    service = CommentService()
    
    # Needs to exist for notification logic (doc author lookup)
    author = Member(yuque_id=999, login="author", name="Author", email="author@example.com")
    await author.insert()
    
    doc = Doc(uuid="uuid", yuque_id=100, slug="doc-slug", repo_id=10, title="Doc Title", type="DOC", user_id=999)
    await doc.insert()

    # Mock WebhookData
    data = WebhookData(
        action_type="comment_create",
        id=500,
        user_id=123, # Commenter
        actor_id=123,
        body_html="<p>Nice post!</p>",
        commentable=WebhookCommentable(id=100, slug="doc-slug", title="Doc Title"),
        user=WebhookUser(id=123, login="commenter", name="Commenter"),
        created_at=datetime.utcnow()
    )
    
    # We need a BackgroundTasks mock, or just pass None and verify core logic
    # The service checks `if not background_tasks: return` for notifications.
    # To test notifications, we need a mock background_tasks
    class MockBackgroundTasks:
        def add_task(self, func, *args, **kwargs):
            self.task = (func, args, kwargs)
            
    bt = MockBackgroundTasks()

    await service.handle_comment_webhook(data, background_tasks=bt)
    
    # Verify Comment created
    comment = await Comment.find_one(Comment.yuque_id == 500)
    assert comment is not None
    assert comment.doc_id == 100
    assert comment.user_id == 123
    assert comment.body_html == "<p>Nice post!</p>"

    # Verify Activity created (via FeedService)
    # FeedService is instantiated inside CommentService
    from app.models.schemas import Activity
    activity = await Activity.find_one(Activity.action_type == "comment_create")
    assert activity is not None
    assert activity.summary == "Nice post!"

    # Verify Notification triggered (MockBackgroundTasks captured it)
    assert hasattr(bt, 'task')
    func, args, kwargs = bt.task
    # args: (to_email, commenter_name, doc_title, comment_content, doc_url) per signature? 
    # check call arguments
    assert kwargs['to_email'] == "author@example.com"
    assert kwargs['commenter_name'] == "Commenter"
    assert kwargs['comment_content'] == "Nice post!"
