"""El esquema completo debe respetar los nombres y relaciones de los SQL protegidos."""

import re
from pathlib import Path

import pytest
from sqlalchemy import BigInteger, create_engine, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.schemas import PersonOut
from app.infrastructure.database import Base, inicializar_base_datos
from app.infrastructure.modelos_sql import EstadoDeLaReserva
from app.infrastructure.models import Category, PersonState, Role


def test_todos_los_sql_tienen_modelo() -> None:
    nombres = set()
    for ruta in (Path(__file__).resolve().parents[1] / "base de datos").rglob("*.sql"):
        nombres.update(re.findall(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)", ruta.read_text()))
    assert set(Base.metadata.tables) == nombres | {"bien", "prestamo"}
    assert len(Base.metadata.tables) == 45


def test_identificadores_bigint_y_referencias_validas() -> None:
    for tabla in Base.metadata.tables.values():
        for columna in tabla.primary_key:
            assert isinstance(columna.type, BigInteger), (tabla.name, columna.name)
        for clave in tabla.foreign_keys:
            assert clave.column.table.name in Base.metadata.tables
    assert "accounts" not in Base.metadata.tables
    assert "reservations" not in Base.metadata.tables


def test_identificadores_no_pierden_precision_en_json() -> None:
    salida = PersonOut(
        id=9223372036854775807,
        cui=None,
        first_names="Prueba",
        last_names="Grande",
        full_name="Prueba Grande",
        institutional_email="prueba@example.test",
        role=Role.ADMINISTRATIVE,
        state=PersonState.ACTIVE,
        is_admin=False,
    )
    assert salida.model_dump(mode="json")["id"] == "9223372036854775807"


def test_claves_foraneas_rechazan_categorias_huerfanas(
    session_factory: sessionmaker[Session],
) -> None:
    with session_factory() as sesion:
        sesion.add(Category(name="Huérfana", item_type_id=99999))
        with pytest.raises(IntegrityError):
            sesion.commit()


def test_catalogos_de_estados_inicializados(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as sesion:
        estados = set(sesion.scalars(select(EstadoDeLaReserva.nombre_estado)))
    assert {"PENDIENTE", "CONFIRMADA", "CANCELADA"} <= estados


def test_no_mezclar_esquema_antiguo_y_nuevo() -> None:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with motor.begin() as conexion:
            conexion.execute(text("CREATE TABLE accounts (id INTEGER PRIMARY KEY)"))
        with pytest.raises(RuntimeError, match="esquema anterior en inglés"):
            inicializar_base_datos(motor)
        assert inspect(motor).get_table_names() == ["accounts"]
    finally:
        motor.dispose()
