from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.infrastructure.models  # noqa: F401
import app.main as main
from app.application.basic_use_cases import create_person
from app.application.schemas import PersonCreate
from app.infrastructure import database
from app.infrastructure.database import Base
from app.infrastructure.models import ItemType


@pytest.fixture
def session_factory() -> Generator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def activar_claves_foraneas(conexion, _registro):  # type: ignore[no-untyped-def]
        conexion.execute("PRAGMA foreign_keys=ON")

    database.inicializar_base_datos(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with factory.begin() as sesion:
        sesion.add(ItemType(id=1, name="Tipo de prueba"))
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


@pytest.fixture
def flujo_basico(client: TestClient, session_factory: sessionmaker[Session]) -> dict[str, str]:
    """Prepara usuarios y catálogo con los mismos contratos que utiliza el navegador."""
    from datetime import date

    from app.infrastructure.models import Person

    with session_factory.begin() as sesion:
        create_person(
            sesion,
            PersonCreate(
                document_type="DNI",
                document_number="87654321",
                first_names="Ana",
                last_names="Administradora",
                institutional_email="admin@example.test",
                role="PERSONAL_ADMINISTRATIVO",
                is_admin=True,
                school_affiliation="EPCC",
                start_date=date.today(),
                username="admin",
                password="clave-administrativa-prueba",
            ),
            None,
        )
    login = client.post(
        "/auth/token", data={"username": "admin", "password": "clave-administrativa-prueba"}
    )
    assert login.status_code == 200, login.text
    admin = "Bearer " + login.json()["access_token"]
    encabezado = {"Authorization": admin}

    def crear(ruta: str, datos: dict) -> dict:  # type: ignore[type-arg]
        respuesta = client.post(ruta, headers=encabezado, json=datos)
        assert respuesta.status_code == 201, respuesta.text
        return respuesta.json()

    tipo = crear("/inventory/types", {"name": "Informática"})
    categoria = crear("/inventory/categories", {"name": "Portátiles", "item_type_id": tipo["id"]})
    ficha = crear(
        "/inventory/items",
        {"name": "Laptop", "category_id": categoria["id"], "attributes": {"RAM": "8GB"}},
    )
    unidad = crear(
        "/inventory/units",
        {
            "item_card_id": ficha["id"],
            "inventory_code": "EPCC-001",
            "serial_number": "SERIE-001",
            "location": "Laboratorio",
            "custody": "EPCC",
            "condition": "Operativa",
        },
    )
    estudiante = crear(
        "/people",
        {
            "cui": "20260001",
            "document_type": "DNI",
            "document_number": "11223344",
            "first_names": "Luis",
            "last_names": "Estudiante",
            "institutional_email": "estudiante@example.test",
            "role": "ESTUDIANTE",
            "school_affiliation": "EPCC",
            "start_date": str(date.today()),
            "username": "estudiante",
            "password": "clave-estudiantil-prueba",
            "student_code": "20260001",
            "program": "Ciencia de la Computación",
            "semester": 5,
        },
    )
    login = client.post(
        "/auth/token", data={"username": "estudiante", "password": "clave-estudiantil-prueba"}
    )
    assert login.status_code == 200, login.text
    with session_factory() as sesion:
        persona = sesion.get(Person, int(estudiante["id"]))
        assert persona is not None and persona.applicant is not None
        solicitante = str(persona.applicant.id)
    return {
        "admin": admin,
        "estudiante": "Bearer " + login.json()["access_token"],
        "unidad": unidad["id"],
        "tipo": tipo["id"],
        "categoria": categoria["id"],
        "ficha": ficha["id"],
        "persona": estudiante["id"],
        "solicitante": solicitante,
    }
