"""El nombre de la reserva procede de su solicitante, sin exponer otras reservas."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.models import Person, Role


def solicitar(client: TestClient, token: str, unidad: str) -> dict:
    inicio = datetime.now(UTC) + timedelta(days=1)
    respuesta = client.post(
        "/reservations",
        headers={"Authorization": token},
        json={
            "unit_id": unidad,
            "starts_at": inicio.isoformat(),
            "ends_at": (inicio + timedelta(hours=1)).isoformat(),
            "intended_use": "Estudio",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def test_nombre_correcto_con_ids_distintos_y_privacidad_de_reservas(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    admin = {"Authorization": flujo_basico["admin"]}
    solicitar(client, flujo_basico["estudiante"], flujo_basico["unidad"])
    # Una persona sin cuenta hace que id_persona e id_solicitante no coincidan.
    with session_factory.begin() as sesion:
        sesion.add(
            Person(
                first_names="Otra",
                last_names="Persona",
                document_type="DEMO",
                document_number="OTRA-01",
                institutional_email="otra@example.test",
                role=Role.ADMINISTRATIVE,
                school_affiliation="EPCC",
                start_date=datetime.now(UTC).date(),
            )
        )
    docente = client.post(
        "/people",
        headers=admin,
        json={
            "document_type": "DNI",
            "document_number": "33334444",
            "first_names": "María Elena",
            "last_names": "Pérez Gómez",
            "institutional_email": "docente@example.test",
            "role": "DOCENTE",
            "school_affiliation": "EPCC",
            "start_date": str(datetime.now(UTC).date()),
            "username": "docente",
            "password": "clave-docente-de-prueba",
            "teacher_code": "DOC-NOMBRE-01",
            "specialty": "Computación",
        },
    )
    assert docente.status_code == 201, docente.text
    assert docente.json()["id"] != docente.json()["applicant_id"]
    login = client.post(
        "/auth/token",
        data={
            "username": "docente",
            "password": "clave-docente-de-prueba",
        },
    )
    assert login.status_code == 200
    token_docente = "Bearer " + login.json()["access_token"]
    reserva = solicitar(client, token_docente, flujo_basico["unidad"])
    assert reserva["applicant_name"] == "María Elena Pérez Gómez"
    assert reserva["applicant_id"] == docente.json()["applicant_id"]
    todas = client.get("/reservations", headers=admin).json()
    assert {fila["applicant_name"] for fila in todas} == {
        "Luis Estudiante",
        "María Elena Pérez Gómez",
    }
    propias = client.get("/reservations", headers={"Authorization": token_docente}).json()
    assert len(propias) == 1
    assert propias[0]["applicant_name"] == "María Elena Pérez Gómez"
    estudiante = client.get(
        "/reservations", headers={"Authorization": flujo_basico["estudiante"]}
    ).json()
    assert len(estudiante) == 1 and estudiante[0]["applicant_name"] == "Luis Estudiante"
    assert "institutional_email" not in propias[0]
    assert "password" not in propias[0]


def test_el_nombre_se_conserva_al_desactivar_al_solicitante(
    client: TestClient,
    flujo_basico: dict[str, str],
) -> None:
    reserva = solicitar(client, flujo_basico["estudiante"], flujo_basico["unidad"])
    admin = {"Authorization": flujo_basico["admin"]}
    respuesta = client.post(f"/people/{flujo_basico['persona']}/deactivate", headers=admin)
    assert respuesta.status_code == 200
    filas = client.get("/reservations", headers=admin).json()
    assert filas[0]["id"] == reserva["id"]
    assert filas[0]["applicant_name"] == "Luis Estudiante"
