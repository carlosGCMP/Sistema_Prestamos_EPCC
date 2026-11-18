"""Rutas administrativas del dashboard y la importación de catálogo."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.application import reportes
from app.core.security import AdminActor
from app.infrastructure.database import obtener_sesion

router = APIRouter(prefix="/reports", tags=["reportes"])
SessionDep = Annotated[Session, Depends(obtener_sesion, scope="function")]


class ImportacionCSV(BaseModel):
    contenido: str = Field(min_length=1, max_length=100_000)


@router.get("/summary")
def consultar_resumen(_actor: AdminActor, sesion: SessionDep) -> dict[str, Any]:
    return reportes.resumen(sesion)


@router.post("/catalog/preview")
def previsualizar_catalogo(
    datos: ImportacionCSV, _actor: AdminActor, sesion: SessionDep
) -> list[dict[str, str]]:
    return reportes.validar_csv(sesion, datos.contenido)


@router.post("/catalog/import", status_code=201)
def importar_catalogo(
    datos: ImportacionCSV, actor: AdminActor, sesion: SessionDep
) -> dict[str, int]:
    return reportes.importar_catalogo(sesion, datos.contenido, actor)
