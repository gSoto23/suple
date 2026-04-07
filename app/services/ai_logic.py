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

# --- ATOMIC NATIVE TOOLS ---

async def get_store_policy(**kwargs) -> str:
    """Devuelve las políticas de la tienda, métodos de pago, envíos, y garantías."""
    return (
        "Políticas de Suplementos CR:\n"
        "- Envíos: 24h hábiles dentro de GAM. A todo el país por Correos de Costa Rica.\n"
        "- Pagos: SINPE Móvil, transferencia bancaria, o tarjeta contra entrega en GAM.\n"
        "- Garantía: No se aceptan devoluciones de suplementos abiertos por medidas de salud."
    )

def _safe_float(val):
    try:
        if val is None or val == "":
            return 0.0
        return float(val)
    except (ValueError, TypeError):
        return 0.0

async def search_catalog_by_name(query: str, **kwargs) -> str:
    """Busca productos en el catálogo filtrando explícitamente por nombre o SKU."""
    import unicodedata
    query = str(query)
    query = "".join(c for c in unicodedata.normalize('NFD', query) if unicodedata.category(c) != 'Mn')
    
    async with AsyncSessionLocal() as db:
        stmt = select(Product).where(
            Product.name.ilike(f"%{query}%") | Product.sku.ilike(f"%{query}%")
        ).where(Product.is_active == True)
        result = await db.execute(stmt)
        products = result.scalars().all()
        if not products:
            return f"SUCCESS: 0 productos encontrados con el nombre '{query}'. Pide al cliente que intente otra palabra."
        
        return json.dumps([{"sku": p.sku, "name": p.name, "price_crc": _safe_float(p.price), "stock": p.stock, "category": p.category} for p in products])

async def search_catalog_by_category(category: str, **kwargs) -> str:
    """Busca productos filtrando exclusivamente por familia/categoría (ej. proteína, creatina, pre-entreno)."""
    import unicodedata
    category = str(category)
    category = "".join(c for c in unicodedata.normalize('NFD', category) if unicodedata.category(c) != 'Mn')
    
    async with AsyncSessionLocal() as db:
        stmt = select(Product).where(Product.category.ilike(f"%{category}%")).where(Product.is_active == True)
        result = await db.execute(stmt)
        products = result.scalars().all()
        if not products:
            return f"SUCCESS: 0 productos encontrados en la categoría '{category}'."
        
        return json.dumps([{"sku": p.sku, "name": p.name, "price_crc": _safe_float(p.price), "stock": p.stock, "category": p.category} for p in products])

async def get_customer_profile(phone: str, **kwargs) -> str:
    """Retorna toda la metadata medica y transaccional del cliente usando su numero."""
    clean_phone = phone[-8:]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Customer).where(Customer.phone.endswith(clean_phone)))
        customer = result.scalars().first()
        if not customer:
            return "Customer Profile no encontrado. Debes pedirle los datos."
            
        return json.dumps({
            "id": customer.id,
            "full_name": customer.full_name,
            "email": customer.email,
            "objective": getattr(customer, 'objective', ''),
            "medical_notes": getattr(customer, 'medical_notes', ''),
            "lifestyle_notes": getattr(customer, 'lifestyle_notes', '')
        })

async def update_customer_profile(phone: str, field: str, value: str, **kwargs) -> str:
    """Actualiza campos especificos del perfil medico o transaccional del cliente."""
    clean_phone = phone[-8:]
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Customer).where(Customer.phone.endswith(clean_phone)))
        customer = result.scalars().first()
        if not customer:
            return "Customer not found. No se puede actualizar."
        
        if hasattr(customer, field):
            setattr(customer, field, value)
            await db.commit()
            return f"SUCCESS: Campo '{field}' actualizado a '{value}'."
        return f"ERROR: Campo inválido '{field}'. Usa full_name, email, objective, medical_notes, lifestyle_notes."

async def get_customer_orders(phone: str, limit: int = 5, **kwargs) -> str:
    """Lee el historial de ordenes previas de compras del cliente."""
    clean_phone = phone[-8:]
    async with AsyncSessionLocal() as db:
        result_c = await db.execute(select(Customer).where(Customer.phone.endswith(clean_phone)))
        customer = result_c.scalars().first()
        if not customer:
            return "Customer not found."
            
        result_o = await db.execute(select(Order).where(Order.customer_id == customer.id).order_by(Order.created_at.desc()).limit(limit))
        orders = result_o.scalars().all()
        if not orders:
            return "El cliente no tiene órdenes previas registradas."
            
        return json.dumps([{"order_id": o.id, "status": o.status, "total_crc": _safe_float(o.total_amount), "date": str(o.created_at)} for o in orders])

async def create_order_draft(phone: str, product_sku: str, quantity: int, **kwargs) -> str:
    """Función de Smart Cart: Crea una orden borrador o añade a un carrito pendiente abierto."""
    clean_phone = phone[-8:]
    try:
        quantity = int(float(quantity))
    except:
        quantity = 1
        
    async with AsyncSessionLocal() as db:
        result_c = await db.execute(select(Customer).where(Customer.phone.endswith(clean_phone)))
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
            return f"El producto '{product_sku}' no existe en la BD."
            
        if product.stock < quantity:
             return f"No hay suficiente stock. Stock actual: {product.stock}"
             
        # Smart Cart Logic: check for open created order
        result_cart = await db.execute(select(Order).where(Order.customer_id == customer.id).where(Order.status == 'created'))
        order = result_cart.scalars().first()
        
        add_total = _safe_float(product.price) * quantity
        
        if not order:
            # Create new cart
            order = Order(
                customer_id=customer.id,
                total_amount=add_total,
                status="created"
            )
            db.add(order)
            await db.commit()
            await db.refresh(order)
        else:
            # Add to existing cart
            order.total_amount = float(order.total_amount) + add_total
            await db.commit()
            await db.refresh(order)
            
        # Insert Item
        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price_at_moment=product.price,
            subtotal=add_total
        )
        db.add(item)
        
        # Deduce stock
        product.stock = max(0, product.stock - quantity)
        await db.commit()
        
        return f"SUCCESS: Carrito Actualizado. Agregaste {quantity}x {product.name}. Gran Total de la orden #{order.id}: {order.total_amount} CRC."

