"""Драйвер PostgreSQL.

Параметры читаются из окружения контейнера backend:
POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB.
В compose хост — сервис postgres, порт 5432, сеть data.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from textwrap import dedent
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

_CREATE_SQL = re.compile(
    r"CREATE TABLE IF NOT EXISTS\b.*?;",
    re.IGNORECASE | re.DOTALL,
)

JSONB_COLUMNS = frozenset(
    {
        "buttons_clicked",
        "cursor_hotspots",
        "technical_info",
        "services",
    }
)

_conn_ctx: contextvars.ContextVar[psycopg.Connection | None] = contextvars.ContextVar(
    "postgres_connection",
    default=None,
)


def build_conninfo() -> str:
    required = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Не заданы переменные подключения к PostgreSQL: {joined}")
    return make_conninfo(
        host=os.environ.get("POSTGRES_HOST", "postgres"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        application_name="autoservice-backend",
    )


pool = ConnectionPool(
    conninfo=build_conninfo(),
    min_size=1,
    max_size=4,
    timeout=10,
    kwargs={"row_factory": dict_row},
    open=False,
)


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def adapt(column: str, value: Any) -> Any:
    if column in JSONB_COLUMNS and value is not None and not isinstance(value, str):
        return Jsonb(value, dumps=_dumps)
    return value


@contextmanager
def transaction() -> Iterator[psycopg.Connection]:
    """Одна транзакция на цепочку вызовов CRUD в текущем потоке."""
    current = _conn_ctx.get()
    if current is not None:
        yield current
        return

    with pool.connection() as conn:
        token = _conn_ctx.set(conn)
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            _conn_ctx.reset(token)


@contextmanager
def cursor():
    with transaction() as conn:
        with conn.cursor() as cur:
            yield cur


def ping() -> bool:
    with cursor() as cur:
        cur.execute("SELECT 1")
        return cur.fetchone() is not None


def insert_returning(
    table: str,
    columns: tuple[str, ...],
    data: dict[str, Any],
) -> dict[str, Any]:
    query = sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING *").format(
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in columns),
    )
    values = [adapt(column, data[column]) for column in columns]
    with cursor() as cur:
        cur.execute(query, values)
        row = cur.fetchone()
    if row is None:
        raise RuntimeError(f"INSERT в {table} не вернул строку")
    return row


def fetch_one(table: str, key_column: str, key: Any) -> dict[str, Any] | None:
    query = sql.SQL("SELECT * FROM {} WHERE {} = {}").format(
        sql.Identifier(table),
        sql.Identifier(key_column),
        sql.Placeholder(),
    )
    with cursor() as cur:
        cur.execute(query, (key,))
        return cur.fetchone()


def fetch_page(table: str, order_by: str, limit: int, offset: int) -> dict[str, Any]:
    count_query = sql.SQL("SELECT COUNT(*) AS total FROM {}").format(
        sql.Identifier(table)
    )
    page_query = sql.SQL(
        "SELECT * FROM {} ORDER BY {} DESC LIMIT {} OFFSET {}"
    ).format(
        sql.Identifier(table),
        sql.Identifier(order_by),
        sql.Placeholder(),
        sql.Placeholder(),
    )
    with cursor() as cur:
        cur.execute(count_query)
        total_row = cur.fetchone()
        total = 0 if total_row is None else int(total_row["total"])
        cur.execute(page_query, (limit, offset))
        return {"items": list(cur.fetchall()), "total": total}


def fetch_latest(table: str) -> dict[str, Any] | None:
    query = sql.SQL(
        "SELECT * FROM {} ORDER BY updated_at DESC, id DESC LIMIT 1"
    ).format(sql.Identifier(table))
    with cursor() as cur:
        cur.execute(query)
        return cur.fetchone()


def update_returning(
    table: str,
    key_column: str,
    key: Any,
    columns: tuple[str, ...],
    data: dict[str, Any],
) -> dict[str, Any] | None:
    selected = [column for column in columns if column in data]
    if not selected:
        return fetch_one(table, key_column, key)

    assignments = sql.SQL(", ").join(
        sql.SQL("{} = {}").format(sql.Identifier(column), sql.Placeholder())
        for column in selected
    )
    query = sql.SQL(
        "UPDATE {} SET {}, updated_at = NOW() WHERE {} = {} RETURNING *"
    ).format(
        sql.Identifier(table),
        assignments,
        sql.Identifier(key_column),
        sql.Placeholder(),
    )
    values: list[Any] = [adapt(column, data[column]) for column in selected]
    values.append(key)
    with cursor() as cur:
        cur.execute(query, values)
        return cur.fetchone()


def delete_by(table: str, key_column: str, key: Any) -> bool:
    query = sql.SQL("DELETE FROM {} WHERE {} = {}").format(
        sql.Identifier(table),
        sql.Identifier(key_column),
        sql.Placeholder(),
    )
    with cursor() as cur:
        cur.execute(query, (key,))
        return cur.rowcount == 1


def create_sql_from_model(model: type) -> str:
    """Берёт CREATE TABLE из докстринга класса модели."""
    text = dedent(model.__doc__ or "")
    match = _CREATE_SQL.search(text)
    if match is None:
        raise RuntimeError(f"В докстринге {model.__name__} нет SQL создания таблицы")
    statement = match.group(0).strip()
    for column in getattr(model, "insert_columns", ()):
        if re.search(rf"\b{re.escape(column)}\b", statement) is None:
            raise RuntimeError(
                f"Колонка {column} не найдена в SQL модели {model.__name__}"
            )
    return statement


def init_schema(statements: list[str]) -> None:
    delay = 0.5
    last_error: Exception | None = None
    for attempt in range(1, 11):
        try:
            with cursor() as cur:
                for statement in statements:
                    cur.execute(statement)
            logger.info("Таблицы PostgreSQL готовы")
            return
        except psycopg.OperationalError as exc:
            last_error = exc
            logger.warning("PostgreSQL ещё не готов, попытка %s", attempt)
            time.sleep(delay)
            delay = min(delay * 2, 5)
    if last_error is not None:
        raise last_error
    raise RuntimeError("Не удалось создать таблицы")
