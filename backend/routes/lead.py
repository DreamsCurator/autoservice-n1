"""Роут заявок. Операции идут в LeadCRUD и, для пакета формы, в LeadMetricsCRUD."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import ConfigDict, Field, field_validator

from core.database import transaction
from models.lead import LeadCRUD
from models.lead_metrics import LeadMetricsCRUD
from routes.common import ApiModel, db_errors
from routes.lead_metrics import LeadMetricsOut, LeadMetricsPayload

router = APIRouter(prefix="/leads", tags=["Заявки"])

Role = Literal["сотрудник", "руководитель"]


class LeadBody(ApiModel):
    first_name: str = Field(min_length=1, max_length=200, description="Имя")
    last_name: str = Field(min_length=1, max_length=200, description="Фамилия")
    middle_name: str | None = Field(default=None, max_length=200, description="Отчество")
    business_info: str = Field(min_length=1, max_length=4000, description="Информация о бизнесе")
    business_niche: str = Field(min_length=1, max_length=500, description="Ниша бизнеса")
    company_size: str = Field(min_length=1, max_length=500, description="Размер компании")
    business_size: str = Field(min_length=1, max_length=500, description="Размер бизнеса")
    task_volume: str = Field(min_length=1, max_length=500, description="Объём задачи")
    need_volume: str = Field(min_length=1, max_length=500, description="Объём потребности")
    role: Role = Field(description="Сотрудник или руководитель")
    deadline: str = Field(min_length=1, max_length=500, description="Срок, когда нужен результат")
    task_type: str = Field(min_length=1, max_length=500, description="Тип задачи")
    product_interest: str = Field(min_length=1, max_length=500, description="Интересующий продукт")
    budget: str = Field(min_length=1, max_length=200, description="Бюджет, значение ползунка")
    contact_method: str = Field(
        min_length=1,
        max_length=200,
        description="Предпочтительный способ связи",
    )
    convenient_time: str = Field(min_length=1, max_length=200, description="Удобное время")
    comment: str | None = Field(default=None, max_length=4000, description="Комментарий")

    @field_validator("role", mode="before")
    @classmethod
    def lower_role(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower() or None
        return value


class LeadCreate(LeadBody):
    metrics: LeadMetricsPayload = Field(description="Поведение на странице и техническая информация")


class LeadUpdate(ApiModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=200)
    last_name: str | None = Field(default=None, min_length=1, max_length=200)
    middle_name: str | None = Field(default=None, max_length=200)
    business_info: str | None = Field(default=None, min_length=1, max_length=4000)
    business_niche: str | None = Field(default=None, min_length=1, max_length=500)
    company_size: str | None = Field(default=None, min_length=1, max_length=500)
    business_size: str | None = Field(default=None, min_length=1, max_length=500)
    task_volume: str | None = Field(default=None, min_length=1, max_length=500)
    need_volume: str | None = Field(default=None, min_length=1, max_length=500)
    role: Role | None = None
    deadline: str | None = Field(default=None, min_length=1, max_length=500)
    task_type: str | None = Field(default=None, min_length=1, max_length=500)
    product_interest: str | None = Field(default=None, min_length=1, max_length=500)
    budget: str | None = Field(default=None, min_length=1, max_length=200)
    contact_method: str | None = Field(default=None, min_length=1, max_length=200)
    convenient_time: str | None = Field(default=None, min_length=1, max_length=200)
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("role", mode="before")
    @classmethod
    def lower_role(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower() or None
        return value


class LeadOut(LeadBody):
    model_config = ConfigDict(extra="ignore")

    id: int
    created_at: datetime
    updated_at: datetime


class LeadPackageOut(LeadOut):
    metrics: LeadMetricsOut | None = None


class LeadPage(ApiModel):
    model_config = ConfigDict(extra="ignore")

    items: list[LeadOut]
    total: int


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail="Заявка не найдена")


@router.get("", response_model=LeadPage, summary="Список заявок")
def list_leads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return LeadCRUD.page(limit, offset)


@router.post(
    "",
    response_model=LeadPackageOut,
    status_code=201,
    summary="Записать пакет заявки и метрик",
)
def create_lead(body: LeadCreate) -> dict:
    lead_data = body.model_dump(exclude={"metrics"})
    metrics_data = body.metrics.model_dump()
    with db_errors():
        with transaction():
            lead = LeadCRUD.create(lead_data)
            metrics = LeadMetricsCRUD.create({**metrics_data, "lead_id": lead["id"]})
    return {**lead, "metrics": metrics}


@router.get("/{lead_id}", response_model=LeadPackageOut, summary="Заявка с метриками")
def get_lead(lead_id: int = Path(gt=0)) -> dict:
    with transaction():
        lead = LeadCRUD.get(lead_id)
        metrics = LeadMetricsCRUD.get(lead_id) if lead is not None else None
    if lead is None:
        raise _missing()
    return {**lead, "metrics": metrics}


@router.patch("/{lead_id}", response_model=LeadOut, summary="Изменить заявку")
def update_lead(body: LeadUpdate, lead_id: int = Path(gt=0)) -> dict:
    data = body.model_dump(exclude_unset=True)
    with db_errors():
        with transaction():
            row = LeadCRUD.update(lead_id, data)
    if row is None:
        raise _missing()
    return row


@router.delete("/{lead_id}", status_code=204, summary="Удалить заявку")
def delete_lead(lead_id: int = Path(gt=0)) -> None:
    if not LeadCRUD.delete(lead_id):
        raise _missing()
