
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pydantic_settings import BaseSettings, SettingsConfigDict


# Configuración de conexión con la base de datos
class ConfiguracionBaseDatos(BaseSettings):
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


configuracion = ConfiguracionBaseDatos()


# Motor encargado de administrar las conexiones
motor_base_datos = create_engine(
    configuracion.DATABASE_URL,
    pool_pre_ping=True
)


# Fábrica de sesiones para realizar operaciones en la BD
SesionBaseDatos = sessionmaker(
    bind=motor_base_datos,
    autoflush=False,
    autocommit=False
)


# Clase base para los modelos de las tablas
class BaseDatos(DeclarativeBase):
    pass


# Proporciona una sesión y la cierra al finalizar
def obtener_conexion():
    sesion = SesionBaseDatos()
    try:
        yield sesion
    finally:
        sesion.close()
