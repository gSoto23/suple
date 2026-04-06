from fastapi import APIRouter
from app.api.endpoints import auth, users, products, orders, customers, chat, webhook, subscriptions, debug, marketing, config

api_router = APIRouter()
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(webhook.router, tags=["webhook"])
from app.api import deps
from fastapi import Depends

api_router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"], dependencies=[Depends(deps.check_subscriptions_enabled)])
api_router.include_router(marketing.router, prefix="/marketing", tags=["marketing"], dependencies=[Depends(deps.check_marketing_enabled)])
