from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_session
from app.models import Account, Person, PersonState, Role
from app.settings import get_settings

password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres")
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_access_token(account: Account) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(account.id),
        "person_id": str(account.person_id),
        "session_version": account.session_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm="HS256")


def get_current_account(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
) -> Account:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión vencida",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token, get_settings().jwt_secret.get_secret_value(), algorithms=["HS256"]
        )
        account_id = UUID(payload["sub"])
        session_version = int(payload["session_version"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        raise unauthorized from error

    account = session.scalar(
        select(Account).options(joinedload(Account.person)).where(Account.id == account_id)
    )
    if (
        account is None
        or not account.active
        or account.session_version != session_version
        or account.person.state != PersonState.ACTIVE
    ):
        raise unauthorized
    return account


def require_roles(*roles: Role) -> Callable[..., Person]:
    def dependency(
        account: Annotated[Account, Depends(get_current_account)],
    ) -> Person:
        if account.person.role not in roles:
            raise HTTPException(status_code=403, detail="No tiene permiso para esta operación")
        return account.person

    return dependency


CurrentAccount = Annotated[Account, Depends(get_current_account)]
AdminActor = Annotated[Person, Depends(require_roles(Role.ADMIN))]
MemberActor = Annotated[Person, Depends(require_roles(Role.STUDENT, Role.TEACHER, Role.ADMIN))]
