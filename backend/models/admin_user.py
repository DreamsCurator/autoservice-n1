"""Учётные записи администраторов панели."""

from __future__ import annotations

from typing import Any

from psycopg.errors import UniqueViolation

from core.database import delete_by, fetch_one, fetch_page, insert_returning, update_returning
from core.exceptions import Conflict


class AdminUser:
    """Администратор панели. Логин уникален, пароль хранится как хеш.

    CREATE TABLE IF NOT EXISTS admin_users (
        id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
        login TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT admin_users_login_uniq UNIQUE (login),
        CONSTRAINT admin_users_login_len CHECK (
            char_length(login) >= 3 AND char_length(login) <= 100
        ),
        CONSTRAINT admin_users_password_hash_len CHECK (char_length(password_hash) >= 20)
    );
    """

    table = "admin_users"
    insert_columns = (
        "login",
        "password_hash",
    )
    mutable_columns = insert_columns


class AdminUserCRUD:
    """Создание, чтение, правка и удаление администраторов."""

    @staticmethod
    def create(data: dict[str, Any]) -> dict[str, Any]:
        try:
            return insert_returning(AdminUser.table, AdminUser.insert_columns, data)
        except UniqueViolation as exc:
            raise Conflict("Администратор с таким логином уже есть") from exc

    @staticmethod
    def get(admin_id: int) -> dict[str, Any] | None:
        return fetch_one(AdminUser.table, "id", admin_id)

    @staticmethod
    def get_by_login(login: str) -> dict[str, Any] | None:
        return fetch_one(AdminUser.table, "login", login)

    @staticmethod
    def count() -> int:
        return int(fetch_page(AdminUser.table, "id", 1, 0)["total"])

    @staticmethod
    def page(limit: int, offset: int) -> dict[str, Any]:
        return fetch_page(AdminUser.table, "id", limit, offset)

    @staticmethod
    def update(admin_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        try:
            return update_returning(
                AdminUser.table,
                "id",
                admin_id,
                AdminUser.mutable_columns,
                data,
            )
        except UniqueViolation as exc:
            raise Conflict("Администратор с таким логином уже есть") from exc

    @staticmethod
    def delete(admin_id: int) -> bool:
        return delete_by(AdminUser.table, "id", admin_id)
