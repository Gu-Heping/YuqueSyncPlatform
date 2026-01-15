import pytest
from app.models.schemas import Repo
from app.services.webhook_service import WebhookService
from app.models.schemas import WebhookPayload, WebhookData, WebhookBook

@pytest.mark.asyncio
async def test_webhook_creates_missing_repo(mock_db):
    # 1. Setup payload with a new Repo ID
    new_repo_id = 99999
    payload = WebhookPayload(
        data=WebhookData(
            action_type="publish",
            id=1001,
            slug="new-doc",
            title="New Doc in New Repo",
            body="Content",
            user_id=1,
            book=WebhookBook(
                id=new_repo_id,
                name="New Auto-Created Repo",
                slug="new-repo",
                description="Auto created description"
            )
        )
    )

    # 2. Verify repo does not exist yet
    repo = await Repo.find_one(Repo.yuque_id == new_repo_id)
    assert repo is None

    # 3. Call the service method directly (simulating endpoint behavior)
    service = WebhookService()
    # We don't pass background_tasks here, assuming optional is handled safely in service
    await service.handle_event(payload, background_tasks=None)

    # 4. Verify repo created
    repo = await Repo.find_one(Repo.yuque_id == new_repo_id)
    assert repo is not None
    assert repo.name == "New Auto-Created Repo"
    assert repo.yuque_id == new_repo_id
