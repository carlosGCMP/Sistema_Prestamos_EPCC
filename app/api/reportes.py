"""Consulta administrativa de reportes; no modifica datos."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.application import reportes
from app.core.security import AdminActor
from app.infrastructure.database import obtener_sesion

router = APIRouter(prefix="/reports", tags=["reportes"])
SessionDep = Annotated[Session, Depends(obtener_sesion, scope="function")]


@router.get("/summary")
def consultar_resumen(_actor: AdminActor, sesion: SessionDep) -> dict[str, Any]:
    return reportes.resumen(sesion)
