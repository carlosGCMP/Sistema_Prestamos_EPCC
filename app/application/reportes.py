"""Reportes de solo lectura: totales y cantidades agrupadas por estado."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.comun import ahora
from app.infrastructure.models import (
    Category,
    ItemType,
    Loan,
    LoanState,
    Person,
    PhysicalUnit,
    Reservation,
)


def contar_registros(sesion: Session, modelo: Any) -> int:
    """COUNT cuenta toda la tabla, no solo las filas cargadas por la interfaz."""
    return int(sesion.scalar(select(func.count()).select_from(modelo)) or 0)


def contar_por_estado(sesion: Session, modelo: Any) -> dict[str, int]:
    """GROUP BY reúne los registros que comparten el mismo estado."""
    consulta = select(modelo.state, func.count()).group_by(modelo.state).order_by(modelo.state)
    return {str(estado): cantidad for estado, cantidad in sesion.execute(consulta)}


def resumen(sesion: Session) -> dict[str, Any]:
    instante = ahora()
    prestamos = contar_por_estado(sesion, Loan)
    abiertos = prestamos.get(LoanState.ACTIVE.value, 0) + prestamos.get(LoanState.OVERDUE.value, 0)
    vencidos = int(
        sesion.scalar(
            select(func.count())
            .select_from(Loan)
            .where(
                Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE)),
                Loan.due_at < instante,
            )
        )
        or 0
    )
    # Solo cambia la clasificación del reporte, nunca el préstamo ni la unidad.
    prestamos[LoanState.ACTIVE.value] = abiertos - vencidos
    prestamos[LoanState.OVERDUE.value] = vencidos
    return {
        "generado_en": instante,
        "personas": contar_registros(sesion, Person),
        "tipos": contar_registros(sesion, ItemType),
        "categorias": contar_registros(sesion, Category),
        "unidades": contar_registros(sesion, PhysicalUnit),
        "reservas": contar_registros(sesion, Reservation),
        "prestamos": contar_registros(sesion, Loan),
        "inventario_por_estado": contar_por_estado(sesion, PhysicalUnit),
        "reservas_por_estado": contar_por_estado(sesion, Reservation),
        "prestamos_por_estado": prestamos,
    }
