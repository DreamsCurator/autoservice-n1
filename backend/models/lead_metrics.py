"""Поведение посетителя на странице заявки. Связь с заявкой один к одному."""

from __future__ import annotations

from typing import Any

from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

from core.database import delete_by, fetch_one, fetch_page, insert_returning, update_returning
from core.exceptions import Conflict, InvalidData, NotFound


class LeadMetrics:
    """Метрики и техническая информация по одной заявке.

    Первичный ключ lead_id совпадает с leads.id: у заявки не больше одной строки метрик.
    Удаление заявки удаляет и метрики.
    time_on_page_seconds — сколько секунд человек провёл на странице.
    buttons_clicked — какие кнопки нажимал, JSON-массив.
    cursor_hotspots — где зависал курсор, JSON-массив.
    return_count — как часто возвращался на страницу.
    technical_info — техническая информация, которую собрал фронтенд, JSON-объект.

    CREATE TABLE IF NOT EXISTS lead_metrics (
        lead_id INTEGER PRIMARY KEY REFERENCES leads (id) ON DELETE CASCADE,
        time_on_page_seconds DOUBLE PRECISION NOT NULL DEFAULT 0,
        buttons_clicked JSONB NOT NULL DEFAULT '[]'::jsonb,
        cursor_hotspots JSONB NOT NULL DEFAULT '[]'::jsonb,
        return_count INTEGER NOT NULL DEFAULT 0,
        technical_info JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT lead_metrics_time_chk CHECK (time_on_page_seconds >= 0),
        CONSTRAINT lead_metrics_returns_chk CHECK (return_count >= 0)
    );
    """

    table = "lead_metrics"
    insert_columns = (
        "lead_id",
        "time_on_page_seconds",
        "buttons_clicked",
        "cursor_hotspots",
        "return_count",
        "technical_info",
    )
    mutable_columns = (
        "time_on_page_seconds",
        "buttons_clicked",
        "cursor_hotspots",
        "return_count",
        "technical_info",
    )


class VisitMetric:
    """Снимок поведения на странице заявки. К заявке не привязан.

    Каждую секунду страница присылает одну строку:
    сколько секунд человек уже на странице, сколько раз нажал какие кнопки
    и где в эту секунду был курсор (x,y).

    CREATE TABLE IF NOT EXISTS visit_metrics (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        application_id INTEGER NOT NULL DEFAULT 0,
        time_on_page DOUBLE PRECISION NOT NULL DEFAULT 0,
        buttons_clicked TEXT NOT NULL DEFAULT '',
        cursor_positions TEXT NOT NULL DEFAULT '',
        return_frequency INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT visit_metrics_time_chk CHECK (time_on_page >= 0),
        CONSTRAINT visit_metrics_returns_chk CHECK (return_frequency >= 0)
    );
    """

    table = "visit_metrics"
    insert_columns = (
        "application_id",
        "time_on_page",
        "buttons_clicked",
        "cursor_positions",
        "return_frequency",
    )


class LeadMetricsCRUD:
    """Создание, чтение, правка и удаление метрик заявки."""

    @staticmethod
    def create(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return insert_returning(LeadMetrics.table, LeadMetrics.insert_columns, data)
        except ForeignKeyViolation as exc:
            raise NotFound("Заявка не найдена") from exc
        except UniqueViolation as exc:
            raise Conflict("Метрики для этой заявки уже записаны") from exc
        except CheckViolation as exc:
            raise InvalidData("Некорректные метрики заявки") from exc

    @staticmethod
    def get(lead_id: int) -> dict[str, Any] | None:
        return fetch_one(LeadMetrics.table, "lead_id", lead_id)

    @staticmethod
    def page(limit: int, offset: int) -> dict[str, Any]:
        return fetch_page(LeadMetrics.table, "lead_id", limit, offset)

    @staticmethod
    def update(lead_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return update_returning(
                LeadMetrics.table,
                "lead_id",
                lead_id,
                LeadMetrics.mutable_columns,
                data,
            )
        except CheckViolation as exc:
            raise InvalidData("Некорректные метрики заявки") from exc

    @staticmethod
    def delete(lead_id: int) -> bool:
        return delete_by(LeadMetrics.table, "lead_id", lead_id)


class VisitMetricCRUD:
    """Запись и чтение ежесекундных снимков страницы заявки."""

    @staticmethod
    def create(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return insert_returning(VisitMetric.table, VisitMetric.insert_columns, data)
        except CheckViolation as exc:
            raise InvalidData("Некорректные метрики страницы") from exc

    @staticmethod
    def page(limit: int, offset: int) -> dict[str, Any]:
        return fetch_page(VisitMetric.table, "id", limit, offset)
