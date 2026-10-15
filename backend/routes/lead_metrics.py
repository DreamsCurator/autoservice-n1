"""Роут метрик поведения. Операции идут в LeadMetricsCRUD."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import ConfigDict, Field, field_validator

from core.database import transaction
from models.lead_metrics import LeadMetricsCRUD
from routes.common import ApiModel, check_events, db_errors, limit_json

router = APIRouter(prefix="/lead-metrics", tags=["Метрики"])


class LeadMetricsPayload(ApiModel):
    time_on_page_seconds: float = Field(
        default=0,
        ge=0,
        le=60 * 60 * 24 * 30,
        description="Сколько секунд человек провёл на странице",
    )
    buttons_clicked: list[Any] = Field(
        default_factory=list,
        description="Какие кнопки нажимал",
    )
    cursor_hotspots: list[Any] = Field(
        default_factory=list,
        description="Где зависал курсор",
    )
    return_count: int = Field(
        default=0,
        ge=0,
        le=1_000_000,
        description="Сколько раз возвращался на страницу",
    )
    technical_info: dict[str, Any] = Field(
        default_factory=dict,
        description="Техническая информация, собранная фронтендом",
    )

    @field_validator("buttons_clicked")
    @classmethod
    def validate_buttons(cls, value: list[Any]) -> list[Any]:
        return check_events(value, "кнопки")

    @field_validator("cursor_hotspots")
    @classmethod
    def validate_hotspots(cls, value: list[Any]) -> list[Any]:
        return check_events(value, "курсор")

    @field_validator("technical_info")
    @classmethod
    def validate_technical(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return limit_json(value, 65536, "Технические данные")


class LeadMetricsOut(LeadMetricsPayload):
    model_config = ConfigDict(extra="ignore")

    lead_id: int
    created_at: datetime
    updated_at: datetime


class LeadMetricsPage(ApiModel):
    model_config = ConfigDict(extra="ignore")

    items: list[LeadMetricsOut]
    total: int


class LeadMetricsUpdate(LeadMetricsPayload):
    time_on_page_seconds: float | None = Field(default=None, ge=0, le=60 * 60 * 24 * 30)
    buttons_clicked: list[Any] | None = None
    cursor_hotspots: list[Any] | None = None
    return_count: int | None = Field(default=None, ge=0, le=1_000_000)
    technical_info: dict[str, Any] | None = None


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail="Метрики для этой заявки не найдены")


@router.get("", response_model=LeadMetricsPage, summary="Список метрик")
def list_metrics(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return LeadMetricsCRUD.page(limit, offset)


@router.post(
    "/{lead_id}",
    response_model=LeadMetricsOut,
    status_code=201,
    summary="Записать метрики заявки",
)
def create_metrics(
    body: LeadMetricsPayload,
    lead_id: int = Path(gt=0),
) -> dict:
    with db_errors():
        return LeadMetricsCRUD.create({**body.model_dump(), "lead_id": lead_id})


@router.get("/{lead_id}", response_model=LeadMetricsOut, summary="Метрики одной заявки")
def get_metrics(lead_id: int = Path(gt=0)) -> dict:
    row = LeadMetricsCRUD.get(lead_id)
    if row is None:
        raise _missing()
    return row


@router.patch("/{lead_id}", response_model=LeadMetricsOut, summary="Изменить метрики")
def update_metrics(body: LeadMetricsUpdate, lead_id: int = Path(gt=0)) -> dict:
    data = body.model_dump(exclude_unset=True)
    with db_errors():
        with transaction():
            row = LeadMetricsCRUD.update(lead_id, data)
    if row is None:
        raise _missing()
    return row


@router.delete("/{lead_id}", status_code=204, summary="Удалить метрики")
def delete_metrics(lead_id: int = Path(gt=0)) -> None:
    if not LeadMetricsCRUD.delete(lead_id):
        raise _missing()
