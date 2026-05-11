from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
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

from app.core.security import encrypt_value

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
    
    # Handle API Key Securely
    if "google_gemini_api_key" in update_data:
        new_key = update_data["google_gemini_api_key"]
        if new_key and new_key.startswith("********"):
            # It's a masked string, don't update it!
            del update_data["google_gemini_api_key"]
        else:
            # Encrypt the real key before saving
            update_data["google_gemini_api_key"] = encrypt_value(new_key)
            
    for field, value in update_data.items():
        setattr(config, field, value)
        
    await db.commit()
    await db.refresh(config)
    return config
