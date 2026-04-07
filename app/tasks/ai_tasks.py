import asyncio
from app.core.celery import celery_app
from app.services.ai_logic import execute_ai_agent
from app.core.logger import app_logger as logger

@celery_app.task(name="process_ai_request", bind=True, max_retries=3)
def process_ai_request_task(self, phone: str, user_message_content: str, message_type: str = "text"):
    """
    Celery task that buffers and sequentially evaluates Agentic AI queries.
    Celery operates synchronously by default, so we wrap our AI Async framework inside an asyncio.run.
    """
    logger.info(f"CELERY: Iniciando tarea de IA para {phone}")
    
    try:
        # Spin up an isolated event loop for this specific task execution
        asyncio.run(execute_ai_agent(phone, user_message_content, message_type))
    except Exception as exc:
        logger.error(f"CELERY: Tarea IA fallida para {phone}: {exc}")
        
        # Optionally retry the task if it dropped due to temporary Meta timeout or Gemini outage
        # We wait 5 seconds before retrying
        raise self.retry(exc=exc, countdown=5)

    logger.info(f"CELERY: Tarea IA completada para {phone}")
