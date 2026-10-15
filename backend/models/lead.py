"""Заявка тёплого клиента."""

from __future__ import annotations

from typing import Any

from psycopg.errors import CheckViolation

from core.database import delete_by, fetch_one, fetch_page, insert_returning, update_returning
from core.exceptions import InvalidData


class Lead:
    """Заявка тёплого клиента. Одна строка — одна отправка формы.

    Контакт: имя, фамилия и отчество.
    Бизнес: свободное описание, ниша, размер компании и размер бизнеса.
    Задача: объём задачи, объём потребности, тип, интересующий продукт и срок результата.
    Роль клиента — сотрудник или руководитель.
    Бюджет — строка, значение ползунка на сайте.
    Связь: предпочтительный способ и удобное время.
    Комментарий необязателен.

    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        middle_name TEXT,
        business_info TEXT NOT NULL,
        business_niche TEXT NOT NULL,
        company_size TEXT NOT NULL,
        business_size TEXT NOT NULL,
        task_volume TEXT NOT NULL,
        need_volume TEXT NOT NULL,
        role TEXT NOT NULL,
        deadline TEXT NOT NULL,
        task_type TEXT NOT NULL,
        product_interest TEXT NOT NULL,
        budget TEXT NOT NULL,
        contact_method TEXT NOT NULL,
        convenient_time TEXT NOT NULL,
        comment TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT leads_role_chk CHECK (role IN ('сотрудник', 'руководитель'))
    );
    """

    table = "leads"
    insert_columns = (
        "first_name",
        "last_name",
        "middle_name",
        "business_info",
        "business_niche",
        "company_size",
        "business_size",
        "task_volume",
        "need_volume",
        "role",
        "deadline",
        "task_type",
        "product_interest",
        "budget",
        "contact_method",
        "convenient_time",
        "comment",
    )
    mutable_columns = insert_columns


class LeadCRUD:
    """Создание, чтение, правка и удаление заявок."""

    @staticmethod
    def create(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return insert_returning(Lead.table, Lead.insert_columns, data)
        except CheckViolation as exc:
            raise _invalid(exc) from exc

    @staticmethod
    def get(lead_id: int) -> dict[str, Any] | None:
        return fetch_one(Lead.table, "id", lead_id)

    @staticmethod
    def page(limit: int, offset: int) -> dict[str, Any]:
        return fetch_page(Lead.table, "id", limit, offset)

    @staticmethod
    def update(lead_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return update_returning(Lead.table, "id", lead_id, Lead.mutable_columns, data)
        except CheckViolation as exc:
            raise _invalid(exc) from exc

    @staticmethod
    def delete(lead_id: int) -> bool:
        return delete_by(Lead.table, "id", lead_id)


def _invalid(exc: CheckViolation) -> InvalidData:
    name = getattr(getattr(exc, "diag", None), "constraint_name", None)
    if name == "leads_role_chk":
        return InvalidData("Роль должна быть «сотрудник» или «руководитель»")
    return InvalidData("Некорректные данные заявки")
