import asyncio
from app.core.celery import celery_app
from app.services.ai_logic import execute_ai_agent
from app.core.logger import app_logger as logger

@celery_app.task(name="process_ai_request", bind=True, max_retries=1)
def process_ai_request_task(self, phone: str, user_message_content: str, message_type: str = "text"):
    """
    Celery task that buffers and sequentially evaluates Agentic AI queries.
    """
    logger.info(f"CELERY: Iniciando tarea de IA para {phone}")
    
    try:
        # Spin up an isolated event loop for this specific task execution
        asyncio.run(execute_ai_agent(phone, user_message_content, message_type))
    except Exception as exc:
        logger.error(f"CELERY: Tarea IA fallida definitivamente para {phone}: {exc}")
        # WE REMOVED raise self.retry() HERE! 
        # By avoiding retries, we force-kill the "Ghost Repeat / Apology Loops" 
        # if the database transaction aborts or timeout occurs.

    logger.info(f"CELERY: Tarea IA completada para {phone}")
