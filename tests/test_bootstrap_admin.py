from collections.abc import Iterator

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import bootstrap_admin
from app.infrastructure.models import Account, Person, Role


def test_bootstrap_creates_admin_only_once(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    answers: Iterator[str] = iter(
        ["admin-cui", "DNI", "12345678", "Admin EPCC", "admin@epcc.edu.pe", "admin"]
    )
    monkeypatch.setattr(bootstrap_admin, "SessionLocal", session_factory)
    monkeypatch.setattr("builtins.input", lambda _prompt: next(answers))
    monkeypatch.setattr(bootstrap_admin, "getpass", lambda _prompt: "clave-de-prueba-segura")
    bootstrap_admin.main()
    bootstrap_admin.main()
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Account)) == 1
        assert session.scalar(select(Person.role)) == Role.INVENTORY_ADMIN
