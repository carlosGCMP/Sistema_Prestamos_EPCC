from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool

from app.api.modulos import router as modulos_router
from app.api.routes import install_error_handlers, router
from app.infrastructure.database import inicializar_base_datos


@asynccontextmanager
async def ciclo_de_vida(aplicacion: FastAPI) -> AsyncIterator[None]:
    """Prepara la base antes de atender peticiones y libera el motor al detenerse."""
    motor = await run_in_threadpool(inicializar_base_datos)
    aplicacion.state.motor_base_datos = motor
    try:
        yield
    finally:
        aplicacion.state.motor_base_datos = None
        motor.dispose()


app = FastAPI(
    title="Sistema de Préstamos EPCC",
    version="0.1.0",
    description=(
        "Usuarios, inventario, reservas, préstamos, políticas y vinculación académica. "
        "Límite de 3 días para estudiantes y 7 para docentes."
    ),
    lifespan=ciclo_de_vida,
)
app.include_router(router)
app.include_router(modulos_router)
install_error_handlers(app)
frontend_directory = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health", tags=["sistema"])
def healthcheck() -> dict[str, str]:
    """Indica que el proceso HTTP está disponible."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["sistema"])
def readiness() -> dict[str, str]:
    """Comprueba que también existe conectividad con la base de datos."""
    motor = getattr(app.state, "motor_base_datos", None)
    if motor is None:
        raise HTTPException(status_code=503, detail="Base de datos no inicializada")
    try:
        with motor.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Base de datos no disponible") from error
    return {"status": "ready"}


app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
