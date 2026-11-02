import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker
from starlette.types import Message, Receive, Scope, Send

from app.api.routes import SessionDep, install_error_handlers
from app.infrastructure import database
from app.infrastructure.models import Category


def test_commit_happens_before_response_and_integrity_errors_are_reported(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> None:
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    api = FastAPI()
    install_error_handlers(api)

    @api.post("/categories", status_code=201)
    def create(session: SessionDep) -> dict[str, str]:
        session.add(Category(name="Categoría persistida"))
        return {"status": "created"}

    async def check_response(scope: Scope, receive: Receive, send: Send) -> None:
        async def checked_send(message: Message) -> None:
            if message["type"] == "http.response.start" and message["status"] == 201:
                with session_factory() as session:
                    assert session.scalar(select(Category.id)) is not None
            await send(message)

        await api(scope, receive, checked_send)

    with TestClient(check_response) as client:
        assert client.post("/categories").status_code == 201
        # La unicidad falla en commit, no en flush: nunca debe devolverse un falso 201.
        duplicate = client.post("/categories")
        assert duplicate.status_code == 409
