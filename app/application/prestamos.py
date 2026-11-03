"""Entrega y devolución de unidades provenientes de reservas confirmadas."""

from datetime import time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.comun import (
    UseCaseError,
    ahora,
    audit,
    bloquear_solicitante,
    bloquear_unidad,
    instante_utc,
)
from app.application.politicas import validar_reserva
from app.application.schemas import LoanCreate, LoanOut, ReturnCreate
from app.infrastructure.modelos_sql import (
    DevolucionDelPrestamo,
    EntregaDelPrestamo,
    PrestamoAprobadoDeReserva,
    RegistroBienesFisicosPrestamo,
    RegistroDeReserva,
)
from app.infrastructure.models import (
    Account,
    Administrador,
    AuditEvent,
    Loan,
    LoanState,
    Person,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Solicitante,
    UnitState,
)


def entregar(sesion: Session, datos: LoanCreate, actor: Person) -> Loan:
    referencia = sesion.get(Reservation, datos.origin_reservation_id)
    if referencia is None:
        raise UseCaseError(404, "Reserva no encontrada")
    persona = bloquear_solicitante(sesion, referencia.applicant_id)
    unidad = bloquear_unidad(sesion, referencia.unit_id)
    reserva = sesion.scalar(
        select(Reservation)
        .where(Reservation.id == referencia.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert reserva is not None
    inicio = ahora()
    fin = instante_utc(datos.due_at, "Vencimiento")
    if reserva.state != ReservationState.CONFIRMED:
        raise UseCaseError(409, "La entrega requiere una reserva confirmada y no atendida")
    if not reserva.starts_at <= inicio < reserva.ends_at:
        raise UseCaseError(409, "La entrega debe realizarse dentro del horario de la reserva")
    if fin <= inicio or fin > reserva.ends_at:
        raise UseCaseError(422, "El vencimiento debe ser futuro y no superar el fin de la reserva")
    registro = sesion.scalar(
        select(RegistroDeReserva).where(RegistroDeReserva.id_solicitud == reserva.id)
    )
    if registro is None:
        raise UseCaseError(409, "La reserva confirmada no tiene su registro de aprobación")
    evento = sesion.scalar(
        select(AuditEvent)
        .where(
            AuditEvent.entity_type == "SolicitudDeReserva",
            AuditEvent.entity_id == str(reserva.id),
            AuditEvent.action == "RESERVA_CONFIRMADA",
        )
        .order_by(AuditEvent.id.desc())
        .limit(1)
    )
    conservada = evento.details.get("politica") if evento else None
    politica = validar_reserva(
        sesion,
        persona,
        unidad,
        inicio,
        fin,
        reserva_excluida=reserva.id,
        politica=conservada if isinstance(conservada, dict) else None,
    )
    assert actor.account is not None and actor.account.administrator is not None

    # Esta tabla usa DATE. Su fin resume los días cubiertos, como límite exclusivo.
    # Las horas exactas siempre se conservan y validan en préstamo y reserva.
    fin_dias = (
        fin.date()
        if fin.timetz().replace(tzinfo=None) == time.min
        else fin.date() + timedelta(days=1)
    )
    aprobacion = PrestamoAprobadoDeReserva(
        id_reserva=registro.id_reserva,
        fecha_inicio=inicio.date(),
        fecha_fin=fin_dias,
    )
    sesion.add(aprobacion)
    sesion.flush()
    prestamo = Loan(
        applicant_id=reserva.applicant_id,
        administrator_id=actor.account.administrator.id,
        unit_id=unidad.id,
        origin_reservation_id=reserva.id,
        approval_id=aprobacion.id_prestamo_aprobado,
        starts_at=inicio,
        due_at=fin,
        use_mode=datos.use_mode,
        delivered_condition=datos.delivered_condition,
        delivered_accessories=datos.delivered_accessories,
        applied_policy=politica,
    )
    reserva.state = ReservationState.FULFILLED
    registro.estado = ReservationState.FULFILLED.value
    unidad.state = UnitState.LOANED
    sesion.add(prestamo)
    sesion.flush()
    sesion.add_all(
        [
            EntregaDelPrestamo(
                id_prestamo=prestamo.id, fecha_entrega=inicio, observaciones=datos.notes
            ),
            RegistroBienesFisicosPrestamo(id_prestamo=prestamo.id, id_unidad_fisica=unidad.id),
        ]
    )
    audit(sesion, actor, "PRESTAMO_ENTREGADO", "Prestamo", prestamo.id, {"politica": politica})
    return prestamo


def devolver(sesion: Session, identificador: int, datos: ReturnCreate, actor: Person) -> Loan:
    referencia = sesion.get(Loan, identificador)
    if referencia is None:
        raise UseCaseError(404, "Préstamo no encontrado")
    solicitante = sesion.get(Solicitante, referencia.applicant_id)
    # Una cuenta desactivada también debe poder devolver sus bienes mediante un administrador.
    if solicitante is not None:
        sesion.scalar(select(Person).where(Person.id == solicitante.person_id).with_for_update())
    unidad = bloquear_unidad(sesion, referencia.unit_id)
    prestamo = sesion.scalar(
        select(Loan)
        .where(Loan.id == identificador)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert prestamo is not None
    if prestamo.state not in (LoanState.ACTIVE, LoanState.OVERDUE):
        raise UseCaseError(409, "El préstamo ya fue devuelto")
    fecha = instante_utc(datos.returned_at, "Devolución") if datos.returned_at else ahora()
    if fecha < prestamo.starts_at or fecha > ahora():
        raise UseCaseError(422, "La devolución no puede ser futura ni anterior a la entrega")
    if datos.disposition == UnitState.LOANED:
        raise UseCaseError(422, "La unidad devuelta no puede seguir en estado prestada")
    prestamo.returned_at = fecha
    prestamo.returned_condition = datos.condition
    prestamo.returned_accessories = datos.accessories
    prestamo.unit_disposition = datos.disposition
    prestamo.closed_at = fecha
    prestamo.state = LoanState.RETURNED
    unidad.state = datos.disposition
    unidad.condition = datos.condition
    unidad.accessories = datos.accessories
    sesion.add(
        DevolucionDelPrestamo(
            id_prestamo=prestamo.id, fecha_devolucion=fecha, observaciones=datos.condition
        )
    )
    audit(
        sesion,
        actor,
        "PRESTAMO_DEVUELTO",
        "Prestamo",
        prestamo.id,
        {"destino": datos.disposition.value},
    )
    return prestamo


def salida_prestamo(sesion: Session, prestamo: Loan) -> LoanOut:
    solicitante = sesion.get(Solicitante, prestamo.applicant_id)
    persona = sesion.get(Person, solicitante.person_id) if solicitante else None
    administrador = sesion.get(Administrador, prestamo.administrator_id)
    cuenta = sesion.get(Account, administrador.account_id) if administrador else None
    unidad = sesion.get(PhysicalUnit, prestamo.unit_id)
    abierta = prestamo.state in (LoanState.ACTIVE, LoanState.OVERDUE)
    referencia = ahora() if abierta else (prestamo.returned_at or prestamo.due_at)
    retraso = max(0, int((referencia - prestamo.due_at).total_seconds() // 60))
    estado = LoanState.OVERDUE if abierta and referencia > prestamo.due_at else prestamo.state
    return LoanOut(
        id=prestamo.id,
        applicant_id=prestamo.applicant_id,
        administrator_id=prestamo.administrator_id,
        unit_id=prestamo.unit_id,
        origin_reservation_id=prestamo.origin_reservation_id,
        starts_at=prestamo.starts_at,
        due_at=prestamo.due_at,
        use_mode=prestamo.use_mode,
        state=estado,
        returned_at=prestamo.returned_at,
        returned_condition=prestamo.returned_condition,
        unit_code=unidad.inventory_code if unidad else str(prestamo.unit_id),
        applicant_name=persona.full_name if persona else "Solicitante",
        administrator_name=cuenta.person.full_name if cuenta else "Administrador",
        late_minutes=retraso,
        delivered_condition=prestamo.delivered_condition,
        delivered_accessories=prestamo.delivered_accessories,
        returned_accessories=prestamo.returned_accessories,
        applied_policy=prestamo.applied_policy,
    )
