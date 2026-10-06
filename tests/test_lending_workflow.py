from datetime import UTC, date, datetime, timedelta

from sqlalchemy.orm import Session, sessionmaker

from app.models import Account, Person, Role
from app.security import hash_password


def test_policy_reservation_loan_renewal_and_return(
    client, session_factory: sessionmaker[Session]
) -> None:  # type: ignore[no-untyped-def]
    with session_factory.begin() as session:
        admin = Person(
            cui="cui-admin",
            document_type="DNI",
            document_number="87654321",
            full_name="Administradora EPCC",
            institutional_email="admin@epcc.edu.pe",
            role=Role.ADMIN,
            school_affiliation="EPCC",
            start_date=date(2026, 1, 1),
        )
        session.add(admin)
        session.flush()
        session.add(
            Account(
                person_id=admin.id,
                username="admin",
                password_hash=hash_password("clave-administrativa-segura-2026"),
            )
        )
    login = client.post(
        "/auth/token", data={"username": "admin", "password": "clave-administrativa-segura-2026"}
    )
    admin_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert login.status_code == 200

    student = client.post(
        "/people",
        headers=admin_headers,
        json={
            "cui": "cui-student",
            "document_type": "DNI",
            "document_number": "11223344",
            "full_name": "Estudiante de Prueba",
            "institutional_email": "student@epcc.edu.pe",
            "role": "ESTUDIANTE",
            "school_affiliation": "EPCC",
            "start_date": "2026-01-01",
            "username": "student",
            "password": "clave-estudiantil-segura-2026",
            "student_code": "20260001",
            "program": "Ciencia de la Computación",
            "semester": 5,
        },
    )
    assert student.status_code == 201

    category = client.post(
        "/inventory/categories", headers=admin_headers, json={"name": "Informática"}
    )
    item_type = client.post(
        "/inventory/types",
        headers=admin_headers,
        json={
            "name": "Laptop",
            "category_id": category.json()["id"],
            "lendable": True,
        },
    )
    item = client.post(
        "/inventory/items",
        headers=admin_headers,
        json={
            "item_type_id": item_type.json()["id"],
            "name": "Laptop de préstamo",
        },
    )
    unit = client.post(
        "/inventory/units",
        headers=admin_headers,
        json={
            "item_card_id": item.json()["id"],
            "inventory_code": "EPCC-LAP-001",
            "location": "Almacén EPCC",
            "custody": "Responsable de laboratorio",
            "condition": "Operativa",
            "accessories": ["cargador"],
        },
    )
    assert unit.status_code == 201

    policy = client.post(
        "/policies",
        headers=admin_headers,
        json={
            "name": "Préstamo estándar",
            "role": "ESTUDIANTE",
            "max_units": 1,
            "max_duration": 1,
            "duration_unit": "DIAS",
            "allowed_modes": ["RETIRO"],
            "allows_renewal": True,
            "max_renewals": 1,
            "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
        },
    )
    assert policy.status_code == 201

    student_token = client.post(
        "/auth/token", data={"username": "student", "password": "clave-estudiantil-segura-2026"}
    ).json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    reserved_from = datetime.now(UTC) + timedelta(days=2)
    reserved_until = reserved_from + timedelta(hours=3)
    reservation = client.post(
        "/reservations",
        headers=student_headers,
        json={
            "unit_id": unit.json()["id"],
            "starts_at": reserved_from.isoformat(),
            "ends_at": reserved_until.isoformat(),
            "intended_use": "Proyecto académico",
        },
    )
    assert reservation.status_code == 201
    decision = client.post(
        f"/reservations/{reservation.json()['id']}/decision",
        headers=admin_headers,
        json={"confirm": True},
    )
    assert decision.status_code == 200, decision.json()
    cancelled = client.post(
        f"/reservations/{reservation.json()['id']}/cancel", headers=student_headers
    )
    assert cancelled.status_code == 200

    due = datetime.now(UTC) + timedelta(hours=2)
    loan = client.post(
        "/loans",
        headers=admin_headers,
        json={
            "applicant_id": student.json()["id"],
            "unit_id": unit.json()["id"],
            "due_at": due.isoformat(),
            "use_mode": "RETIRO",
            "delivered_condition": "Operativa",
            "delivered_accessories": ["cargador"],
        },
    )
    assert loan.status_code == 201
    renewed_due = due + timedelta(hours=4)
    renewal = client.post(
        f"/loans/{loan.json()['id']}/renewals",
        headers=admin_headers,
        json={"new_due_at": renewed_due.isoformat()},
    )
    assert renewal.status_code == 201
    returned = client.post(
        f"/loans/{loan.json()['id']}/return",
        headers=admin_headers,
        json={"condition": "Operativa", "accessories": ["cargador"], "disposition": "DISPONIBLE"},
    )
    assert returned.status_code == 200
    assert returned.json()["state"] == "DEVUELTO"
    assert client.get("/audit", headers=admin_headers).status_code == 200
