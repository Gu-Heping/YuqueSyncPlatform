from fastapi import APIRouter, Body, BackgroundTasks
from app.models.schemas import WebhookPayload
from app.services.webhook_service import WebhookService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/yuque", summary="接收语雀 Webhook 推送")
async def handle_yuque_webhook(background_tasks: BackgroundTasks, payload: WebhookPayload = Body(...)):
    """
    接收并处理来自语雀的 Webhook 事件
    """
    service = WebhookService()
    try:
        await service.handle_event(payload, background_tasks)
        return {"message": "Event received"}
    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        # 返回 200 避免语雀无限重试，错误已记录
        return {"message": "Event received with errors"}