async def remove_item_from_cart(phone: str, product_sku: str, **kwargs) -> str:
    """Saca un producto del carrito pendiente y devuelve el stock al inventario."""
    clean_phone = phone[-8:]
    async with AsyncSessionLocal() as db:
        result_c = await db.execute(select(Customer).where(Customer.phone.endswith(clean_phone)))
        customer = result_c.scalars().first()
        if not customer:
            return "Customer not found."
            
        result_cart = await db.execute(select(Order).where(Order.customer_id == customer.id).where(Order.status == 'created'))
        order = result_cart.scalars().first()
        if not order:
            return "No hay ningún carrito u orden pendiente abierta para este cliente."
            
        result_p = await db.execute(
            select(Product).where(
                (Product.sku == product_sku) | (Product.name.ilike(f"%{product_sku}%"))
            )
        )
        product = result_p.scalars().first()
        if not product:
            return "Producto invalido."
            
        result_items = await db.execute(select(OrderItem).where(OrderItem.order_id == order.id).where(OrderItem.product_id == product.id))
        items = result_items.scalars().all()
        if not items:
            return "El cliente no tiene ese producto en su carrito."
            
        # Take the first matched item and destroy it
        item_to_remove = items[0]
        qty_restored = item_to_remove.quantity
        price_deduced = _safe_float(item_to_remove.unit_price) * qty_restored
        
        await db.delete(item_to_remove)
        
        # Restore stock & total
        product.stock += qty_restored
        order.total_amount = max(0, float(order.total_amount) - price_deduced)
        
        await db.commit()
        
        return f"SUCCESS: Producto {product.name} removido del carrito. Nuevo Total de Orden #{order.id} es: {order.total_amount} CRC."

# Tool Mapping dictionary
AVAILABLE_TOOLS = {
    "get_store_policy": get_store_policy,
    "search_catalog_by_name": search_catalog_by_name,
    "search_catalog_by_category": search_catalog_by_category,
    "get_customer_profile": get_customer_profile,
    "update_customer_profile": update_customer_profile,
    "get_customer_orders": get_customer_orders,
    "create_order_draft": create_order_draft,
    "remove_item_from_cart": remove_item_from_cart
}

# Define Tool Schemas for Gemini
gemini_tools = [
     types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="get_store_policy",
            description="Lee las politicas de la tienda, metodos de pago, y politicas de envio y devoluciones.",
            parameters=types.Schema(type="OBJECT", properties={})
        ),
        types.FunctionDeclaration(
            name="search_catalog_by_name",
            description="Busca productos en el catálogo usando el nombre literal o SKU. Ideal cuando el cliente pide una marca o nombre exacto.",
            parameters=types.Schema(type="OBJECT", properties={
                "query": types.Schema(type="STRING", description="Filtro exacto o parte del nombre.")
            })
        ),
        types.FunctionDeclaration(
            name="search_catalog_by_category",
            description="Busca productos usando una familia o categoria general. Ej: proteina, creatina, pre-entreno.",
            parameters=types.Schema(type="OBJECT", properties={
                "category": types.Schema(type="STRING", description="Palabra categoria (creatina, proteina, aminoacidos).")
            })
        ),
        types.FunctionDeclaration(
            name="get_customer_profile",
            description="Revisa el area personal y notas medicas del cliente para darle contexto a la asesoria.",
            parameters=types.Schema(type="OBJECT", properties={})
        ),
        types.FunctionDeclaration(
            name="update_customer_profile",
            description="Actualiza datos transaccionales o notas fisicas/objetivos del cliente en base a lo que platica.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "field": types.Schema(type="STRING", description="Usa: full_name, medical_notes, lifestyle_notes u objective"),
                    "value": types.Schema(type="STRING", description="Dato o nota nueva.")
                },
                required=["field", "value"]
            )
        ),
        types.FunctionDeclaration(
            name="get_customer_orders",
            description="Consulta compras anteriores y status de facturacion del cliente.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "limit": types.Schema(type="INTEGER", description="Cuantas ordenes retornar (max 5)")
                }
            )
        ),
        types.FunctionDeclaration(
            name="create_order_draft",
            description="SMART CART: Mete un producto al carrito pendiente del cliente. REGLA: *SIEMPRE DEBES pedirle al cliente que te confirme la cantidad exacta de bultos y el nombre del producto ANTES de invocar esta herramienta. Nunca la uses asumiendo datos sin preguntar.*",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "product_sku": types.Schema(type="STRING", description="El SKU o nombre exacto del producto."),
                    "quantity": types.Schema(type="INTEGER", description="Cantidad numerica a meter al carrito.")
                },
                required=["product_sku", "quantity"]
            )
        ),
        types.FunctionDeclaration(
            name="remove_item_from_cart",
            description="SMART CART: Saca un producto especifico del carrito de compras si el cliente cambia de opinion.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "product_sku": types.Schema(type="STRING", description="El SKU o nombre exacto del producto a quitar.")
                },
                required=["product_sku"]
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
                        # Inject phone universally. Atomic Tools without phone arg will swallow it via **kwargs
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
