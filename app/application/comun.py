"""Errores, fechas y auditoría compartidos por los módulos del aplicativo."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infrastructure.modelos_sql import HistorialDeCambios, TipoDeEvento
from app.infrastructure.models import AuditEvent, Person, PersonState, PhysicalUnit, Solicitante


class UseCaseError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def ahora() -> datetime:
    return datetime.now(UTC)


def instante_utc(valor: datetime, campo: str) -> datetime:
    if valor.tzinfo is None or valor.utcoffset() is None:
        raise UseCaseError(422, f"{campo} debe incluir zona horaria")
    return valor.astimezone(UTC)


def bloquear_solicitante(sesion: Session, identificador: int) -> Person:
    solicitante = sesion.get(Solicitante, identificador)
    if solicitante is None:
        raise UseCaseError(404, "Solicitante no encontrado")
    persona = sesion.scalar(
        select(Person)
        .where(Person.id == solicitante.person_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if persona is None or persona.state != PersonState.ACTIVE:
        raise UseCaseError(409, "La persona solicitante no está activa")
    if persona.account is None or not persona.account.active:
        raise UseCaseError(409, "Se requiere una cuenta activa")
    return persona


def bloquear_unidad(sesion: Session, identificador: int) -> PhysicalUnit:
    unidad = sesion.scalar(
        select(PhysicalUnit)
        .where(PhysicalUnit.id == identificador)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if unidad is None:
        raise UseCaseError(404, "Unidad física no encontrada")
    return unidad


def audit(
    sesion: Session,
    actor: Person | None,
    accion: str,
    entidad: str,
    identificador: int | str,
    detalles: dict[str, Any] | None = None,
) -> None:
    tipo = sesion.scalar(select(TipoDeEvento).where(TipoDeEvento.nombre_tipo_evento == "OPERACION"))
    if tipo is None:
        raise UseCaseError(500, "Falta inicializar el catálogo de auditoría")
    evento = AuditEvent(
        actor_id=actor.account.id if actor and actor.account else None,
        event_type_id=tipo.id_tipo_evento,
        actor_type="USUARIO" if actor else "PROCESO_AUTOMATICO",
        action=accion,
        entity_type=entidad,
        entity_id=str(identificador),
        details=detalles or {},
    )
    sesion.add(evento)
    sesion.flush()
    sesion.add(HistorialDeCambios(id_registro=evento.id, descripcion=accion))
