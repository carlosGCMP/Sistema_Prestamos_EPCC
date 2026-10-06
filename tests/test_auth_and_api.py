from datetime import date

from sqlalchemy.orm import Session, sessionmaker

from app.models import Account, Person, Role
from app.security import hash_password


def test_health_and_openapi(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/health").json() == {"status": "ok"}
    schema = client.get("/openapi.json").json()
    assert "/loans/{loan_id}/return" in schema["paths"]
    assert "/reservations/{reservation_id}/decision" in schema["paths"]


def test_login_and_role_protected_profile(client, session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        person = Person(
            cui="cui-admin",
            document_type="DNI",
            document_number="12345678",
            full_name="Administradora EPCC",
            institutional_email="admin@epcc.edu.pe",
            role=Role.ADMIN,
            school_affiliation="EPCC",
            start_date=date(2026, 1, 1),
        )
        session.add(person)
        session.flush()
        session.add(
            Account(
                person_id=person.id,
                username="admin",
                password_hash=hash_password("una-clave-segura-2026"),
            )
        )

    response = client.post(
        "/auth/token", data={"username": "admin", "password": "una-clave-segura-2026"}
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    assert client.get("/me", headers=headers).status_code == 200
    assert client.post("/auth/logout", headers=headers).status_code == 204
    assert client.get("/me", headers=headers).status_code == 401


def test_login_rejects_wrong_password(client, session_factory: sessionmaker[Session]) -> None:
    with session_factory.begin() as session:
        person = Person(
            cui="cui-admin",
            document_type="DNI",
            document_number="12345678",
            full_name="Administradora EPCC",
            institutional_email="admin@epcc.edu.pe",
            role=Role.ADMIN,
            school_affiliation="EPCC",
            start_date=date(2026, 1, 1),
        )
        session.add(person)
        session.flush()
        session.add(
            Account(
                person_id=person.id,
                username="admin",
                password_hash=hash_password("una-clave-segura-2026"),
            )
        )
    response = client.post("/auth/token", data={"username": "admin", "password": "incorrecta"})
    assert response.status_code == 401
