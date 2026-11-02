"""Nombres compatibles con la rama de conexiones, sin duplicar la persistencia.

La API, Alembic y este módulo comparten motor, sesiones y metadatos.
Importarlo no abre conexiones ni imprime credenciales.
"""

from app.infrastructure.database import (
    Base as BaseDatos,
)
from app.infrastructure.database import (
    SessionLocal as SesionBaseDatos,
)
from app.infrastructure.database import (
    engine as motor_base_datos,
)
from app.infrastructure.database import (
    get_session as obtener_conexion,
)

__all__ = ["BaseDatos", "SesionBaseDatos", "motor_base_datos", "obtener_conexion"]


if __name__ == "__main__":
    with motor_base_datos.connect() as conexion:
        print(conexion.exec_driver_sql("SELECT version()").scalar())
