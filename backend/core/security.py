"""Хеширование паролей и JWT для админ-панели."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from models.admin_user import AdminUserCRUD

_bearer = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 12


def jwt_secret() -> str:
    secret = os.environ.get("JWT_SECRET", "").strip()
    if not secret:
        raise RuntimeError("Не задана переменная JWT_SECRET")
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(*, admin_id: int, login: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "login": login,
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="Срок действия токена истёк") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="Некорректный токен") from exc


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    payload = decode_access_token(credentials.credentials)
    try:
        admin_id = int(payload.get("sub", 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Некорректный токен") from exc
    admin = AdminUserCRUD.get(admin_id)
    if admin is None:
        raise HTTPException(status_code=401, detail="Администратор не найден")
    return {
        "id": admin["id"],
        "login": admin["login"],
        "created_at": admin["created_at"],
        "updated_at": admin["updated_at"],
    }
