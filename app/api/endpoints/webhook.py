from fastapi import APIRouter, Request, Response, BackgroundTasks, Depends
from typing import Dict, Any
import httpx
from app.core.config import settings
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logger import app_logger as logger

router = APIRouter()

@router.get("/webhook")
async def verify_webhook(request: Request):
    """
    Handle Meta's Webhook Verification Challenge.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
            return Response(content=challenge, media_type="text/plain")
        else:
            return Response(status_code=403, content="Verification failed")
    
    return Response(status_code=400, content="Missing parameters")

from app.tasks.ai_tasks import process_ai_request_task

async def process_incoming_message(payload: Dict[str, Any], db: AsyncSession):
    """
    Extract message from payload, ENSURE CUSTOMER EXISTS, and save message to DB.
    """
    try:
        logger.info(f"REAL WEBHOOK PAYLOAD: {payload}")
        entry = payload.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        contacts = value.get("contacts", [])

        if messages:
            msg = messages[0]
            logger.info(f"REAL WEBHOOK MSG: {msg}")
            
            # --- REDIS DEDUPLICATION START ---
            msg_id = msg.get("id")
            if msg_id:
                try:
                    import redis
                    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
                    # Use setnx (NX=True) for atomic race condition prevention
                    is_new = r.set(f"wamid:{msg_id}", "1", nx=True, ex=3600)
                    if not is_new:
                        logger.info(f"DUPLICATE WEBHOOK PREVENTED FOR WAMID: {msg_id}")
                        return False, None, None
                except Exception as re_err:
                    logger.error(f"Redis Deduplication Error: {re_err}")
            # --- REDIS DEDUPLICATION END ---

            phone = msg.get("from")
            msg_type = msg.get("type")
            
            # Extract Profile Name
            profile_name = "Cliente WhatsApp"
            if contacts:
                profile = contacts[0].get("profile", {})
                profile_name = profile.get("name", "Cliente WhatsApp")
            
            if msg_type == "text":
                content = msg.get("text", {}).get("body", "")
            elif msg_type == "interactive":
                # Handle interactive buttons or lists
                interactive = msg.get("interactive", {})
                int_type = interactive.get("type")
                if int_type == "button_reply":
                    content = interactive.get("button_reply", {}).get("id")
                    # Mutate payload so AI sees a normal text message
                    msg["type"] = "text"
                    msg["text"] = {"body": interactive.get("button_reply", {}).get("title", content)}
                elif int_type == "list_reply":
                    content = interactive.get("list_reply", {}).get("id")
                    # Mutate payload so AI sees a normal text message
                    msg["type"] = "text"
                    msg["text"] = {"body": interactive.get("list_reply", {}).get("title", content)}
            elif msg_type == "button":
                # Handle Quick Reply Buttons from Templates
                content = msg.get("button", {}).get("text") or msg.get("button", {}).get("payload")
                # Mutate payload so AI sees a normal text message
                if content:
                    msg["type"] = "text"
                    msg["text"] = {"body": content}
            elif msg_type in ["image", "audio", "document"]:
                # Handle Media
                media_id = msg.get(msg_type, {}).get("id")
                
                # Fetch Media from WhatsApp
                from app.core.whatsapp import whatsapp_client
                import os
                import uuid
                
                try:
                    logger.info(f"DOWNLOADING MEDIA ID: {media_id}")
                    media_url = await whatsapp_client.get_media_url(media_id)
                    media_binary = await whatsapp_client.download_media(media_url)
                    
                    # Determine extension
                    mime_type = msg.get(msg_type, {}).get("mime_type", "")
                    ext = ".bin"
                    if "image" in mime_type: ext = ".jpg" # Simplify
                    elif "audio" in mime_type: ext = ".ogg"
                    elif "pdf" in mime_type: ext = ".pdf"
                    
                    # Save to static
                    UPLOAD_DIR = "app/static/chat_uploads"
                    os.makedirs(UPLOAD_DIR, exist_ok=True)
                    
                    filename = f"{uuid.uuid4()}{ext}"
                    file_path = os.path.join(UPLOAD_DIR, filename)
                    
                    with open(file_path, "wb") as f:
                        f.write(media_binary)
                        
                    content = f"{settings.APP_ROOT_PATH}/api/v1/chat/media/{filename}"
                    logger.info(f"MEDIA SAVED: {content}")
                    
                except Exception as e:
                    logger.info(f"FAILED TO DOWNLOAD MEDIA: {e}")
                    content = f"[ERROR DOWNLOADING MEDIA {msg_type}]"
            
            should_forward_to_ai = True

            if phone and content:
                # --- GET OR CREATE CUSTOMER LOGIC START ---
                from app.models.customers import Customer
                from sqlalchemy import select
                
                # Handle optional country code dynamically
                country_code = settings.COUNTRY_PHONE_CODE
                phones_to_check = [phone]
                clean_phone = phone
                if phone.startswith(country_code) and len(phone) > len(country_code):
                    clean_phone = phone[len(country_code):]
                    phones_to_check.append(clean_phone)
                
                # Check exist
                result = await db.execute(select(Customer).where(Customer.phone.in_(phones_to_check)))
                customer = result.scalars().first()
                
                if not customer:
                    logger.info(f"CREATING NEW CUSTOMER: {profile_name} - {clean_phone}")
                    new_customer = Customer(
                        full_name=profile_name,
                        phone=clean_phone,
                        email=None,
                        is_active=True
                    )
                    db.add(new_customer)
                    await db.commit()
                    await db.refresh(new_customer)
                    customer = new_customer
                    logger.info(f"CUSTOMER CREATED ID: {new_customer.id}")
                else:
                    logger.info(f"CUSTOMER EXISTS: {customer.full_name}")
                # --- GET OR CREATE CUSTOMER LOGIC END ---

                if not customer.ai_active:
                    logger.info(f"AI IS OFF FOR CUSTOMER {clean_phone}. Message will be saved but not forwarded to Agent.")
                    should_forward_to_ai = False

                from app.models.orders import Order
                from app.models.chat import ChatMessage
                from app.core.whatsapp import whatsapp_client
                import re

                # --- SAVE INCOMING MESSAGE EARLY FOR CHRONOLOGY ---
                logger.info(f"SAVING MSG EARLY: {phone} - {content}")
                chat_msg = ChatMessage(
                    customer_phone=phone,
                    sender="user",
                    message_type=msg_type,
                    content=content
                )
                db.add(chat_msg)
                await db.commit()
                # --------------------------------------------------

                # --- RECEIPT INTERCEPTION LOGIC START ---
                
                # Bypassing the AI completely if the admin took control
                if not customer.ai_active:
                    logger.info("AI is OFF. Bypassing State Machine Receipt Interception.")
                    return should_forward_to_ai, phone, content

                # Quick helper to save internal AI messages so UI can see the history
                async def _save_ai_msg(text: str):
                    ai_msg = ChatMessage(
                        customer_phone=phone,
                        sender="ai",
                        message_type="text",
                        content=text
                    )
                    db.add(ai_msg)
                    await db.commit()

                # 1. State Machine Interceptions
                # Find orders in waiting states
                pending_orders_result = await db.execute(select(Order).where(
                    Order.customer_id == customer.id,
                    Order.status.in_(["created", "pending_payment", "awaiting_receipt_confirmation", "awaiting_receipt_confirmation_multiple", "awaiting_receipt_selection"])
                ))
                pending_orders = pending_orders_result.scalars().all()

                if msg_type in ["image", "document"]:
                    # Intercept image
                    normal_pendings = [o for o in pending_orders if o.status in ["created", "pending_payment"] and not o.payment_proof]
                    if len(normal_pendings) == 1:
                        # Case A: 1 pending order
                        order = normal_pendings[0]
                        order.status = "awaiting_receipt_confirmation"
                        order.pending_receipt_url = content
                        await db.commit()
                        
                        
                        msg_text = f"Hemos recibido una imagen. ¿Es este el comprobante de pago para tu orden #{order.id} por {settings.CURRENCY_SYMBOL}{order.total_amount:,.2f}?"
                        await whatsapp_client.send_interactive_buttons(
                            to=phone,
                            body_text=msg_text,
                            buttons=[
                                {"id": "receipt_confirm_yes", "title": "SÍ"},
                                {"id": "receipt_confirm_no", "title": "NO"}
                            ]
                        )
                        await _save_ai_msg(msg_text)
                        await db.commit()
                        should_forward_to_ai = False
                        
                    elif len(normal_pendings) > 1:
                        # Case B Step 1: Multiple pending orders
                        for o in normal_pendings:
                            o.status = "awaiting_receipt_confirmation_multiple"
                            o.pending_receipt_url = content
                        await db.commit()
                        
                        
                        msg_text = "Hemos recibido una imagen. ¿Es un comprobante de pago?"
                        await whatsapp_client.send_interactive_buttons(
                            to=phone,
                            body_text=msg_text,
                            buttons=[
                                {"id": "receipt_multiple_yes", "title": "SÍ"},
                                {"id": "receipt_multiple_no", "title": "NO"}
                            ]
                        )
                        await _save_ai_msg(msg_text)
                        await db.commit()
                        should_forward_to_ai = False
                    else:
                        # No pending orders
                        msg_text = "Aún no estoy entrenada para analizar imágenes. Por favor envíame texto."
                        await whatsapp_client.send_message(phone, msg_text)
                        await _save_ai_msg(msg_text)
                        await db.commit()
                        should_forward_to_ai = False

                elif msg_type == "interactive" or msg_type == "text":
                    # Check for active flows
                    awaiting_single = [o for o in pending_orders if o.status == "awaiting_receipt_confirmation"]
                    awaiting_multiple_conf = [o for o in pending_orders if o.status == "awaiting_receipt_confirmation_multiple"]
                    awaiting_selection = [o for o in pending_orders if o.status == "awaiting_receipt_selection"]

                    user_text = content.strip().lower()

                    # Handle Single Order Confirmation
                    if awaiting_single and (msg_type == "interactive" or user_text in ["si", "sí", "yes", "no"]):
                        order = awaiting_single[0]
                        is_yes = content == "receipt_confirm_yes" or user_text in ["si", "sí", "yes"]
                        
                        if is_yes:
                            order.status = "pending_payment"
                            order.payment_proof = order.pending_receipt_url
                            order.pending_receipt_url = None
                            msg_text = f"¡Gracias! Hemos recibido tu comprobante para la orden #{order.id} y está en revisión para confirmación final."
                            await whatsapp_client.send_message(phone, msg_text)
                            await _save_ai_msg(msg_text)
                            await db.commit()
                        else:
                            order.status = "pending_payment"
                            order.pending_receipt_url = None
                            msg_text = "Entendido. Por favor envíanos un texto si necesitas ayuda adicional."
                            await whatsapp_client.send_message(phone, msg_text)
                            await _save_ai_msg(msg_text)
                            await db.commit()
                            should_forward_to_ai = False

                    # Handle Multiple Orders Confirmation (Is it a receipt?)
                    elif awaiting_multiple_conf and (msg_type == "interactive" or user_text in ["si", "sí", "yes", "no"]):
                        is_yes = content == "receipt_multiple_yes" or user_text in ["si", "sí", "yes"]
                        
                        if is_yes:
                            for o in awaiting_multiple_conf:
                                o.status = "awaiting_receipt_selection"
                            await db.commit()
                            
                            if len(awaiting_multiple_conf) <= 3:
                                # Use Buttons
                                buttons = [{"id": f"order_receipt_{o.id}", "title": f"Orden #{o.id}"} for o in awaiting_multiple_conf]
                                msg_text = "Vemos que tienes varias órdenes pendientes. Por favor selecciona a cuál pertenece este comprobante:"
                                await whatsapp_client.send_interactive_buttons(
                                    to=phone,
                                    body_text=msg_text,
                                    buttons=buttons
                                )
                                await _save_ai_msg(msg_text)
                            else:
                                # Use List Menu
                                rows = [{"id": f"order_receipt_{o.id}", "title": f"Orden #{o.id}", "description": f"{settings.CURRENCY_SYMBOL}{o.total_amount:,.2f}"} for o in awaiting_multiple_conf]
                                msg_text = "Vemos que tienes varias órdenes pendientes. Por favor selecciona a cuál pertenece este comprobante:"
                                await whatsapp_client.send_interactive_list(
                                    to=phone,
                                    body_text=msg_text,
                                    button_text="Ver Órdenes",
                                    sections=[{"title": "Órdenes Pendientes", "rows": rows[:10]}]
                                )
                                await _save_ai_msg(msg_text)
                            await db.commit()
                        else:
                            for o in awaiting_multiple_conf:
                                o.status = "pending_payment"
                                o.pending_receipt_url = None
                            msg_text = "Entendido. Por favor envíanos un texto si necesitas ayuda adicional."
                            await whatsapp_client.send_message(phone, msg_text)
                            await _save_ai_msg(msg_text)
                            await db.commit()
                            should_forward_to_ai = False

                    # Handle Multiple Orders Selection
                    elif awaiting_selection:
                        selected_id = None
                        if msg_type == "interactive" and content.startswith("order_receipt_"):
                            selected_id = int(content.split("_")[-1])
                        elif msg_type == "text":
                            # Try to extract numbers
                            match = re.search(r'\d+', content)
                            if match:
                                selected_id = int(match.group(0))

                        if selected_id:
                            target_order = next((o for o in awaiting_selection if o.id == selected_id), None)
                            if target_order:
                                target_order.status = "pending_payment"
                                target_order.payment_proof = target_order.pending_receipt_url
                                target_order.pending_receipt_url = None
                                
                                # Revert the others
                                others = [o for o in awaiting_selection if o.id != selected_id]
                                for o in others:
                                    o.status = "pending_payment"
                                    o.pending_receipt_url = None
                                
                                msg_text = f"¡Gracias! Hemos recibido tu comprobante para la orden #{target_order.id} y está en revisión para confirmación final."
                                await whatsapp_client.send_message(phone, msg_text)
                                await _save_ai_msg(msg_text)
                                await db.commit()
                            else:
                                msg_text = "No encontré esa orden. Por favor selecciona una del menú."
                                await whatsapp_client.send_message(phone, msg_text)
                                await _save_ai_msg(msg_text)
                                await db.commit()
                            should_forward_to_ai = False

                        else:
                            msg_text = "Por favor selecciona una orden de la lista o envía el número de la orden."
                            await whatsapp_client.send_message(phone, msg_text)
                            await _save_ai_msg(msg_text)
                            await db.commit()
                            should_forward_to_ai = False

                # --- RECEIPT INTERCEPTION LOGIC END ---

                return should_forward_to_ai, phone, content
                
    except Exception as e:
        await db.rollback()
        logger.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return True, None, None # Default to forward on error to handle gracefully via AI
    
    return True, None, None

@router.post("/webhook")
async def receive_webhook(
    request: Request, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Receive Webhook from Meta.
    """
    try:
        payload = await request.json()
        
        # 1. Log to DB (User Message)
        # We await this because we want to ensure it's saved? 
        # Or background it? Let's background the processing to return 200 OK fast to Meta.
        # However, passing DB session to background task can be tricky with async dependency injection closing session.
        # For simplicity and robustness in this scale, let's await the DB save (fast enough) and background the AI queue forward.
        
        # Actually, let's just inspect payload quickly.
        # Meta expects 200 OK fast.
        
        # IMPORTANT: 'process_incoming_message' needs a session. 
        # Fastapi dependency 'db' is scoped to request. 
        # So we should await it here.
        should_forward, phone, content = await process_incoming_message(payload, db)
        
        # 2. Forward to Celery AI Queue if not handled internally
        if should_forward and phone and content:
            process_ai_request_task.delay(phone, content, "text")

        
        return Response(status_code=200, content="EVENT_RECEIVED")
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        # Always return 200 to Meta to prevent retries loop if it's our bug
        return Response(status_code=200, content="EVENT_RECEIVED_ERROR")
