"""Reglas acordadas y recorridos completos de los tres módulos habilitados."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.application import basic_use_cases, politicas, prestamos
from app.infrastructure.database import inicializar_base_datos
from app.infrastructure.modelos_sql import (
    DevolucionDelPrestamo,
    EntregaDelPrestamo,
    PrestamoAprobadoDeReserva,
    RegistroBienesFisicosPrestamo,
    ReglasDelPrestamo,
    VersionDeLaPolitica,
)
from app.infrastructure.models import AcademicRecord, Category, ItemType, LoanPolicy


def encabezado(flujo: dict[str, str], rol: str = "admin") -> dict[str, str]:
    return {"Authorization": flujo[rol]}


def publicar(client: TestClient, flujo: dict[str, str], **cambios):  # type: ignore[no-untyped-def]
    datos = {
        "name": "Política de prueba",
        "role": "ESTUDIANTE",
        "item_type_id": flujo["tipo"],
        "max_duration": 3,
        "max_units": 2,
        **cambios,
    }
    return client.post("/policies", headers=encabezado(flujo), json=datos)


def unidad_adicional(client: TestClient, flujo: dict[str, str], numero: int) -> str:
    ficha = client.post(
        "/inventory/items",
        headers=encabezado(flujo),
        json={
            "name": f"Laptop {numero}",
            "category_id": flujo["categoria"],
        },
    )
    assert ficha.status_code == 201, ficha.text
    unidad = client.post(
        "/inventory/units",
        headers=encabezado(flujo),
        json={
            "item_card_id": ficha.json()["id"],
            "inventory_code": f"EPCC-{numero}",
            "serial_number": f"SERIE-{numero}",
            "location": "EPCC",
            "custody": "EPCC",
            "condition": "Bueno",
        },
    )
    assert unidad.status_code == 201, unidad.text
    return unidad.json()["id"]


def reservar(
    client: TestClient,
    flujo: dict[str, str],
    inicio: datetime,
    duracion: timedelta = timedelta(days=2),
    unidad: str | None = None,
    solicitante: str = "estudiante",
):
    return client.post(
        "/reservations",
        headers=encabezado(flujo, solicitante),
        json={
            "unit_id": unidad or flujo["unidad"],
            "starts_at": inicio.isoformat(),
            "ends_at": (inicio + duracion).isoformat(),
            "intended_use": "Prueba de políticas",
        },
    )


def confirmar(client: TestClient, flujo: dict[str, str], identificador: str):
    return client.post(
        f"/reservations/{identificador}/decision", headers=encabezado(flujo), json={"confirm": True}
    )


def mover_reloj(monkeypatch: pytest.MonkeyPatch, fecha: datetime) -> None:
    for modulo in (basic_use_cases, politicas, prestamos):
        monkeypatch.setattr(modulo, "ahora", lambda: fecha)


def crear_docente(
    client: TestClient, flujo: dict[str, str], *, administrador: bool = False
) -> None:
    respuesta = client.post(
        "/people",
        headers=encabezado(flujo),
        json={
            "document_type": "DNI",
            "document_number": "22222222",
            "first_names": "Docente",
            "last_names": "De prueba",
            "institutional_email": "docente@example.test",
            "role": "DOCENTE",
            "school_affiliation": "EPCC",
            "start_date": "2026-01-01",
            "username": "docente",
            "password": "clave-docente-de-prueba",
            "teacher_code": "DOC-01",
            "specialty": "Computación",
            "is_admin": administrador,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    login = client.post(
        "/auth/token", data={"username": "docente", "password": "clave-docente-de-prueba"}
    )
    assert login.status_code == 200, login.text
    flujo["docente"] = "Bearer " + login.json()["access_token"]


def test_politicas_iniciales_y_arranque_idempotente(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    filas = client.get("/policies", headers=encabezado(flujo_basico, "estudiante")).json()
    actuales = [fila for fila in filas if fila["item_type_id"] == flujo_basico["tipo"]]
    assert {fila["role"]: fila["max_duration"] for fila in actuales} == {
        "ESTUDIANTE": 3,
        "DOCENTE": 7,
    }
    assert all(fila["max_units"] == 2 for fila in actuales)
    motor = session_factory.kw["bind"]
    inicializar_base_datos(motor)
    assert client.get("/policies", headers=encabezado(flujo_basico)).json() == filas


@pytest.mark.parametrize("cantidad,permitido", [(1, True), (0, False)])
def test_reglas_manuales_previas_se_conservan_al_crear_la_primera_version(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
    cantidad: int,
    permitido: bool,
) -> None:
    with session_factory.begin() as sesion:
        tipo = ItemType(name="Tipo con regla manual")
        sesion.add(tipo)
        sesion.flush()
        identificador = tipo.id
        sesion.add(
            ReglasDelPrestamo(
                id_tipo_bien=identificador,
                tipo_solicitante="ESTUDIANTE",
                cantidad_maxima_prestamos=cantidad,
                cantidad_maxima_bienes=cantidad,
                permitido=True,
            )
        )
    inicializar_base_datos(session_factory.kw["bind"])
    filas = client.get("/policies", headers=encabezado(flujo_basico)).json()
    politica = next(
        fila
        for fila in filas
        if fila["item_type_id"] == str(identificador) and fila["role"] == "ESTUDIANTE"
    )
    assert politica["max_units"] == 1
    assert politica["permitted"] is permitido
    with session_factory() as sesion:
        regla = sesion.scalar(
            select(ReglasDelPrestamo).where(
                ReglasDelPrestamo.id_tipo_bien == identificador,
                ReglasDelPrestamo.tipo_solicitante == "ESTUDIANTE",
            )
        )
        assert regla is not None and regla.cantidad_maxima_bienes == cantidad


@pytest.mark.parametrize(
    "cambio",
    [
        {"max_duration": 4},
        {"role": "DOCENTE", "max_duration": 8},
        {"max_units": 3},
        {"role": "PERSONAL_ADMINISTRATIVO"},
        {"duration_unit": "HORAS"},
        {"fine_per_day": "1.00"},
        {"max_duration": 0},
    ],
)
def test_publicacion_no_puede_exceder_lo_acordado(
    client: TestClient, flujo_basico: dict[str, str], cambio: dict
) -> None:
    assert publicar(client, flujo_basico, **cambio).status_code == 422


def test_publicacion_restringida_e_historial_conservado(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    datos = {
        "name": "Prohibida",
        "role": "ESTUDIANTE",
        "item_type_id": flujo_basico["tipo"],
        "max_duration": 3,
    }
    assert (
        client.post(
            "/policies", headers=encabezado(flujo_basico, "estudiante"), json=datos
        ).status_code
        == 403
    )
    respuesta = publicar(client, flujo_basico, max_units=1, max_duration=2)
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["version"] == 2
    with session_factory() as sesion:
        reglas = sesion.scalar(
            select(ReglasDelPrestamo).where(
                ReglasDelPrestamo.id_tipo_bien == int(flujo_basico["tipo"]),
                ReglasDelPrestamo.tipo_solicitante == "ESTUDIANTE",
            )
        )
        assert reglas is not None and reglas.cantidad_maxima_bienes == 1
        assert sesion.scalar(select(func.count()).select_from(VersionDeLaPolitica)) >= 3
    historia = client.get(
        f"/policies/{respuesta.json()['id']}/history", headers=encabezado(flujo_basico)
    )
    assert historia.status_code == 200 and len(historia.json()) == 1


def test_version_futura_no_desactiva_antes_la_anterior(
    client: TestClient, flujo_basico: dict[str, str]
) -> None:
    futuro = datetime.now(UTC) + timedelta(days=2)
    respuesta = publicar(client, flujo_basico, permitted=False, valid_from=futuro.isoformat())
    assert respuesta.status_code == 201 and respuesta.json()["status"] == "PROGRAMADA"
    assert (
        reservar(client, flujo_basico, futuro - timedelta(days=1), timedelta(hours=2)).status_code
        == 201
    )
    assert (
        reservar(client, flujo_basico, futuro + timedelta(days=1), timedelta(hours=2)).status_code
        == 403
    )


def test_no_se_reactivan_politicas_modificadas_al_reiniciar(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    assert publicar(client, flujo_basico, permitted=False).status_code == 201
    inicializar_base_datos(session_factory.kw["bind"])
    assert reservar(client, flujo_basico, datetime.now(UTC) + timedelta(days=1)).status_code == 403


@pytest.mark.parametrize("dias,esperado", [(3, 201), (3.01, 422)])
def test_limite_estudiantes(
    client: TestClient, flujo_basico: dict[str, str], dias: float, esperado: int
) -> None:
    assert (
        reservar(
            client, flujo_basico, datetime.now(UTC) + timedelta(days=1), timedelta(days=dias)
        ).status_code
        == esperado
    )


@pytest.mark.parametrize("dias,esperado", [(7, 201), (7.01, 422)])
def test_limite_docentes(
    client: TestClient, flujo_basico: dict[str, str], dias: float, esperado: int
) -> None:
    crear_docente(client, flujo_basico)
    assert (
        reservar(
            client,
            flujo_basico,
            datetime.now(UTC) + timedelta(days=1),
            timedelta(days=dias),
            solicitante="docente",
        ).status_code
        == esperado
    )


def test_no_autoconfirmacion(client: TestClient, flujo_basico: dict[str, str]) -> None:
    crear_docente(client, flujo_basico, administrador=True)
    reserva = reservar(
        client, flujo_basico, datetime.now(UTC) + timedelta(days=1), solicitante="docente"
    )
    assert reserva.status_code == 201
    respuesta = client.post(
        f"/reservations/{reserva.json()['id']}/decision",
        headers=encabezado(flujo_basico, "docente"),
        json={"confirm": True},
    )
    assert respuesta.status_code == 403
    assert confirmar(client, flujo_basico, reserva.json()["id"]).status_code == 200


def test_cupo_de_dos_y_pendientes_no_consumen_cupo(
    client: TestClient, flujo_basico: dict[str, str]
) -> None:
    inicio = datetime.now(UTC) + timedelta(days=1)
    unidades = [
        flujo_basico["unidad"],
        unidad_adicional(client, flujo_basico, 2),
        unidad_adicional(client, flujo_basico, 3),
    ]
    solicitudes = [reservar(client, flujo_basico, inicio, unidad=unidad) for unidad in unidades]
    assert all(respuesta.status_code == 201 for respuesta in solicitudes)
    assert confirmar(client, flujo_basico, solicitudes[0].json()["id"]).status_code == 200
    assert confirmar(client, flujo_basico, solicitudes[1].json()["id"]).status_code == 200
    assert confirmar(client, flujo_basico, solicitudes[2].json()["id"]).status_code == 409


def test_cancelacion_titular_antes_y_admin_con_motivo(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inicio = datetime.now(UTC) + timedelta(minutes=5)
    reserva = reservar(client, flujo_basico, inicio)
    assert reserva.status_code == 201
    identificador = reserva.json()["id"]
    mover_reloj(monkeypatch, inicio + timedelta(minutes=1))
    assert (
        client.post(
            f"/reservations/{identificador}/cancel", headers=encabezado(flujo_basico, "estudiante")
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/reservations/{identificador}/cancel", headers=encabezado(flujo_basico)
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/reservations/{identificador}/cancel",
            headers=encabezado(flujo_basico),
            params={"reason": "Mantenimiento"},
        ).status_code
        == 200
    )


def test_entrega_devolucion_y_trazabilidad_completas(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inicio = datetime.now(UTC) + timedelta(minutes=5)
    reserva = reservar(client, flujo_basico, inicio, timedelta(hours=2))
    assert reserva.status_code == 201
    assert confirmar(client, flujo_basico, reserva.json()["id"]).status_code == 200
    # Un cambio posterior no invalida una confirmación ya concedida.
    assert publicar(client, flujo_basico, permitted=False).status_code == 201
    mover_reloj(monkeypatch, inicio + timedelta(minutes=1))
    datos = {
        "origin_reservation_id": reserva.json()["id"],
        "due_at": (inicio + timedelta(hours=1)).isoformat(),
        "use_mode": "RETIRO",
        "delivered_condition": "Bueno",
        "delivered_accessories": ["Cargador"],
    }
    assert (
        client.post(
            "/loans", headers=encabezado(flujo_basico, "estudiante"), json=datos
        ).status_code
        == 403
    )
    entrega = client.post("/loans", headers=encabezado(flujo_basico), json=datos)
    assert entrega.status_code == 201, entrega.text
    assert entrega.json()["applied_policy"]["version"] == 1
    assert client.post("/loans", headers=encabezado(flujo_basico), json=datos).status_code == 409
    assert (
        client.get("/loans", headers=encabezado(flujo_basico, "estudiante")).json()[0]["id"]
        == entrega.json()["id"]
    )
    with session_factory() as sesion:
        for modelo in (
            PrestamoAprobadoDeReserva,
            EntregaDelPrestamo,
            RegistroBienesFisicosPrestamo,
        ):
            assert sesion.scalar(select(func.count()).select_from(modelo)) == 1
    mover_reloj(monkeypatch, inicio + timedelta(hours=1, minutes=2))
    assert client.get("/loans", headers=encabezado(flujo_basico)).json()[0]["state"] == "VENCIDO"
    retorno = {"condition": "Bueno", "accessories": ["Cargador"], "disposition": "DISPONIBLE"}
    devuelto = client.post(
        f"/loans/{entrega.json()['id']}/return", headers=encabezado(flujo_basico), json=retorno
    )
    assert devuelto.status_code == 200, devuelto.text
    assert devuelto.json()["state"] == "DEVUELTO"
    assert (
        client.post(
            f"/loans/{entrega.json()['id']}/return", headers=encabezado(flujo_basico), json=retorno
        ).status_code
        == 409
    )
    with session_factory() as sesion:
        assert sesion.scalar(select(func.count()).select_from(DevolucionDelPrestamo)) == 1
    assert (
        client.get("/inventory/units", headers=encabezado(flujo_basico)).json()[0]["state"]
        == "DISPONIBLE"
    )


def test_no_entregar_reserva_futura_o_pendiente(
    client: TestClient, flujo_basico: dict[str, str]
) -> None:
    inicio = datetime.now(UTC) + timedelta(days=1)
    reserva = reservar(client, flujo_basico, inicio)
    datos = {
        "origin_reservation_id": reserva.json()["id"],
        "due_at": (inicio + timedelta(hours=1)).isoformat(),
        "use_mode": "RETIRO",
        "delivered_condition": "Bueno",
    }
    assert client.post("/loans", headers=encabezado(flujo_basico), json=datos).status_code == 409
    assert confirmar(client, flujo_basico, reserva.json()["id"]).status_code == 200
    assert client.post("/loans", headers=encabezado(flujo_basico), json=datos).status_code == 409


def test_academico_guardar_actualizar_matricular_y_permisos(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    assert (
        client.get("/academic/students", headers=encabezado(flujo_basico, "estudiante")).status_code
        == 403
    )
    periodo = client.post(
        "/academic/terms",
        headers=encabezado(flujo_basico),
        json={
            "nombre_semestre": "2026-II",
            "fecha_inicio": "2026-08-01",
            "fecha_fin": "2026-12-31",
        },
    )
    assert periodo.status_code == 201, periodo.text
    datos = {
        "persona_id": flujo_basico["persona"],
        "situacion": "MATRICULADO",
        "periodo": "2026-II",
        "promedio_acumulado": "15.50",
        "creditos_aprobados": 100,
        "creditos_reprobados": 0,
        "creditos_cursando": 20,
    }
    registro = client.post("/academic/records", headers=encabezado(flujo_basico), json=datos)
    assert registro.status_code == 200, registro.text
    nuevo = client.post(
        "/academic/records",
        headers=encabezado(flujo_basico),
        json={**datos, "creditos_aprobados": 120},
    )
    assert nuevo.status_code == 200 and nuevo.json()["id"] == registro.json()["id"]
    with session_factory() as sesion:
        assert sesion.scalar(select(func.count()).select_from(AcademicRecord)) == 1
    matricula = {
        "persona_id": flujo_basico["persona"],
        "id_semestre": periodo.json()["id_semestre"],
    }
    assert (
        client.post(
            "/academic/enrollments", headers=encabezado(flujo_basico), json=matricula
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/academic/enrollments", headers=encabezado(flujo_basico), json=matricula
        ).status_code
        == 409
    )
    assert len(client.get("/academic/enrollments", headers=encabezado(flujo_basico)).json()) == 1


def test_validacion_no_devuelve_contrasena(
    client: TestClient, flujo_basico: dict[str, str]
) -> None:
    secreto = "no-debe-aparecer-en-respuesta"
    respuesta = client.post("/people", headers=encabezado(flujo_basico), json={"password": secreto})
    assert respuesta.status_code == 422
    assert secreto not in respuesta.text
    assert all("input" not in error and "ctx" not in error for error in respuesta.json()["detail"])


def preparar_entrega(
    client: TestClient, flujo: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> tuple[str, datetime]:
    inicio = datetime.now(UTC) + timedelta(minutes=5)
    reserva = reservar(client, flujo, inicio, timedelta(hours=2))
    assert reserva.status_code == 201, reserva.text
    assert confirmar(client, flujo, reserva.json()["id"]).status_code == 200
    mover_reloj(monkeypatch, inicio + timedelta(minutes=1))
    entrega = client.post(
        "/loans",
        headers=encabezado(flujo),
        json={
            "origin_reservation_id": reserva.json()["id"],
            "due_at": (inicio + timedelta(hours=1)).isoformat(),
            "use_mode": "RETIRO",
            "delivered_condition": "Bueno",
        },
    )
    assert entrega.status_code == 201, entrega.text
    return entrega.json()["id"], inicio


def test_prestamos_privados_y_devolucion_de_persona_inactiva(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identificador, _ = preparar_entrega(client, flujo_basico, monkeypatch)
    crear_docente(client, flujo_basico)
    assert client.get("/loans", headers=encabezado(flujo_basico, "docente")).json() == []
    assert len(client.get("/loans", headers=encabezado(flujo_basico, "estudiante")).json()) == 1
    respuesta = client.post(
        f"/people/{flujo_basico['persona']}/deactivate",
        headers=encabezado(flujo_basico),
    )
    assert respuesta.status_code == 200
    retorno = client.post(
        f"/loans/{identificador}/return",
        headers=encabezado(flujo_basico),
        json={"condition": "Bueno", "disposition": "MANTENIMIENTO"},
    )
    assert retorno.status_code == 200, retorno.text
    assert (
        client.get("/inventory/units", headers=encabezado(flujo_basico)).json()[0]["state"]
        == "MANTENIMIENTO"
    )


@pytest.mark.parametrize(
    "cambio",
    [
        {"disposition": "PRESTADA"},
        {"returned_at": "2000-01-01T00:00:00+00:00"},
        {"returned_at": "2099-01-01T00:00:00+00:00"},
        {"returned_at": "2026-01-01T00:00:00"},
    ],
)
def test_devolucion_invalida_no_cierra_el_prestamo(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
    cambio: dict,
) -> None:
    identificador, _ = preparar_entrega(client, flujo_basico, monkeypatch)
    respuesta = client.post(
        f"/loans/{identificador}/return",
        headers=encabezado(flujo_basico),
        json={"condition": "Bueno", **cambio},
    )
    assert respuesta.status_code == 422, respuesta.text
    assert client.get("/loans", headers=encabezado(flujo_basico)).json()[0]["state"] == "ACTIVO"
    assert (
        client.get("/inventory/units", headers=encabezado(flujo_basico)).json()[0]["state"]
        == "PRESTADA"
    )


def test_prestamo_vencido_mas_reserva_ocupan_el_cupo(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, inicio = preparar_entrega(client, flujo_basico, monkeypatch)
    mover_reloj(monkeypatch, inicio + timedelta(hours=3))
    futuro = inicio + timedelta(days=1)
    segunda = unidad_adicional(client, flujo_basico, 2)
    tercera = unidad_adicional(client, flujo_basico, 3)
    reserva = reservar(client, flujo_basico, futuro, timedelta(hours=1), unidad=segunda)
    assert reserva.status_code == 201, reserva.text
    assert confirmar(client, flujo_basico, reserva.json()["id"]).status_code == 200
    # El préstamo vencido sigue abierto y la reserva confirmada ocupa el otro cupo.
    assert (
        reservar(client, flujo_basico, futuro, timedelta(hours=1), unidad=tercera).status_code
        == 409
    )


def test_cruces_y_limite_se_revisan_al_confirmar(
    client: TestClient,
    flujo_basico: dict[str, str],
) -> None:
    inicio = datetime.now(UTC) + timedelta(days=1)
    primera = reservar(client, flujo_basico, inicio, timedelta(hours=2))
    cruzada = reservar(client, flujo_basico, inicio + timedelta(hours=1), timedelta(hours=2))
    assert primera.status_code == cruzada.status_code == 201
    assert confirmar(client, flujo_basico, primera.json()["id"]).status_code == 200
    assert confirmar(client, flujo_basico, cruzada.json()["id"]).status_code == 409
    consecutiva = reservar(client, flujo_basico, inicio + timedelta(hours=2), timedelta(hours=2))
    assert consecutiva.status_code == 201, consecutiva.text
    assert confirmar(client, flujo_basico, consecutiva.json()["id"]).status_code == 200


def test_categoria_inactiva_y_politica_vencida_no_se_eluden(
    client: TestClient,
    flujo_basico: dict[str, str],
    session_factory: sessionmaker[Session],
) -> None:
    inicio = datetime.now(UTC) + timedelta(days=1)
    with session_factory.begin() as sesion:
        categoria = sesion.get(Category, int(flujo_basico["categoria"]))
        assert categoria is not None
        categoria.active = False
    assert reservar(client, flujo_basico, inicio).status_code == 409
    with session_factory.begin() as sesion:
        categoria = sesion.get(Category, int(flujo_basico["categoria"]))
        assert categoria is not None
        categoria.active = True
        for politica in sesion.scalars(select(LoanPolicy)):
            politica.valid_until = datetime.now(UTC)
    inicializar_base_datos(session_factory.kw["bind"])
    assert reservar(client, flujo_basico, inicio).status_code == 409


def test_entrega_no_puede_extender_el_horario_confirmado(
    client: TestClient,
    flujo_basico: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inicio = datetime.now(UTC) + timedelta(minutes=5)
    reserva = reservar(client, flujo_basico, inicio, timedelta(hours=1))
    assert confirmar(client, flujo_basico, reserva.json()["id"]).status_code == 200
    mover_reloj(monkeypatch, inicio + timedelta(minutes=1))
    respuesta = client.post(
        "/loans",
        headers=encabezado(flujo_basico),
        json={
            "origin_reservation_id": reserva.json()["id"],
            "due_at": (inicio + timedelta(hours=2)).isoformat(),
            "use_mode": "RETIRO",
            "delivered_condition": "Bueno",
        },
    )
    assert respuesta.status_code == 422
    assert client.get("/loans", headers=encabezado(flujo_basico)).json() == []
