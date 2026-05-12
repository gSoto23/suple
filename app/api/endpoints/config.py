from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models.system import SystemConfig
from app.schemas.system import SystemConfig as SystemConfigSchema, SystemConfigUpdate
from app.models.users import User
from app.api import deps

router = APIRouter()

@router.get("/", response_model=SystemConfigSchema)
async def get_config(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()

    if not config:
        config = SystemConfig()
        db.add(config)
        await db.commit()
        await db.refresh(config)

    return config

@router.get("/diagnostic_ai")
async def diagnostic_ai(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Endpoint de diagnóstico para revisar exactamente qué tiene cargado Gunicorn en la memoria.
    No expone la llave completa por seguridad.
    """
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()
    
    key_in_memory = settings.GEMINI_API_KEY or ""
    
    # Prevenir que truene si la llave está vacía
    if len(key_in_memory) > 10:
        masked_key = f"{key_in_memory[:6]}...{key_in_memory[-4:]}"
    else:
        masked_key = "VACIA O MUY CORTA"

    return {
        "status": "Diagnostic Running",
        "gemini_api_key_length": len(key_in_memory),
        "gemini_api_key_masked": masked_key,
        "contains_quotes": '"' in key_in_memory or "'" in key_in_memory,
        "contains_dame": "dame" in key_in_memory.lower(),
        "db_ai_model_name": config.ai_model_name if config else "None"
    }

@router.put("/", response_model=SystemConfigSchema)
async def update_config(
    config_in: SystemConfigUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: User = Depends(deps.get_current_active_admin)
):
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()
    
    if not config:
        config = SystemConfig()
        db.add(config)
    
    update_data = config_in.model_dump(exclude_unset=True)
            
    for field, value in update_data.items():
        setattr(config, field, value)
        
    await db.commit()
    await db.refresh(config)
    return config
