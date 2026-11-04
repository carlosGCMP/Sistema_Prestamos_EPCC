"""La entrega demo es repetible y nunca requiere la base real del desarrollador."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    Table,
    create_engine,
    event,
    func,
    inspect,
    select,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main
from app import cargar_demo
from app.application.basic_use_cases import create_person
from app.application.datos_demo import CLAVE_ADMIN_DEMO, CLAVE_DEMO, USUARIOS_DEMO
from app.application.schemas import PersonCreate
from app.core.security import verify_password
from app.core.settings import Settings
from app.infrastructure import database
from app.infrastructure.database import inicializar_base_datos
from app.infrastructure.modelos_sql import (
    DevolucionDelPrestamo,
    EntregaDelPrestamo,
    MatriculaRealizada,
    PrestamoAprobadoDeReserva,
    RegistroBienesFisicosPrestamo,
    RegistroDeReserva,
    SemestreAcademico,
)
from app.infrastructure.models import (
    AcademicRecord,
    Account,
    AuditEvent,
    ItemType,
    Loan,
    LoanPolicy,
    LoanState,
    Person,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    UnitState,
)
from app.infrastructure.seguridad_demo import ACCION_DEMO, CargaDemoRechazada


@pytest.fixture
def motor_demo() -> Iterator[Engine]:
    motor = create_engine(
        "sqlite+pysqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(motor, "connect")
    def activar_claves(conexion, _registro):  # type: ignore[no-untyped-def]
        conexion.execute("PRAGMA foreign_keys=ON")

    try:
        yield motor
    finally:
        motor.dispose()


def foto(motor: Engine) -> dict:
    tablas = MetaData()
    tablas.reflect(bind=motor)
    with motor.connect() as conexion:
        return {
            t.name: list(conexion.execute(select(t)).mappings()) for t in tablas.tables.values()
        }


def test_carga_completa_con_relaciones_fechas_y_claves_seguras(motor_demo: Engine) -> None:
    antes = datetime.now(UTC)
    assert cargar_demo.cargar_demo(motor_demo) is True
    assert len(inspect(motor_demo).get_table_names()) == 45
    with Session(motor_demo) as sesion:
        cantidades = {
            Person: 4,
            Account: 4,
            ItemType: 2,
            PhysicalUnit: 6,
            LoanPolicy: 4,
            Reservation: 5,
            Loan: 2,
            RegistroDeReserva: 4,
            PrestamoAprobadoDeReserva: 2,
            EntregaDelPrestamo: 2,
            RegistroBienesFisicosPrestamo: 2,
            DevolucionDelPrestamo: 1,
            SemestreAcademico: 1,
            AcademicRecord: 2,
            MatriculaRealizada: 2,
        }
        for modelo, cantidad in cantidades.items():
            assert sesion.scalar(select(func.count()).select_from(modelo)) == cantidad
        cuentas = list(sesion.scalars(select(Account)))
        assert {c.username for c in cuentas} == set(USUARIOS_DEMO)
        assert USUARIOS_DEMO[0] == "admin"
        assert CLAVE_ADMIN_DEMO == "contra123456"
        for cuenta in cuentas:
            clave = CLAVE_ADMIN_DEMO if cuenta.username == "admin" else CLAVE_DEMO
            assert cuenta.password_hash != clave and verify_password(clave, cuenta.password_hash)
        assert len({c.password_hash for c in cuentas}) == 4
        assert sum(c.person.is_admin for c in cuentas) == 1
        assert {p.max_duration for p in sesion.scalars(select(LoanPolicy))} == {3, 7}
        assert {p.state for p in sesion.scalars(select(Loan))} == {
            LoanState.ACTIVE,
            LoanState.RETURNED,
        }
        for reserva in sesion.scalars(select(Reservation)):
            assert reserva.ends_at > antes
            assert reserva.starts_at.tzinfo is not None
            assert reserva.ends_at - reserva.starts_at <= timedelta(days=7)
        lista = sesion.scalar(
            select(Reservation)
            .join(PhysicalUnit)
            .where(
                PhysicalUnit.inventory_code == "DEMO-LAP-002",
            )
        )
        assert lista is not None and lista.state == ReservationState.CONFIRMED
        assert lista.starts_at <= datetime.now(UTC) < lista.ends_at


@pytest.mark.parametrize("inicializada", [False, True])
def test_segunda_carga_no_duplica_ni_reescribe(motor_demo: Engine, inicializada: bool) -> None:
    if inicializada:
        inicializar_base_datos(motor_demo)
    cargar_demo.cargar_demo(motor_demo)
    original = foto(motor_demo)
    assert cargar_demo.cargar_demo(motor_demo) is False
    assert foto(motor_demo) == original


@pytest.mark.parametrize("solo_inventario", [False, True])
def test_rechaza_datos_previos_sin_sembrar_politicas_ni_cambiar_filas(
    motor_demo: Engine,
    solo_inventario: bool,
) -> None:
    inicializar_base_datos(motor_demo)
    with Session(motor_demo) as sesion, sesion.begin():
        if solo_inventario:
            sesion.add(ItemType(name="Inventario anterior"))
        else:
            create_person(
                sesion,
                PersonCreate(
                    document_type="DNI",
                    document_number="87654321",
                    first_names="Persona",
                    last_names="Existente",
                    institutional_email="persona@example.test",
                    role=Role.ADMINISTRATIVE,
                    is_admin=True,
                    school_affiliation="EPCC",
                    start_date=datetime.now(UTC).date(),
                    username="admin",
                    password="clave-real-no-tocar",
                ),
                None,
            )
    original = foto(motor_demo)
    with pytest.raises(CargaDemoRechazada, match="datos previos"):
        cargar_demo.cargar_demo(motor_demo)
    assert foto(motor_demo) == original


def test_rechaza_esquemas_ajenos_antes_de_crear_tablas(motor_demo: Engine) -> None:
    tabla = Table("datos_anteriores", MetaData(), Column("id", Integer, primary_key=True))
    tabla.create(motor_demo)
    with motor_demo.begin() as conexion:
        conexion.execute(tabla.insert().values(id=1))
    with pytest.raises(CargaDemoRechazada):
        cargar_demo.cargar_demo(motor_demo)
    assert inspect(motor_demo).get_table_names() == ["datos_anteriores"]
    assert foto(motor_demo) == {"datos_anteriores": [{"id": 1}]}


def test_version_anterior_no_cambia_cuentas_existentes(motor_demo: Engine) -> None:
    cargar_demo.cargar_demo(motor_demo)
    with Session(motor_demo) as sesion, sesion.begin():
        marca = sesion.scalar(select(AuditEvent).where(AuditEvent.action == ACCION_DEMO))
        assert marca is not None
        marca.entity_id = "epcc-demo-v1"
    original = foto(motor_demo)
    with pytest.raises(CargaDemoRechazada):
        cargar_demo.cargar_demo(motor_demo)
    assert foto(motor_demo) == original


@pytest.mark.parametrize("alteracion", ["nueva_persona", "editar_persona", "marca_invalida"])
def test_rechaza_demo_alterada_sin_restaurar_ni_borrar(
    motor_demo: Engine,
    alteracion: str,
) -> None:
    cargar_demo.cargar_demo(motor_demo)
    with Session(motor_demo) as sesion, sesion.begin():
        if alteracion == "nueva_persona":
            sesion.add(
                Person(
                    first_names="Otra",
                    last_names="Persona",
                    document_type="DNI",
                    document_number="12345678",
                    institutional_email="otra@example.test",
                    role=Role.ADMINISTRATIVE,
                    school_affiliation="EPCC",
                    start_date=datetime.now(UTC).date(),
                )
            )
        elif alteracion == "editar_persona":
            persona = sesion.scalar(select(Person))
            assert persona is not None
            persona.first_names = "Datos modificados"
        else:
            marca = sesion.scalar(select(AuditEvent).where(AuditEvent.action == ACCION_DEMO))
            assert marca is not None
            marca.description = "no es JSON"
    original = foto(motor_demo)
    with pytest.raises(CargaDemoRechazada):
        cargar_demo.cargar_demo(motor_demo)
    assert foto(motor_demo) == original


def test_error_revierte_la_carga_completa(
    motor_demo: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    crear = cargar_demo.crear_datos

    def fallar(sesion: Session) -> None:
        crear(sesion)
        raise RuntimeError("Fallo simulado después de crear los datos")

    monkeypatch.setattr(cargar_demo, "crear_datos", fallar)
    with pytest.raises(RuntimeError):
        cargar_demo.cargar_demo(motor_demo)
    assert all(not filas for filas in foto(motor_demo).values())
    monkeypatch.setattr(cargar_demo, "crear_datos", crear)
    assert cargar_demo.cargar_demo(motor_demo) is True


def test_datos_utilizables_desde_la_api(
    motor_demo: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    cargar_demo.cargar_demo(motor_demo)
    fabrica = sessionmaker(bind=motor_demo, expire_on_commit=False, autoflush=False)
    monkeypatch.setattr(database, "crear_sesion", fabrica)
    monkeypatch.setattr(main, "inicializar_base_datos", lambda: inicializar_base_datos(motor_demo))
    with TestClient(main.app) as client:
        tokens = {}
        for usuario in USUARIOS_DEMO:
            clave = CLAVE_ADMIN_DEMO if usuario == "admin" else CLAVE_DEMO
            login = client.post("/auth/token", data={"username": usuario, "password": clave})
            assert login.status_code == 200, login.text
            tokens[usuario] = {"Authorization": "Bearer " + login.json()["access_token"]}
        assert (
            client.post(
                "/auth/token",
                data={
                    "username": "admin",
                    "password": CLAVE_DEMO,
                },
            ).status_code
            == 401
        )
        assert (
            client.post(
                "/auth/token",
                data={
                    "username": "demo_admin",
                    "password": CLAVE_ADMIN_DEMO,
                },
            ).status_code
            == 401
        )
        # Iniciar sesión no invalida la marca ni vuelve a escribir los datos.
        assert cargar_demo.cargar_demo(motor_demo) is False
        admin = tokens["admin"]
        estudiante = tokens["demo_estudiante1"]
        assert len(client.get("/loans", headers=admin).json()) == 2
        assert len(client.get("/loans", headers=estudiante).json()) == 1
        assert len(client.get("/academic/enrollments", headers=admin).json()) == 2
        assert client.get("/academic/enrollments", headers=estudiante).status_code == 403
        unidades = client.get("/inventory/units", headers=admin).json()
        unidad = next(u for u in unidades if u["inventory_code"] == "DEMO-LAP-002")
        reservas = client.get("/reservations", headers=admin).json()
        reserva = next(r for r in reservas if r["unit_id"] == unidad["id"])
        entrega = client.post(
            "/loans",
            headers=admin,
            json={
                "origin_reservation_id": reserva["id"],
                "due_at": reserva["ends_at"],
                "use_mode": "RETIRO",
                "delivered_condition": "Bueno",
            },
        )
        assert entrega.status_code == 201, entrega.text
        retorno = client.post(
            f"/loans/{entrega.json()['id']}/return",
            headers=admin,
            json={"condition": "Bueno", "disposition": UnitState.AVAILABLE},
        )
        assert retorno.status_code == 200, retorno.text


def test_no_se_permite_en_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    conectar = Mock()
    monkeypatch.setattr(cargar_demo, "obtener_motor", conectar)
    monkeypatch.setattr(cargar_demo, "get_settings", lambda: Settings(app_env="production"))
    with pytest.raises(SystemExit, match="APP_ENV=development"):
        cargar_demo.main()
    conectar.assert_not_called()


def test_comando_informa_sin_mostrar_secretos(
    motor_demo: Engine,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cargar_demo, "obtener_motor", lambda: motor_demo)
    monkeypatch.setattr(cargar_demo, "get_settings", lambda: Settings(app_env="development"))
    cargar_demo.main()
    salida = capsys.readouterr().out
    assert "Datos de demostración creados" in salida
    assert "docs/datos-demo.md" in salida
    assert CLAVE_DEMO not in salida
    assert CLAVE_ADMIN_DEMO not in salida
