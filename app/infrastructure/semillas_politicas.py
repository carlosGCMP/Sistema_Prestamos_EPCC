"""Crea reglas iniciales solo donde nunca se publicó una política; no sobrescribe cambios."""

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, select
from sqlalchemy.orm import Session

from app.core.reglas import DIAS_POR_ROL, MAXIMO_BIENES
from app.infrastructure.modelos_sql import ReglasDelPrestamo, VersionDeLaPolitica
from app.infrastructure.models import ItemType, LoanPolicy, Role, TimeUnit


def resumen_politica(politica: LoanPolicy, permitido: bool) -> dict[str, Any]:
    return {
        "policy_id": str(politica.id),
        "version": politica.version,
        "role": politica.role.value if politica.role else None,
        "item_type_id": str(politica.item_type_id),
        "name": politica.name,
        "max_units": politica.max_units,
        "max_duration": politica.max_duration,
        "duration_unit": politica.duration_unit.value,
        "permitted": permitido,
        "valid_from": politica.valid_from.isoformat(),
        "valid_until": politica.valid_until.isoformat() if politica.valid_until else None,
    }


def guardar_version(sesion: Session, politica: LoanPolicy, permitido: bool) -> None:
    sesion.add(
        VersionDeLaPolitica(
            id_politica=politica.id,
            contenido=json.dumps(resumen_politica(politica, permitido), ensure_ascii=False),
        )
    )


def crear_predeterminadas(sesion: Session, tipo_id: int) -> None:
    for rol, dias in DIAS_POR_ROL.items():
        if (
            sesion.scalar(
                select(LoanPolicy.id)
                .where(
                    LoanPolicy.item_type_id == tipo_id,
                    LoanPolicy.role == Role(rol),
                )
                .limit(1)
            )
            is not None
        ):
            continue
        regla = sesion.scalar(
            select(ReglasDelPrestamo).where(
                ReglasDelPrestamo.id_tipo_bien == tipo_id,
                ReglasDelPrestamo.tipo_solicitante == rol,
            )
        )
        # Si ya había una regla manual, conservar también sus restricciones de cupo.
        maximo = (
            min(MAXIMO_BIENES, regla.cantidad_maxima_bienes, regla.cantidad_maxima_prestamos)
            if regla
            else MAXIMO_BIENES
        )
        permitido = regla.permitido and maximo > 0 if regla else True
        politica = LoanPolicy(
            name=f"Política inicial: {rol.lower()}",
            role=Role(rol),
            item_type_id=tipo_id,
            max_units=max(1, maximo),
            max_duration=dias,
            duration_unit=TimeUnit.DAYS,
            allowed_modes=["RETIRO", "EN_SITIO"],
            valid_from=datetime(1970, 1, 1, tzinfo=UTC),
        )
        sesion.add(politica)
        sesion.flush()
        if regla is None:
            sesion.add(
                ReglasDelPrestamo(
                    id_tipo_bien=tipo_id,
                    tipo_solicitante=rol,
                    cantidad_maxima_prestamos=MAXIMO_BIENES,
                    cantidad_maxima_bienes=MAXIMO_BIENES,
                    permitido=True,
                )
            )
        guardar_version(sesion, politica, permitido)
    sesion.flush()


def cargar_politicas_iniciales(conexion: Connection) -> None:
    # La conexión ya tiene una transacción de arranque. Aquí solo se hace flush.
    with Session(bind=conexion, autoflush=False) as sesion:
        for identificador in sesion.scalars(select(ItemType.id)).all():
            crear_predeterminadas(sesion, identificador)
