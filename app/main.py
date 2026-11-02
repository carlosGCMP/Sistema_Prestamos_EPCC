from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import install_error_handlers, router
from app.infrastructure.database import engine

app = FastAPI(
    title="Sistema de Préstamos EPCC",
    version="0.1.0",
    description=(
        "API básica de usuarios, catálogo e inventario, y reservas para la EPCC. "
        "Las operaciones de préstamo todavía no están habilitadas."
    ),
)
app.include_router(router)
install_error_handlers(app)
frontend_directory = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/health", tags=["sistema"])
def healthcheck() -> dict[str, str]:
    """Indica que el proceso HTTP está disponible."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["sistema"])
def readiness() -> dict[str, str]:
    """Comprueba que también existe conectividad con la base de datos."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        from fastapi import HTTPException

        raise HTTPException(status_code=503, detail="Base de datos no disponible") from error
    return {"status": "ready"}


app.mount("/", StaticFiles(directory=frontend_directory, html=True), name="frontend")
