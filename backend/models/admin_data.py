"""Настройки, по которым фронтенд собирает форму."""

from __future__ import annotations

from typing import Any

from psycopg.errors import CheckViolation

from core.database import (
    delete_by,
    fetch_latest,
    fetch_one,
    fetch_page,
    insert_returning,
    update_returning,
)
from core.exceptions import InvalidData


class AdminData:
    """Услуги и диапазон бюджета для интерфейса формы.

    services — JSON-массив объектов с полями name и description.
    По этому списку фронтенд показывает, какие услуги можно выбрать.
    budget_min, budget_max и budget_step задают ползунок бюджета.
    Выбранное на ползунке значение уходит в заявку отдельной строкой.

    CREATE TABLE IF NOT EXISTS admin_data (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        services JSONB NOT NULL,
        budget_min DOUBLE PRECISION NOT NULL,
        budget_max DOUBLE PRECISION NOT NULL,
        budget_step DOUBLE PRECISION NOT NULL DEFAULT 1,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT admin_data_services_chk CHECK (
            jsonb_typeof(services) = 'array' AND jsonb_array_length(services) >= 1
        ),
        CONSTRAINT admin_data_budget_chk CHECK (
            budget_max >= budget_min AND budget_step > 0
        )
    );
    """

    table = "admin_data"
    insert_columns = (
        "services",
        "budget_min",
        "budget_max",
        "budget_step",
    )
    mutable_columns = insert_columns


class AdminDataCRUD:
    """Создание, чтение, правка и удаление админ-настроек."""

    @staticmethod
    def create(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return insert_returning(AdminData.table, AdminData.insert_columns, data)
        except CheckViolation as exc:
            raise InvalidData("Проверьте список услуг и диапазон бюджета") from exc

    @staticmethod
    def get(item_id: int) -> dict[str, Any] | None:
        return fetch_one(AdminData.table, "id", item_id)

    @staticmethod
    def latest() -> dict[str, Any] | None:
        return fetch_latest(AdminData.table)

    @staticmethod
    def page(limit: int, offset: int) -> dict[str, Any]:
        return fetch_page(AdminData.table, "id", limit, offset)

    @staticmethod
    def update(item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return update_returning(
                AdminData.table,
                "id",
                item_id,
                AdminData.mutable_columns,
                data,
            )
        except CheckViolation as exc:
            raise InvalidData("Проверьте список услуг и диапазон бюджета") from exc

    @staticmethod
    def delete(item_id: int) -> bool:
        return delete_by(AdminData.table, "id", item_id)
