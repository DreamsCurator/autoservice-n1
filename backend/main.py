"""Точка входа FastAPI.

Слушает 0.0.0.0:8080 внутри контейнера, чтобы frontend из сети app
мог вызвать http://backend:8080. На хост порт не публикуется.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from core.database import create_sql_from_model, init_schema, ping, pool
from models import SCHEMA_MODELS
from routes import api_router

logger = logging.getLogger("autoservice")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    pool.open(wait=True, timeout=20)
    try:
        init_schema([create_sql_from_model(model) for model in SCHEMA_MODELS])
        yield
    finally:
        pool.close()


app = FastAPI(
    title="Autoservice API",
    version="1.0.0",
    description=(
        "Приватный API заявок. Контейнер не публикует порт на хост. "
        "Вызов доступен только из сети Docker app, адрес http://backend:8080."
    ),
    lifespan=lifespan,
)
app.include_router(api_router)


@app.get("/health", summary="Проверка процесса и базы")
def health() -> dict[str, str]:
    if not ping():
        raise HTTPException(status_code=503, detail="db_unavailable")
    return {"status": "ok"}


@app.exception_handler(psycopg.Error)
async def postgres_error(request, exc: psycopg.Error) -> JSONResponse:
    logger.error("Ошибка PostgreSQL: %s", type(exc).__name__)
    return JSONResponse(status_code=500, content={"detail": "Ошибка записи в базу"})
