"""Acceso a PostgreSQL y ciclo de vida de las sesiones.

Arranque: esperar PostgreSQL → cargar la conexión original → validar y crear tablas.
Petición: abrir sesión → ejecutar el caso de uso → confirmar o revertir → cerrar.

Importar este módulo no abre conexiones. El motor y la fábrica de sesiones se
reutilizan desde conexion_python_base_datos.py, que permanece sin modificaciones.
"""

import time
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from functools import lru_cache

import psycopg
from sqlalchemy import Engine, make_url, text
from sqlalchemy.orm import DeclarativeBase, Session

from app.core.settings import get_settings
from app.infrastructure.schema import validar_esquema


class Base(DeclarativeBase):
    """Registro de modelos ORM; permite importarlos sin conectarse a PostgreSQL."""


def esperar_base_datos() -> None:
    """Espera un tiempo limitado, sin imprimir la URL ni sus credenciales."""
    configuracion = get_settings()
    direccion = make_url(configuracion.database_url)
    if direccion.drivername != "postgresql+psycopg":
        raise ValueError("DATABASE_URL debe utilizar el controlador postgresql+psycopg.")

    # Psycopg recibe una URI PostgreSQL, sin el sufijo de controlador de SQLAlchemy.
    uri = direccion.set(drivername="postgresql").render_as_string(hide_password=False)
    limite = time.monotonic() + configuracion.database_wait_seconds
    while True:
        try:
            with psycopg.connect(uri, connect_timeout=2):
                return
        except psycopg.OperationalError:
            restante = limite - time.monotonic()
            if restante <= 0:
                raise RuntimeError(
                    "PostgreSQL no está disponible. Revisa DATABASE_URL en .env "
                    "y ejecuta 'docker compose up -d db'."
                ) from None
            time.sleep(min(1, restante))


@lru_cache
def obtener_motor() -> Engine:
    """Carga una sola vez el motor original, después de comprobar PostgreSQL."""
    esperar_base_datos()
    # El módulo protegido consulta SELECT version() al importarse: no cargarlo antes.
    from app.conexion_python_base_datos import motor_base_datos

    return motor_base_datos


def inicializar_base_datos(motor: Engine | None = None) -> Engine:
    """Valida tablas existentes y crea solo las faltantes; no ejecuta migraciones."""
    # Los modelos deben registrarse antes de consultar Base.metadata.
    import app.infrastructure.models  # noqa: F401
    from app.infrastructure.catalogos import cargar_catalogos

    motor = motor if motor is not None else obtener_motor()
    with motor.begin() as conexion:
        if motor.dialect.name == "postgresql":
            # Evita que dos procesos creen las mismas tablas durante el arranque.
            conexion.execute(text("SELECT pg_advisory_xact_lock(73421001)"))
        validar_esquema(conexion, Base.metadata)
        Base.metadata.create_all(bind=conexion)
        cargar_catalogos(conexion)
    return motor


def crear_sesion() -> Session:
    """Reutiliza la fábrica original sin modificar su configuración global."""
    obtener_motor()
    from app.conexion_python_base_datos import SesionBaseDatos

    return SesionBaseDatos(expire_on_commit=False)


@contextmanager
def abrir_sesion() -> Iterator[Session]:
    """Agrupa una operación completa: confirma al terminar o revierte si falla."""
    with crear_sesion() as sesion:
        try:
            yield sesion
            sesion.commit()
        except BaseException:
            sesion.rollback()
            raise


def obtener_sesion() -> Generator[Session]:
    """Dependencia de FastAPI; comparte una sesión durante cada petición."""
    with abrir_sesion() as sesion:
        yield sesion


# Compatibilidad con los imports y las sustituciones de dependencias existentes.
get_session = obtener_sesion
