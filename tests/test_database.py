"""Pruebas del arranque y las sesiones sin acceder a la base local del usuario."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Annotated
from unittest.mock import Mock

import psycopg
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import install_error_handlers
from app.core.settings import Settings
from app.infrastructure import database
from app.infrastructure.models import Category, ItemType


def test_importar_aplicacion_no_abre_conexiones() -> None:
    codigo = """
import sys
import psycopg

def conexion_prohibida(*args, **kwargs):
    raise AssertionError("No debe abrir conexiones al importar")

psycopg.connect = conexion_prohibida
import app.main
assert "app.conexion_python_base_datos" not in sys.modules
"""
    entorno = {**os.environ, "DATABASE_URL": "postgresql+psycopg://inexistente@localhost:1/prueba"}
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=Path(__file__).resolve().parents[1],
        env=entorno,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert resultado.returncode == 0, resultado.stderr
    assert resultado.stdout == ""


def configurar_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    configuracion = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://usuario:clave-secreta@localhost:5433/prueba",
        database_wait_seconds=1,
    )
    monkeypatch.setattr(database, "get_settings", lambda: configuracion)


def test_esperar_base_disponible(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_espera(monkeypatch)
    conexion = Mock()
    conexion.__enter__ = Mock(return_value=conexion)
    conexion.__exit__ = Mock(return_value=None)
    conectar = Mock(return_value=conexion)
    monkeypatch.setattr(database.psycopg, "connect", conectar)

    database.esperar_base_datos()

    conectar.assert_called_once_with(
        "postgresql://usuario:clave-secreta@localhost:5433/prueba", connect_timeout=2
    )
    conexion.__exit__.assert_called_once()


def test_esperar_reintenta_antes_de_fallar(monkeypatch: pytest.MonkeyPatch) -> None:
    configurar_espera(monkeypatch)
    conectar = Mock(side_effect=psycopg.OperationalError("rechazada"))
    dormir = Mock()
    monkeypatch.setattr(database.psycopg, "connect", conectar)
    monkeypatch.setattr(database.time, "monotonic", Mock(side_effect=[0, 0.25, 1]))
    monkeypatch.setattr(database.time, "sleep", dormir)

    with pytest.raises(RuntimeError, match="docker compose up -d db") as error:
        database.esperar_base_datos()

    assert conectar.call_count == 2
    dormir.assert_called_once_with(0.75)
    assert "clave-secreta" not in str(error.value)
    assert error.value.__suppress_context__


def test_esperar_rechaza_controlador_incorrecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        database, "get_settings", lambda: Settings(database_url="sqlite:///:memory:")
    )
    with pytest.raises(ValueError, match="postgresql\\+psycopg"):
        database.esperar_base_datos()


def test_inicializar_crea_tablas_y_conserva_datos() -> None:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        assert database.inicializar_base_datos(motor) is motor
        with Session(motor) as sesion:
            tipo = ItemType(name="Temporal")
            sesion.add(tipo)
            sesion.flush()
            sesion.add(Category(name="No borrar", item_type_id=tipo.id))
            sesion.commit()

        database.inicializar_base_datos(motor)

        with Session(motor) as sesion:
            assert sesion.scalar(select(Category.name)) == "No borrar"
        assert "solicitud_de_reserva" in inspect(motor).get_table_names()
    finally:
        motor.dispose()


@pytest.mark.parametrize(
    ("definicion", "mensaje"),
    [
        (
            "id_categoria INTEGER NOT NULL PRIMARY KEY",
            "Falta la columna categoria_del_bien.nombre_categoria",
        ),
        (
            "id_categoria VARCHAR(30) NOT NULL PRIMARY KEY, "
            "nombre_categoria VARCHAR(100) NOT NULL, "
            "id_tipo_bien INTEGER NOT NULL, descripcion TEXT, activo BOOLEAN NOT NULL",
            "categoria_del_bien.id_categoria: tipo VARCHAR",
        ),
        (
            "id_categoria INTEGER NOT NULL PRIMARY KEY, nombre_categoria VARCHAR(100), "
            "id_tipo_bien INTEGER NOT NULL, descripcion TEXT, activo BOOLEAN NOT NULL",
            "categoria_del_bien.nombre_categoria: la restricción de valores nulos",
        ),
        (
            "id_categoria INTEGER NOT NULL, nombre_categoria VARCHAR(100) NOT NULL PRIMARY KEY, "
            "id_tipo_bien INTEGER NOT NULL, descripcion TEXT, activo BOOLEAN NOT NULL",
            "categoria_del_bien: la clave primaria",
        ),
        (
            "id_categoria INTEGER NOT NULL PRIMARY KEY, nombre_categoria VARCHAR(100) NOT NULL, "
            "id_tipo_bien INTEGER NOT NULL, descripcion TEXT, "
            "activo BOOLEAN NOT NULL, obligatoria TEXT NOT NULL",
            "categoria_del_bien.obligatoria: columna obligatoria no prevista",
        ),
    ],
)
def test_esquema_incompatible_no_crea_otras_tablas(definicion: str, mensaje: str) -> None:
    motor = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with motor.begin() as conexion:
            conexion.execute(text(f"CREATE TABLE categoria_del_bien ({definicion})"))
        with pytest.raises(RuntimeError, match=mensaje):
            database.inicializar_base_datos(motor)
        assert inspect(motor).get_table_names() == ["categoria_del_bien"]
    finally:
        motor.dispose()


def test_sesion_confirma_y_cierra(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    sesion = session_factory()
    cerrar = Mock(wraps=sesion.close)
    monkeypatch.setattr(sesion, "close", cerrar)
    monkeypatch.setattr(database, "crear_sesion", lambda: sesion)

    with database.abrir_sesion() as actual:
        actual.add(Category(name="Confirmada", item_type_id=1))

    cerrar.assert_called_once()
    with session_factory() as consulta:
        assert consulta.scalar(select(Category.name)) == "Confirmada"


def test_sesion_revierte_y_cierra_si_falla(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    sesion = session_factory()
    cerrar = Mock(wraps=sesion.close)
    monkeypatch.setattr(sesion, "close", cerrar)
    monkeypatch.setattr(database, "crear_sesion", lambda: sesion)

    with pytest.raises(ValueError, match="operación interrumpida"):
        with database.abrir_sesion() as actual:
            actual.add(Category(name="Revertida", item_type_id=1))
            actual.flush()
            raise ValueError("operación interrumpida")

    cerrar.assert_called_once()
    with session_factory() as consulta:
        assert consulta.scalar(select(Category)) is None


def test_commit_fallido_no_envia_respuesta_exitosa(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with session_factory.begin() as sesion:
        sesion.add(Category(name="Duplicada", item_type_id=1))
    monkeypatch.setattr(database, "crear_sesion", session_factory)
    aplicacion = FastAPI()
    install_error_handlers(aplicacion)

    @aplicacion.post("/prueba", status_code=201)
    def crear_duplicado(
        sesion: Annotated[Session, Depends(database.obtener_sesion, scope="function")],
    ) -> dict[str, bool]:
        # Sin flush: el error debe detectarse al confirmar, antes de enviar el 201.
        sesion.add(Category(name="Duplicada", item_type_id=1))
        return {"creada": True}

    with TestClient(aplicacion) as cliente:
        respuesta = cliente.post("/prueba")

    assert respuesta.status_code == 409
    with session_factory() as consulta:
        assert len(consulta.scalars(select(Category)).all()) == 1


def test_arranque_y_readiness(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert client.get("/").status_code == 200


def test_readiness_detecta_desconexion(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        client.app.state.motor_base_datos,
        "connect",
        Mock(side_effect=SQLAlchemyError("sin conexión")),
    )
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health").status_code == 200
