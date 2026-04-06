from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.system import SystemConfig

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals['settings'] = settings

async def get_system_config(db: AsyncSession):
    result = await db.execute(select(SystemConfig).limit(1))
    config = result.scalars().first()
    if not config:
        config = SystemConfig()
    return config

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("dashboard.html", {"request": request, "title": "Dashboard", "system_config": config})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("login.html", {"request": request, "title": "Login", "system_config": config})

@router.get("/inventory", response_class=HTMLResponse)
async def inventory_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("inventory.html", {"request": request, "title": "Inventario", "system_config": config})

@router.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("customers.html", {"request": request, "title": "Clientes", "system_config": config})

@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("orders.html", {"request": request, "title": "Órdenes", "system_config": config})

@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("users.html", {"request": request, "title": "Usuarios", "system_config": config})

@router.get("/service", response_class=HTMLResponse)
async def service_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("service.html", {"request": request, "title": "Servicio al Cliente", "system_config": config})

@router.get("/marketing", response_class=HTMLResponse)
async def marketing_page(request: Request, db: AsyncSession = Depends(get_db)):
    config = await get_system_config(db)
    return templates.TemplateResponse("marketing.html", {"request": request, "title": "Marketing", "system_config": config})
