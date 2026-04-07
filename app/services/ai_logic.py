import json
import time
import traceback
from typing import Optional, List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.system import SystemConfig
from app.models.chat import ChatMessage, AILog
from app.models.customers import Customer
from app.models.products import Product
from app.models.orders import Order, OrderItem
from app.core.whatsapp import whatsapp_client
from app.core.logger import app_logger as logger

# Import the new GenAI SDK
from google import genai
from google.genai import types

async def _get_global_config(db: AsyncSession) -> SystemConfig:
    result = await db.execute(select(SystemConfig).limit(1))
    return result.scalars().first()

# --- NATIVE TOOLS ---
async def get_inventory(query: str = "", **kwargs) -> str:
    """Read the current store products inventory. Includes name, details, price, SKU, and stock count."""
    import unicodedata
    if query:
        query = str(query)
        # Strip accents forcefully so PostgreSQL doesn't fail basic wildcard matching
        query = "".join(c for c in unicodedata.normalize('NFD', query) if unicodedata.category(c) != 'Mn')
    async with AsyncSessionLocal() as db:
        stmt = select(Product)
        if query:
            stmt = stmt.where(
                Product.name.ilike(f"%{query}%") | 
                Product.sku.ilike(f"%{query}%") |
                Product.category.ilike(f"%{query}%")
            )
        result = await db.execute(stmt)
        products = result.scalars().all()
        if not products:
            return "SUCCESS: Query executed perfectly. Result: 0 products found with that specific word. Do NOT say there was an error. Ask the user to be more specific or try searching with English terms like 'whey', 'mass', 'isolate'."
        
        def safe_float(val):
            try:
                if val is None or val == "":
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0
                
        return json.dumps([{"sku": p.sku, "name": p.name, "price_crc": safe_float(p.price), "stock": p.stock, "category": p.category} for p in products])

