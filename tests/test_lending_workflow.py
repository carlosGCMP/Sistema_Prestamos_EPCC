"""Flujo operativo de la API sobre el esquema SQL español (sin rutas históricas)."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.modelos_sql import (
    CaracteristicaDelBien,
    HistorialDeCambios,
    RegistroDeReserva,
    UbicacionDelBien,
)
from app.infrastructure.models import Account, Bien, Person


def test_reservar_confirmar_cancelar_y_conservar_relaciones_sql(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    admin = {"Authorization": flujo_basico["admin"]}
    estudiante = {"Authorization": flujo_basico["estudiante"]}
    inicio = datetime.now(UTC) + timedelta(days=1)
    respuesta = client.post(
        "/reservations",
        headers=estudiante,
        json={
            "unit_id": flujo_basico["unidad"],
            "starts_at": inicio.isoformat(),
            "ends_at": (inicio + timedelta(hours=2)).isoformat(),
            "intended_use": "Estudio",
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    reserva = respuesta.json()
    assert reserva["applicant_id"] == flujo_basico["solicitante"]
    confirmada = client.post(
        f"/reservations/{reserva['id']}/decision", headers=admin, json={"confirm": True}
    )
    assert confirmada.status_code == 200, confirmada.text
    with session_factory() as sesion:
        registro = sesion.scalar(
            select(RegistroDeReserva).where(RegistroDeReserva.id_solicitud == int(reserva["id"]))
        )
        assert registro is not None and registro.estado == "CONFIRMADA"
        assert sesion.scalar(select(Bien.name)) == "Laptop"
        assert sesion.scalar(select(CaracteristicaDelBien.nombre_caracteristica)) == "RAM"
        assert sesion.scalar(select(UbicacionDelBien.ubicacion)) == "Laboratorio"
        assert sesion.scalar(select(HistorialDeCambios.id_historial)) is not None
        persona = sesion.get(Person, int(flujo_basico["persona"]))
        assert persona is not None and persona.student_profile is not None
        assert persona.student_profile.applicant_id == int(flujo_basico["solicitante"])
    cancelada = client.post(f"/reservations/{reserva['id']}/cancel", headers=estudiante)
    assert cancelada.status_code == 200, cancelada.text
    with session_factory() as sesion:
        assert sesion.scalar(select(RegistroDeReserva.estado)) == "CANCELADA"
    assert (
        client.get(
            "/inventory/units", headers=estudiante, params={"item_type_id": flujo_basico["tipo"]}
        ).status_code
        == 200
    )


def test_una_unidad_por_ficha_y_permisos_administrativos(
    client: TestClient,
    flujo_basico: dict[str, str],
) -> None:
    admin = {"Authorization": flujo_basico["admin"]}
    estudiante = {"Authorization": flujo_basico["estudiante"]}
    repetida = client.post(
        "/inventory/units",
        headers=admin,
        json={
            "item_card_id": flujo_basico["ficha"],
            "inventory_code": "EPCC-002",
            "serial_number": "SERIE-002",
            "location": "Laboratorio",
            "custody": "EPCC",
            "condition": "Operativa",
        },
    )
    assert repetida.status_code == 409
    assert (
        client.post("/inventory/types", headers=estudiante, json={"name": "Prohibido"}).status_code
        == 403
    )
    assert client.get("/people", headers=estudiante).status_code == 403
    assert client.get("/me", headers=admin).json()["is_admin"] is True
    assert client.get("/me", headers=estudiante).json()["is_admin"] is False


def test_rechaza_ids_invalidos_y_nombre_en_tipo_inexistente(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    admin = {"Authorization": flujo_basico["admin"]}
    assert client.get("/people/no-es-un-id", headers=admin).status_code == 422
    assert client.get("/people/9223372036854775808", headers=admin).status_code == 422
    respuesta = client.post(
        "/inventory/categories", headers=admin, json={"name": "Huérfana", "item_type_id": "999999"}
    )
    assert respuesta.status_code == 404
    with session_factory() as sesion:
        assert len(sesion.scalars(select(Account)).all()) == 2
