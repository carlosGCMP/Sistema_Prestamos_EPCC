"""Permisos, totales globales y reportes sin modificar los datos."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application import basic_use_cases, prestamos, reportes
from app.infrastructure.models import (
    Account,
    Administrador,
    Category,
    ItemType,
    Loan,
    LoanState,
    Person,
    PhysicalUnit,
    Role,
    UnitState,
    UseMode,
)


def test_reportes_requieren_sesion(client: TestClient) -> None:
    assert client.get("/reports/summary").status_code == 401


def test_interfaz_de_reportes_carga_sus_estilos_y_no_ofrece_importacion(client: TestClient) -> None:
    pagina = client.get("/").text
    assert 'href="/reportes.css"' in pagina
    assert pagina.count("data-report-total=") == 6
    assert 'id="reports-inventory"' in pagina
    assert 'id="reports-reservations"' in pagina
    assert 'id="reports-loans"' in pagina
    assert "reports-import-form" not in pagina
    assert "reports-file" not in pagina
    estilos = client.get("/reportes.css")
    assert estilos.status_code == 200
    assert "text/css" in estilos.headers["content-type"]


def test_estudiante_no_puede_consultar_reportes(
    client: TestClient,
    flujo_basico: dict[str, str],
) -> None:
    respuesta = client.get(
        "/reports/summary", headers={"Authorization": flujo_basico["estudiante"]}
    )
    assert respuesta.status_code == 403


def test_resumen_de_una_base_sin_operaciones(
    client: TestClient,
    flujo_basico: dict[str, str],
) -> None:
    respuesta = client.get("/reports/summary", headers={"Authorization": flujo_basico["admin"]})
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["personas"] == 2
    assert datos["unidades"] == 1
    assert datos["reservas"] == datos["prestamos"] == 0
    assert datos["inventario_por_estado"] == {"DISPONIBLE": 1}
    assert datos["reservas_por_estado"] == {}
    assert datos["prestamos_por_estado"] == {"ACTIVO": 0, "VENCIDO": 0}
    assert datetime.fromisoformat(datos["generado_en"]).tzinfo is not None


def test_totales_consultan_toda_la_base_no_la_pagina_de_usuarios(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory.begin() as sesion:
        sesion.add_all(
            [
                Person(
                    first_names=f"Persona {numero}",
                    last_names="Prueba",
                    document_type="DEMO",
                    document_number=f"REPORTE-{numero}",
                    institutional_email=f"reporte{numero}@example.test",
                    role=Role.ADMINISTRATIVE,
                    school_affiliation="EPCC",
                    start_date=datetime.now(UTC).date(),
                )
                for numero in range(105)
            ]
        )
    admin = {"Authorization": flujo_basico["admin"]}
    assert len(client.get("/people", headers=admin).json()) == 100
    assert client.get("/reports/summary", headers=admin).json()["personas"] == 107


def test_entregar_un_nuevo_prestamo_se_refleja_en_reportes(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = {"Authorization": flujo_basico["admin"]}
    estudiante = {"Authorization": flujo_basico["estudiante"]}
    antes = client.get("/reports/summary", headers=admin).json()
    inicio = datetime.now(UTC) + timedelta(minutes=5)
    fin = inicio + timedelta(hours=2)
    reserva = client.post(
        "/reservations",
        headers=estudiante,
        json={
            "unit_id": flujo_basico["unidad"],
            "starts_at": inicio.isoformat(),
            "ends_at": fin.isoformat(),
            "intended_use": "Comprobar el reporte de préstamos",
        },
    )
    assert reserva.status_code == 201, reserva.text
    decision = client.post(
        f"/reservations/{reserva.json()['id']}/decision", headers=admin, json={"confirm": True}
    )
    assert decision.status_code == 200, decision.text
    for modulo in (basic_use_cases, prestamos, reportes):
        monkeypatch.setattr(modulo, "ahora", lambda: inicio + timedelta(minutes=1))
    entrega = client.post(
        "/loans",
        headers=admin,
        json={
            "origin_reservation_id": reserva.json()["id"],
            "due_at": fin.isoformat(),
            "use_mode": "RETIRO",
            "delivered_condition": "Bueno",
        },
    )
    assert entrega.status_code == 201, entrega.text
    despues = client.get("/reports/summary", headers=admin).json()
    assert despues["prestamos"] == antes["prestamos"] + 1
    assert despues["prestamos_por_estado"]["ACTIVO"] == 1
    assert despues["inventario_por_estado"] == {"PRESTADA": 1}
    assert despues["reservas_por_estado"] == {"ATENDIDA": 1}
    assert despues["unidades"] == antes["unidades"]


@pytest.mark.parametrize(
    ("estado", "horas", "clasificacion"),
    [
        (LoanState.ACTIVE, -1, "VENCIDO"),
        (LoanState.ACTIVE, 1, "ACTIVO"),
        (LoanState.ACTIVE, 0, "ACTIVO"),
        (LoanState.OVERDUE, -1, "VENCIDO"),
        (LoanState.RETURNED, -1, "DEVUELTO"),
    ],
)
def test_vencimiento_calculado_sin_cambiar_el_prestamo_ni_la_unidad(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    estado: LoanState,
    horas: int,
    clasificacion: str,
) -> None:
    instante = datetime.now(UTC)
    monkeypatch.setattr(reportes, "ahora", lambda: instante)
    with session_factory.begin() as sesion:
        administrador = sesion.scalar(
            select(Administrador.id).join(Account).where(Account.username == "admin")
        )
        sesion.add(
            Loan(
                applicant_id=int(flujo_basico["solicitante"]),
                administrator_id=administrador,
                unit_id=int(flujo_basico["unidad"]),
                starts_at=instante - timedelta(days=2),
                due_at=instante + timedelta(hours=horas),
                state=estado,
                use_mode=UseMode.TAKE_HOME,
                delivered_condition="Bueno",
                applied_policy={},
            )
        )
        unidad = sesion.get(PhysicalUnit, int(flujo_basico["unidad"]))
        assert unidad is not None
        unidad.state = UnitState.LOANED
    datos = client.get("/reports/summary", headers={"Authorization": flujo_basico["admin"]}).json()
    assert datos["prestamos"] == 1
    assert datos["prestamos_por_estado"][clasificacion] == 1
    assert sum(datos["prestamos_por_estado"].values()) == 1
    with session_factory() as sesion:
        assert sesion.scalar(select(Loan.state)) == estado
        assert sesion.scalar(select(PhysicalUnit.state)) == UnitState.LOANED


@pytest.mark.parametrize("accion", ["preview", "import"])
def test_importacion_csv_ya_no_esta_expuesta(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
    accion: str,
) -> None:
    ruta = f"/reports/catalog/{accion}"
    assert ruta not in client.get("/openapi.json").json()["paths"]
    with session_factory() as sesion:
        antes = [
            sesion.scalar(select(func.count()).select_from(modelo))
            for modelo in (ItemType, Category)
        ]
    respuesta = client.post(
        ruta,
        headers={"Authorization": flujo_basico["admin"]},
        json={
            "contenido": "tipo,categoria,descripcion\nAudio,Parlantes,Ejemplo\n",
        },
    )
    assert respuesta.status_code in (404, 405)
    with session_factory() as sesion:
        despues = [
            sesion.scalar(select(func.count()).select_from(modelo))
            for modelo in (ItemType, Category)
        ]
    assert despues == antes