async def update_customer_info(phone: str, field: str, value: str, **kwargs) -> str:
    """Updates a text field in the customer's profile. Fields allowed: full_name, email, medical_notes, lifestyle_notes, objective."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Customer).where(Customer.phone == phone))
        customer = result.scalars().first()
        if not customer:
            return "Customer not found by phone."
        
        if hasattr(customer, field):
            setattr(customer, field, value)
            await db.commit()
            return f"Customer {field} updated successfully."
        return f"Invalid field: {field}"

async def create_order(phone: str, product_sku: str, quantity: int, **kwargs) -> str:
    """Creates a new sales order for the customer given the product SKU and quantity."""
    try:
        quantity = int(float(quantity))
    except:
        quantity = 1
    
    async with AsyncSessionLocal() as db:
        result_c = await db.execute(select(Customer).where(Customer.phone == phone))
        customer = result_c.scalars().first()
        if not customer:
            return "Customer not found."
            
        result_p = await db.execute(
            select(Product).where(
                (Product.sku == product_sku) | (Product.name.ilike(f"%{product_sku}%"))
            )
        )
        product = result_p.scalars().first()
        if not product:
            return f"Product with SKU or Name '{product_sku}' not found."
            
        # Create order
        total = product.price * quantity
        order = Order(
            customer_id=customer.id,
            total_amount=total,
            status="created",
            shipping_method="delivery" # default
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        
        # Add item
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price
        )
        db.add(item)
        
        # Decrease stock
        product.stock = max(0, product.stock - quantity)
        await db.commit()
        
        return f"Order #{order.id} created successfully for {quantity}x {product.name}. Total: {total} CRC."

# Tool Mapping dictionary
AVAILABLE_TOOLS = {
    "get_inventory": get_inventory,
    "update_customer_info": update_customer_info,
    "create_order": create_order
}

# Define Tool Schemas for Gemini
gemini_tools = [
     types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_inventory",
            description="Lee el inventario de la tienda para saber qué productos, precios (₡) y cuántas unidades tenemos en stock.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "query": types.Schema(type="STRING", description="Busca el nombre o categoría. PROHIBIDO USAR TILDES o Plurales (ej. escribe 'proteina', no 'proteína'). Déjalo vacio para ver todos.")
                }
            )
        ),
        types.FunctionDeclaration(
            name="update_customer_info",
            description="Actualiza la información vital del cliente si en la conversacion te cuenta sus medidas o nombre real. Manten esto actualizado para ayudar mejor.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "field": types.Schema(type="STRING", description="Campo a reemplazar. Usa estrictamente: full_name o medical_notes o lifestyle_notes u objective"),
                    "value": types.Schema(type="STRING", description="El valor actualizado del campo.")
                },
                required=["field", "value"]
            )
        ),
        types.FunctionDeclaration(
            name="create_order",
            description="Crea un borrador oficial de una orden de pedido para el cliente cuando ya confirma su interés de compra en algo en especifico.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "product_sku": types.Schema(type="STRING", description="El identificador unico (SKU) O el nombre exacto del producto."),
                    "quantity": types.Schema(type="INTEGER", description="Cantidad de bultos del producto.")
                },
                required=["product_sku", "quantity"]
            )
        )
    ])
]


async def execute_ai_agent(phone: str, user_message_content: str, message_type: str = "text"):
    """
    Main Loop for the AI Logic. Intercepts webhook payload, thinks, runs tools, and replies.
    """
    start_time = time.time()
    
    async with AsyncSessionLocal() as db:
        config = await _get_global_config(db)
        if not config or not config.google_gemini_api_key:
            logger.error("No Gemini API Key defined in DB.")
            return

        client = genai.Client(api_key=config.google_gemini_api_key)
        model_name = config.ai_model_name or "gemini-1.5-flash"
        if model_name.startswith("models/"):
            model_name = model_name.replace("models/", "")
        
        # Assemble history for context limit
        result_history = await db.execute(select(ChatMessage).where(ChatMessage.customer_phone == phone).order_by(ChatMessage.id.desc()).limit(15))
        history_msgs = list(reversed(result_history.scalars().all()))
        
        gemini_history = []
        for msg in history_msgs:
            if not msg.content: continue
            
            # The last message is usually the trigger message. We already have it in history at this point because webhook.py saves it.
            # But the prompt requires mapping to Gemini Role spec ("user" or "model")
            role = "user" if msg.sender in ["user", "admin"] else "model"
            content = msg.content
            if msg.message_type != "text":
                content = f"[{msg.message_type.upper()} RECEIVED]: {content}"
                
            gemini_history.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
            
        # Gather Guard Rails Context (Time, Customer Info)
        import datetime
        cr_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=6)).strftime("%Y-%m-%d %H:%M:%S")
        
        cust_res = await db.execute(select(Customer).where(Customer.phone == phone))
        cust = cust_res.scalars().first()
        customer_data = {}
        if cust:
            customer_data = {
                "full_name": cust.full_name,
                "email": cust.email,
                "objective": getattr(cust, 'objective', ''),
                "medical_notes": getattr(cust, 'medical_notes', ''),
                "lifestyle_notes": getattr(cust, 'lifestyle_notes', '')
            }
            
        # Compile System Prompts
        sys_prompt = config.ai_system_prompt or "Eres el asistente de ventas estrella. Siempre hablas con profesionalismo y carisma."
        sys_prompt += "\n\n--- GUARDS Y CONTEXTO AUTOMÁTICO ---\n"
        sys_prompt += f"HORA ACTUAL COSTA RICA (America/Costa_Rica UTC-6): {cr_time}\n"
        sys_prompt += f"TELÉFONO DEL CLIENTE: {phone}\n"
        sys_prompt += f"DATOS DEL CLIENTE: {json.dumps(customer_data, ensure_ascii=False)}\n"
        
        chat = client.aio.chats.create(
            model=model_name,
            config=types.GenerateContentConfig(
                system_instruction=sys_prompt,
                temperature=0.7,
                tools=gemini_tools
            ),
            history=gemini_history[:-1] # We omit the very last one to send it explicitly below
        )
        
        # Initiate iterative Request
        MAX_ITERATIONS = 5
        iters = 0
        current_request_msg = user_message_content
        
        full_raw_log = []
        total_prompt_tokens = 0
        total_completion_tokens = 0
        
        final_answer = None

        try:
            while iters < MAX_ITERATIONS:
                iters += 1
                response = await chat.send_message(current_request_msg)
                
                if response.usage_metadata:
                    total_prompt_tokens += response.usage_metadata.prompt_token_count
                    total_completion_tokens += response.usage_metadata.candidates_token_count

                # Extract Tool Calls Safely
                function_calls = []
                for part in response.parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                
                # Safe Text Extraction
                try:
                    out_text = response.text if response.text else "[Sin texto]"
                except Exception:
                    out_text = "[Herramienta Invocada]"

                full_raw_log.append({
                    "iteration": iters,
                    "input": current_request_msg if isinstance(current_request_msg, str) else "[Devolucion de Tool]",
                    "output_text": out_text
                })

                if not function_calls:
                    # Model provided text response, loop finishes
                    final_answer = out_text
                    break
                
                # Execute mapped functions
                tool_responses = []
                for fc in function_calls:
                    f_name = fc.name
                    
                    # Force serialize f_args
                    f_args_dict = {}
                    if fc.args:
                        # Convert protobuf maps / Gemini SDK wrappers strictly to dict primitives
                        for k, v in fc.args.items():
                            f_args_dict[k] = str(v) if not isinstance(v, (int, float, str, bool)) else v
                    
                    full_raw_log[-1]["function_invoked"] = f_name
                    full_raw_log[-1]["function_args"] = f_args_dict
                    
                    # Override phone args safely if needed by the Python functions mapping
                    if "phone" in f_args_dict:
                        # Our definition doesn't declare phone intentionally, we force it internal
                        pass
                    
                    if f_name in AVAILABLE_TOOLS:
                        logger.info(f"AI INVOCANDO HERRAMIENTA: {f_name} {f_args_dict}")
                        if f_name in ["update_customer_info", "create_order"]:
                            # Inject phone to positional/kwargs automatically
                            f_args_dict["phone"] = phone
                        
                        try:
                            res_val = await AVAILABLE_TOOLS[f_name](**f_args_dict)
                        except Exception as e:
                            logger.error(f"Errored executing {f_name}: {e}")
                            res_val = f"Error ejecutando herramienta interna: {e}"
                    else:
                        res_val = "Error: Herramienta no existe."
                        
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=f_name,
                            response={"result": res_val}
                        )
                    )
                
                # Push the function results back via send_message passing parts
                current_request_msg = tool_responses
                
        except Exception as e:
            logger.error(f"AI AGENT LOOP CRASHED: {e}")
            traceback.print_exc()
            final_answer = f"[System Error]: Ocurrió un error consultando la Inteligencia artificial: {e}"

        duration_ms = int((time.time() - start_time) * 1000)
        
        # We will commit BOTH ChatMessage and AILog in a single atomic transaction 
        # to prevent SQLite 'Database is Locked' concurrency errors between consecutive commits
        
        if final_answer:
            msg_to_save = ChatMessage(
                customer_phone=phone,
                sender="ai",
                message_type="text",
                content=final_answer
            )
            db.add(msg_to_save)
            
            # Send message asynchronously before DB commit locking (non-blocking)
            try:
                await whatsapp_client.send_message(to=phone, content=final_answer)
            except Exception as e:
                logger.error(f"Failed to Send WhatsApp Reponse from AI: {e}")
                
        # Prepare Telemetry Log
        try:
            safe_payload = json.loads(json.dumps(full_raw_log, default=str))
            
            ai_log = AILog(
                customer_phone=phone,
                endpoint=model_name,
                request_payload={"history_count": len(gemini_history), "event_message": str(user_message_content)[:500]},
                response_payload={"iterations_history": safe_payload, "final_answer": final_answer},
                prompt_tokens=total_prompt_tokens,
                completion_tokens=total_completion_tokens,
                total_tokens=total_prompt_tokens + total_completion_tokens,
                duration_ms=duration_ms
            )
            db.add(ai_log)
        except Exception as prep_err:
            logger.error(f"Failed preparing AILog object: {prep_err}")
            
        # Unified Atomic Commit
        try:
            await db.commit()
        except Exception as db_err:
            logger.error(f"CRITICAL DB COMMIT ERROR (AILog / ChatMessage): {db_err}")
            # If commit fails, we just log it and move on to kill the process loop smoothly
            pass
