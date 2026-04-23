from __future__ import annotations

import os
import time

from fastapi import Depends, Header, HTTPException
import jwt


ROLE_PERMISSIONS = {
    "contractor": {"translate", "code_assist", "docs"},
    "engineer": {"translate", "review", "test_gen", "refactor", "code_assist", "docs"},
    "admin": {"translate", "review", "test_gen", "refactor", "code_assist", "docs", "admin"},
}


def require_permission(payload: dict, permission: str) -> None:
    role = payload.get("role")
    perms = ROLE_PERMISSIONS.get(role, set())
    if permission not in perms:
        raise HTTPException(status_code=403, detail=f"missing permission: {permission}")


def _decode_token(token: str) -> dict:
    pubkey = os.getenv("JWT_PUBLIC_KEY", "")
    if not pubkey or pubkey == "placeholder":
        raise HTTPException(status_code=401, detail="JWT public key not configured")

    try:
        payload = jwt.decode(token, pubkey, algorithms=["RS256"])
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=401, detail="token expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc

    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        raise HTTPException(status_code=401, detail="token expired")

    return payload


def verify_token(authorization: str | None = Header(default=None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="missing authorization")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="invalid authorization header")

    return _decode_token(parts[1])


def permission_dependency(permission: str):
    def _dep(payload: dict = Depends(verify_token)) -> dict:
        require_permission(payload, permission)
        return payload

    return _dep
