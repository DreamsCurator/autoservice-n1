"""Авторизация администраторов: статус, регистрация первого, вход, профиль."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ConfigDict, Field, field_validator

from core.security import (
    create_access_token,
    hash_password,
    require_admin,
    verify_password,
)
from models.admin_user import AdminUserCRUD
from routes.common import ApiModel, db_errors

router = APIRouter(prefix="/auth", tags=["Авторизация"])


class AuthCredentials(ApiModel):
    login: str = Field(min_length=3, max_length=100, description="Логин администратора")
    password: str = Field(min_length=6, max_length=200, description="Пароль")

    @field_validator("login", mode="before")
    @classmethod
    def normalize_login(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower() or None
        return value


class AuthStatus(ApiModel):
    model_config = ConfigDict(extra="ignore")

    has_admin: bool
    registration_open: bool


class AdminPublic(ApiModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    login: str
    created_at: datetime
    updated_at: datetime


class TokenOut(ApiModel):
    model_config = ConfigDict(extra="ignore")

    access_token: str
    token_type: str = "bearer"
    admin: AdminPublic


@router.get("/status", response_model=AuthStatus, summary="Есть ли уже администратор")
def auth_status() -> dict:
    has_admin = AdminUserCRUD.count() > 0
    return {"has_admin": has_admin, "registration_open": not has_admin}


@router.post(
    "/register",
    response_model=TokenOut,
    status_code=201,
    summary="Зарегистрировать первого администратора",
)
def register(body: AuthCredentials) -> dict:
    if AdminUserCRUD.count() > 0:
        raise HTTPException(
            status_code=403,
            detail="Регистрация закрыта: администратор уже создан",
        )
    with db_errors():
        admin = AdminUserCRUD.create(
            {
                "login": body.login,
                "password_hash": hash_password(body.password),
            }
        )
    token = create_access_token(admin_id=admin["id"], login=admin["login"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": {
            "id": admin["id"],
            "login": admin["login"],
            "created_at": admin["created_at"],
            "updated_at": admin["updated_at"],
        },
    }


@router.post("/login", response_model=TokenOut, summary="Вход администратора")
def login(body: AuthCredentials) -> dict:
    admin = AdminUserCRUD.get_by_login(body.login)
    if admin is None or not verify_password(body.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_access_token(admin_id=admin["id"], login=admin["login"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "admin": {
            "id": admin["id"],
            "login": admin["login"],
            "created_at": admin["created_at"],
            "updated_at": admin["updated_at"],
        },
    }


@router.get("/me", response_model=AdminPublic, summary="Текущий администратор")
def me(admin: dict = Depends(require_admin)) -> dict:
    return admin
