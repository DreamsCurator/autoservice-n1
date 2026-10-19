"""Общий роутер API. К нему подключены роуты всех моделей."""

from fastapi import APIRouter

from routes.admin_data import router as admin_data_router
from routes.auth import router as auth_router
from routes.lead import router as lead_router
from routes.lead_metrics import router as lead_metrics_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(lead_router)
api_router.include_router(lead_metrics_router)
api_router.include_router(admin_data_router)
