"""Las siete políticas, en un solo lugar, para reservas y entregas."""

import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.comun import UseCaseError, ahora, audit, instante_utc
from app.application.schemas import PolicyCreate, PolicyOut
from app.core.reglas import DIAS_POR_ROL, MAXIMO_BIENES
from app.infrastructure.modelos_sql import ReglasDelPrestamo, VersionDeLaPolitica
from app.infrastructure.models import (
    Bien,
    Category,
    ItemCard,
    ItemType,
    Loan,
    LoanPolicy,
    LoanState,
    Person,
    PersonState,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    TimeUnit,
    UnitState,
)
from app.infrastructure.semillas_politicas import guardar_version, resumen_politica


def contenido_politica(sesion: Session, politica: LoanPolicy) -> dict[str, Any]:
    version = sesion.scalar(
        select(VersionDeLaPolitica)
        .where(
            VersionDeLaPolitica.id_politica == politica.id,
        )
        .order_by(VersionDeLaPolitica.id_version.desc())
        .limit(1)
    )
    if version is not None:
        try:
            contenido = json.loads(version.contenido)
        except ValueError:
            raise UseCaseError(
                409, "El historial de la política no es válido; publica una nueva versión"
            ) from None
        if not isinstance(contenido, dict) or "permitted" not in contenido:
            raise UseCaseError(409, "Falta completar el historial de la política")
        permitido = bool(contenido["permitted"])
    else:
        regla = sesion.scalar(
            select(ReglasDelPrestamo).where(
                ReglasDelPrestamo.id_tipo_bien == politica.item_type_id,
                ReglasDelPrestamo.tipo_solicitante == politica.role,
            )
        )
        if regla is None:
            raise UseCaseError(
                409, "La política no tiene una regla asociada; publica una nueva versión"
            )
        permitido = regla.permitido
    return resumen_politica(politica, permitido)


def salida_politica(sesion: Session, politica: LoanPolicy) -> PolicyOut:
    instante = ahora()
    estado = "VIGENTE"
    if not politica.active or (politica.valid_until and politica.valid_until <= instante):
        estado = "FINALIZADA"
    elif politica.valid_from > instante:
        estado = "PROGRAMADA"
    return PolicyOut(
        id=politica.id,
        name=politica.name,
        role=politica.role,
        item_type_id=politica.item_type_id,
        version=politica.version,
        max_units=politica.max_units,
        max_duration=politica.max_duration,
        duration_unit=politica.duration_unit,
        permitted=contenido_politica(sesion, politica)["permitted"],
        valid_from=politica.valid_from,
        valid_until=politica.valid_until,
        active=politica.active,
        status=estado,
    )


def publicar_politica(sesion: Session, datos: PolicyCreate, actor: Person) -> LoanPolicy:
    tipo = sesion.scalar(
        select(ItemType).where(ItemType.id == datos.item_type_id).with_for_update()
    )
    if tipo is None:
        raise UseCaseError(404, "Tipo de bien no encontrado")
    inicio = instante_utc(datos.valid_from, "Vigencia de inicio") if datos.valid_from else ahora()
    fin = instante_utc(datos.valid_until, "Vigencia de fin") if datos.valid_until else None
    if fin is not None and fin <= inicio:
        raise UseCaseError(422, "La vigencia de fin debe ser posterior al inicio")
    versiones = list(
        sesion.scalars(
            select(LoanPolicy)
            .where(
                LoanPolicy.item_type_id == tipo.id,
                LoanPolicy.role == datos.role,
            )
            .order_by(LoanPolicy.version)
        )
    )
    if versiones and inicio <= max(p.valid_from for p in versiones):
        raise UseCaseError(409, "La nueva versión debe iniciar después de las versiones publicadas")
    for anterior in versiones:
        if anterior.valid_until is None or anterior.valid_until > inicio:
            anterior.valid_until = inicio
        # Una versión anterior sigue vigente hasta su fecha de fin, incluso si se programa otra.
    politica = LoanPolicy(
        name=datos.name,
        role=datos.role,
        item_type_id=tipo.id,
        version=max((p.version for p in versiones), default=0) + 1,
        max_units=datos.max_units,
        max_duration=datos.max_duration,
        duration_unit=TimeUnit.DAYS,
        allowed_modes=["RETIRO", "EN_SITIO"],
        valid_from=inicio,
        valid_until=fin,
    )
    sesion.add(politica)
    sesion.flush()
    regla = sesion.scalar(
        select(ReglasDelPrestamo).where(
            ReglasDelPrestamo.id_tipo_bien == tipo.id,
            ReglasDelPrestamo.tipo_solicitante == datos.role.value,
        )
    )
    if regla is None:
        regla = ReglasDelPrestamo(id_tipo_bien=tipo.id, tipo_solicitante=datos.role.value)
        sesion.add(regla)
    regla.cantidad_maxima_bienes = datos.max_units
    regla.cantidad_maxima_prestamos = datos.max_units
    regla.permitido = datos.permitted
    guardar_version(sesion, politica, datos.permitted)
    audit(
        sesion,
        actor,
        "POLITICA_PUBLICADA",
        "PoliticaDelPrestamo",
        politica.id,
        resumen_politica(politica, datos.permitted),
    )
    return politica


