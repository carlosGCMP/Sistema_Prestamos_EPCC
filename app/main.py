from fastapi import FastAPI

app = FastAPI(
    title="Sistema de Préstamos EPCC",
    version="0.1.0",
    description="API para la gestión de préstamos de bienes de la EPCC.",
)


@app.get("/health", tags=["sistema"])
def healthcheck() -> dict[str, str]:
    """Indica que el proceso HTTP está disponible."""
    return {"status": "ok"}
