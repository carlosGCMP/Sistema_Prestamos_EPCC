"""Uso explícito: python -m app.cargar_demo. Nunca se ejecuta al arrancar la API."""

from pydantic import ValidationError
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.application.comun import UseCaseError
from app.application.datos_demo import USUARIOS_DEMO, crear_datos
from app.bootstrap_admin import explicar_validacion
from app.core.settings import get_settings
from app.infrastructure.catalogos import cargar_catalogos
from app.infrastructure.database import Base, obtener_motor
from app.infrastructure.schema import validar_esquema
from app.infrastructure.seguridad_demo import (
    CargaDemoRechazada,
    comprobar_destino,
    registrar_carga,
)


def cargar_demo(motor: Engine) -> bool:
    """Crea tablas y datos solo después de comprobar el destino, sin migraciones."""
    with motor.begin() as conexion:
        if motor.dialect.name == "postgresql":
            # Mismo orden que el arranque y el alta del primer administrador.
            conexion.execute(text("SELECT pg_advisory_xact_lock(73421001)"))
            conexion.execute(text("SELECT pg_advisory_xact_lock(73421002)"))
        if not comprobar_destino(conexion):
            return False
        # No usar el inicializador normal antes de comprobar: añadiría catálogos
        # o políticas a una base existente que debemos dejar completamente intacta.
        validar_esquema(conexion, Base.metadata)
        Base.metadata.create_all(bind=conexion)
        cargar_catalogos(conexion)
        with Session(bind=conexion, autoflush=False, expire_on_commit=False) as sesion:
            crear_datos(sesion)
            registrar_carga(sesion)
    return True


def main() -> None:
    motor: Engine | None = None
    try:
        if get_settings().app_env != "development":
            raise CargaDemoRechazada("La demo solo está permitida con APP_ENV=development.")
        motor = obtener_motor()
        creada = cargar_demo(motor)
    except ValidationError as error:
        raise SystemExit(explicar_validacion(error, configuracion=True)) from None
    except CargaDemoRechazada as error:
        raise SystemExit(str(error)) from None
    except (SQLAlchemyError, RuntimeError, UseCaseError):
        # No imprimir URLs, contraseñas, parámetros SQL ni datos de otras cuentas.
        raise SystemExit(
            "No se pudo cargar la demo. Revisa PostgreSQL y DATABASE_URL en .env. "
            "La carga de datos se revierte si ocurre un error; no borres tu base para solucionarlo."
        ) from None
    finally:
        if motor is not None:
            motor.dispose()
    print(
        "Datos de demostración creados."
        if creada
        else "La demo ya está cargada; no se cambió nada."
    )
    print("Cuentas de prueba: " + ", ".join(USUARIOS_DEMO))
    print("Contraseña y pasos: docs/datos-demo.md. Solo para evaluación local.")


if __name__ == "__main__":
    main()
