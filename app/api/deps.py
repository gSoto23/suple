from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_db
from app.models import User
from app.schemas.auth import TokenData


oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.APP_ROOT_PATH}{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Wait for normal tokens

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user

async def get_current_active_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

from app.models.system import SystemConfig

async def check_subscriptions_enabled(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()
    if config and not config.enable_subscriptions:
        raise HTTPException(status_code=403, detail="El módulo de suscripciones está deshabilitado en la configuración del sistema.")
    return True

async def check_marketing_enabled(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()
    if config and not config.enable_marketing:
        raise HTTPException(status_code=403, detail="El módulo de marketing está deshabilitado en la configuración del sistema.")
    return True