def buscar_politica_vigente(
    sesion: Session, rol: Role, tipo_id: int, fecha: datetime
) -> dict[str, Any]:
    politica = sesion.scalar(
        select(LoanPolicy)
        .where(
            LoanPolicy.role == rol,
            LoanPolicy.item_type_id == tipo_id,
            LoanPolicy.active.is_(True),
            LoanPolicy.valid_from <= fecha,
            (LoanPolicy.valid_until.is_(None) | (LoanPolicy.valid_until > fecha)),
        )
        .order_by(LoanPolicy.version.desc())
        .limit(1)
    )
    if politica is None:
        raise UseCaseError(409, "No hay una política vigente para este rol, tipo de bien y fecha")
    return contenido_politica(sesion, politica)


def validar_acceso(persona: Person) -> None:
    if persona.role.value not in DIAS_POR_ROL:
        raise UseCaseError(403, "Solo estudiantes y docentes pueden solicitar reservas")
    if (
        persona.state != PersonState.ACTIVE
        or persona.account is None
        or not persona.account.active
        or persona.applicant is None
    ):
        raise UseCaseError(409, "Se requiere una persona y cuenta activas")


def validar_disponibilidad(unidad: PhysicalUnit) -> int:
    ficha = unidad.item_card
    categoria = ficha.bien.category
    tipo = categoria.item_type
    if (
        unidad.state != UnitState.AVAILABLE
        or not ficha.active
        or not categoria.active
        or not tipo.active
        or not tipo.lendable
    ):
        raise UseCaseError(409, "La unidad o su catálogo no están disponibles para reservar")
    return tipo.id


def asegurar_sin_cruces(
    sesion: Session,
    unidad_id: int,
    inicio: datetime,
    fin: datetime,
    *,
    reserva_excluida: int | None = None,
) -> None:
    consulta = select(Reservation.id).where(
        Reservation.unit_id == unidad_id,
        Reservation.state == ReservationState.CONFIRMED,
        Reservation.starts_at < fin,
        Reservation.ends_at > inicio,
    )
    if reserva_excluida is not None:
        consulta = consulta.where(Reservation.id != reserva_excluida)
    if sesion.scalar(consulta.limit(1)) is not None:
        raise UseCaseError(409, "El intervalo se cruza con una reserva confirmada de esta unidad")
    if (
        sesion.scalar(
            select(Loan.id)
            .where(
                Loan.unit_id == unidad_id,
                Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE)),
            )
            .limit(1)
        )
        is not None
    ):
        raise UseCaseError(409, "La unidad tiene un préstamo abierto; primero debe devolverse")


def validar_cantidad(
    sesion: Session,
    solicitante_id: int,
    tipo_id: int,
    inicio: datetime,
    fin: datetime,
    maximo: int,
    *,
    reserva_excluida: int | None = None,
) -> None:
    unidades_tipo = (
        select(PhysicalUnit.id)
        .join(ItemCard)
        .join(Bien)
        .join(Category)
        .where(Category.item_type_id == tipo_id)
    )
    # Una devolución pendiente sigue ocupando cupo, aunque haya pasado el vencimiento.
    prestamos = sesion.scalars(
        select(Loan).where(
            Loan.applicant_id == solicitante_id,
            Loan.unit_id.in_(unidades_tipo),
            Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE)),
        )
    ).all()
    eventos = [(inicio, 1), (fin, -1)]
    for _prestamo in prestamos:
        eventos.extend([(inicio, 1), (fin, -1)])
    reservas = sesion.scalars(
        select(Reservation).where(
            Reservation.applicant_id == solicitante_id,
            Reservation.unit_id.in_(unidades_tipo),
            Reservation.state == ReservationState.CONFIRMED,
            Reservation.starts_at < fin,
            Reservation.ends_at > inicio,
        )
    ).all()
    for reserva in reservas:
        if reserva.id != reserva_excluida:
            eventos.extend([(max(inicio, reserva.starts_at), 1), (min(fin, reserva.ends_at), -1)])
    cantidad = 0
    # El final no se incluye: devolver a las 10 permite reservar desde las 10.
    for _, cambio in sorted(eventos, key=lambda evento: (evento[0], evento[1])):
        cantidad += cambio
        if cantidad > maximo:
            raise UseCaseError(
                409, f"El límite es {maximo} bienes simultáneos de este tipo por persona"
            )


def validar_reserva(
    sesion: Session,
    persona: Person,
    unidad: PhysicalUnit,
    inicio: datetime,
    fin: datetime,
    *,
    reserva_excluida: int | None = None,
    politica: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validar_acceso(persona)
    tipo_id = validar_disponibilidad(unidad)
    aplicada = (
        politica
        if politica is not None
        else buscar_politica_vigente(sesion, persona.role, tipo_id, inicio)
    )
    if not aplicada["permitted"]:
        raise UseCaseError(403, "La política no permite reservar este tipo de bien para tu rol")
    dias = int(aplicada["max_duration"])
    maximo = int(aplicada["max_units"])
    if (
        aplicada["duration_unit"] != TimeUnit.DAYS.value
        or dias < 1
        or dias > DIAS_POR_ROL[persona.role.value]
        or not 1 <= maximo <= MAXIMO_BIENES
    ):
        raise UseCaseError(
            409, "La política no cumple los límites acordados; publica una versión válida"
        )
    if fin - inicio > timedelta(days=dias):
        raise UseCaseError(422, f"La duración máxima para este rol y tipo es {dias} días corridos")
    asegurar_sin_cruces(sesion, unidad.id, inicio, fin, reserva_excluida=reserva_excluida)
    assert persona.applicant is not None
    validar_cantidad(
        sesion,
        persona.applicant.id,
        tipo_id,
        inicio,
        fin,
        maximo,
        reserva_excluida=reserva_excluida,
    )
    return aplicada
