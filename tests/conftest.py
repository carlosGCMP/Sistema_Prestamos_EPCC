from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.infrastructure.models  # noqa: F401
import app.main as main
from app.infrastructure import database
from app.infrastructure.database import Base


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    try:
        yield factory
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient]:
    engine = session_factory.kw["bind"]
    # Se usa la inicialización y la transacción reales, pero sobre SQLite aislado.
    monkeypatch.setattr(database, "crear_sesion", session_factory)
    monkeypatch.setattr(
        main, "inicializar_base_datos", lambda: database.inicializar_base_datos(engine)
    )
    with TestClient(main.app) as test_client:
        yield test_client
