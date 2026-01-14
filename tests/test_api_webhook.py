import pytest
from app.models.schemas import WebhookPayload, WebhookData

@pytest.mark.asyncio
async def test_webhook_receive(client, mock_db):
    payload = {
        "data": {
            "action_type": "publish",
            "id": 123,
            "slug": "test-doc",
            "title": "Test Document",
            "body": "Content",
            "user_id": 1,
            "book": {
                "id": 10,
                "name": "Test Book",
                "slug": "test-book"
            }
        }
    }
    
    # Needs background tasks to work without error
    # The endpoint uses BackgroundTasks.
    # Starlette/FastAPI TestClient handles BackgroundTasks by executing them synchronously or ignoring?
    # Actually httpx.AsyncClient with asgi app supports it.
    
    response = await client.post("/api/v1/webhook/yuque", json=payload)
    assert response.status_code == 200
    assert response.json() == {"message": "Event received"}
