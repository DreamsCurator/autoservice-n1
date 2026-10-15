"""Общие схемы и перевод ошибок базы в ответы API."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, field_validator

from core.exceptions import Conflict, InvalidData, NotFound


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("*", mode="before")
    @classmethod
    def strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


def limit_json(value: Any, max_chars: int, label: str) -> Any:
    try:
        encoded = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: некорректный JSON") from exc
    if len(encoded) > max_chars:
        raise ValueError(f"{label} слишком большой")
    return value


def check_events(value: list[Any] | None, label: str) -> list[Any] | None:
    if value is None:
        return None
    if len(value) > 2000:
        raise ValueError(f"Слишком много записей: {label}")
    for item in value:
        if isinstance(item, str):
            if not item.strip() or len(item) > 300:
                raise ValueError(f"Некорректный элемент списка: {label}")
            continue
        if isinstance(item, dict):
            continue
        raise ValueError(f"Элемент списка {label} должен быть строкой или объектом")
    return limit_json(value, 65536, label)


@contextmanager
def db_errors() -> Iterator[None]:
    try:
        yield
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidData as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
