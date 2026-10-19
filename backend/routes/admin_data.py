"""Роут админ-данных. Операции идут в AdminDataCRUD."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import ConfigDict, Field

from core.database import transaction
from core.security import require_admin
from models.admin_data import AdminDataCRUD
from routes.common import ApiModel, db_errors

router = APIRouter(prefix="/admin-data", tags=["Админ-данные"])


class ServiceIn(ApiModel):
    name: str = Field(min_length=1, max_length=300, description="Название услуги")
    description: str | None = Field(default=None, max_length=2000, description="Описание услуги")


class AdminBody(ApiModel):
    services: list[ServiceIn] = Field(min_length=1, description="Услуги для интерфейса")
    budget_min: float = Field(ge=0, le=1_000_000_000, description="Нижняя граница ползунка бюджета")
    budget_max: float = Field(ge=0, le=1_000_000_000, description="Верхняя граница ползунка бюджета")
    budget_step: float = Field(
        default=1,
        gt=0,
        le=1_000_000_000,
        description="Шаг ползунка бюджета",
    )


class AdminUpdate(ApiModel):
    services: list[ServiceIn] | None = Field(default=None, min_length=1)
    budget_min: float | None = Field(default=None, ge=0, le=1_000_000_000)
    budget_max: float | None = Field(default=None, ge=0, le=1_000_000_000)
    budget_step: float | None = Field(default=None, gt=0, le=1_000_000_000)


class AdminOut(AdminBody):
    model_config = ConfigDict(extra="ignore")

    id: int
    created_at: datetime
    updated_at: datetime


class AdminPage(ApiModel):
    model_config = ConfigDict(extra="ignore")

    items: list[AdminOut]
    total: int


def _missing() -> HTTPException:
    return HTTPException(status_code=404, detail="Админ-данные не найдены")


def _dump_admin(body: AdminBody | AdminUpdate, *, exclude_unset: bool) -> dict:
    data = body.model_dump(exclude_unset=exclude_unset)
    if "services" in data and data["services"] is not None:
        data["services"] = [item.model_dump() for item in body.services or []]
    return data


@router.get("", response_model=AdminPage, summary="Список наборов админ-данных")
def list_admin(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    return AdminDataCRUD.page(limit, offset)


@router.get("/current", response_model=AdminOut, summary="Актуальные услуги и диапазон бюджета")
def current_admin() -> dict:
    row = AdminDataCRUD.latest()
    if row is None:
        raise HTTPException(status_code=404, detail="Админ-данные ещё не заданы")
    return row


@router.post(
    "",
    response_model=AdminOut,
    status_code=201,
    summary="Сохранить админ-данные",
    dependencies=[Depends(require_admin)],
)
def create_admin(body: AdminBody) -> dict:
    with db_errors():
        return AdminDataCRUD.create(_dump_admin(body, exclude_unset=False))


@router.get("/{item_id}", response_model=AdminOut, summary="Один набор админ-данных")
def get_admin(item_id: int = Path(gt=0)) -> dict:
    row = AdminDataCRUD.get(item_id)
    if row is None:
        raise _missing()
    return row


@router.patch(
    "/{item_id}",
    response_model=AdminOut,
    summary="Изменить админ-данные",
    dependencies=[Depends(require_admin)],
)
def update_admin(body: AdminUpdate, item_id: int = Path(gt=0)) -> dict:
    data = _dump_admin(body, exclude_unset=True)
    with db_errors():
        with transaction():
            row = AdminDataCRUD.update(item_id, data)
    if row is None:
        raise _missing()
    return row


@router.delete(
    "/{item_id}",
    status_code=204,
    summary="Удалить админ-данные",
    dependencies=[Depends(require_admin)],
)
def delete_admin(item_id: int = Path(gt=0)) -> None:
    if not AdminDataCRUD.delete(item_id):
        raise _missing()
