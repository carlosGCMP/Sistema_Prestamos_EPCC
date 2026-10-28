"""Small application services for users, inventory, and reservations."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas import ItemCreate, PersonCreate, UnitCreate
from app.core.security import hash_password
from app.infrastructure.models import (
    Account,
    AuditEvent,
    Category,
    ItemCard,
    ItemType,
    Person,
    PersonState,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    StudentProfile,
    TeacherProfile,
    UnitState,
)


class UseCaseError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _aware_utc(value: datetime, field: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise UseCaseError(422, f"{field} debe incluir zona horaria")
    return value.astimezone(UTC)


def audit(
    session: Session,
    actor: Person | None,
    action: str,
    entity_type: str,
    entity_id: UUID | str,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditEvent(
            actor_id=actor.id if actor else None,
            actor_type="USUARIO" if actor else "PROCESO_AUTOMATICO",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details or {},
        )
    )


def create_person(session: Session, data: PersonCreate, actor: Person) -> Person:
    person = Person(
        cui=data.cui,
        document_type=data.document_type,
        document_number=data.document_number,
        full_name=data.full_name,
        institutional_email=data.institutional_email,
        role=data.role,
        school_affiliation=data.school_affiliation,
        start_date=data.start_date,
    )
    session.add(person)
    session.flush()

    session.add(
        Account(
            person_id=person.id,
            username=data.username,
            password_hash=hash_password(data.password),
        )
    )
    if data.role == Role.STUDENT:
        session.add(
            StudentProfile(
                person_id=person.id,
                university_code=data.student_code,
                program=data.program,
                semester=data.semester,
            )
        )
    elif data.role == Role.TEACHER:
        session.add(
            TeacherProfile(
                person_id=person.id,
                institutional_code=data.teacher_code,
                specialty=data.specialty,
            )
        )
    audit(session, actor, "PERSONA_REGISTRADA", "Person", person.id)
    return person


def new_category(session: Session, name: str, description: str | None, actor: Person) -> Category:
    category = Category(name=name, description=description)
    session.add(category)
    session.flush()
    audit(session, actor, "CATEGORIA_CREADA", "Category", category.id)
    return category


def new_item_type(
    session: Session, name: str, category_id: UUID, lendable: bool, actor: Person
) -> ItemType:
    category = session.get(Category, category_id)
    if category is None or not category.active:
        raise UseCaseError(404, "Categoría no encontrada o inactiva")
    item_type = ItemType(name=name, category_id=category.id, lendable=lendable)
    session.add(item_type)
    session.flush()
    audit(session, actor, "TIPO_BIEN_CREADO", "ItemType", item_type.id)
    return item_type


def new_item(session: Session, data: ItemCreate, actor: Person) -> ItemCard:
    item_type = session.get(ItemType, data.item_type_id)
    if item_type is None or not item_type.active:
        raise UseCaseError(404, "Tipo de bien no encontrado o inactivo")
    item = ItemCard(
        item_type_id=item_type.id,
        name=data.name,
        description=data.description,
        attributes=data.attributes,
    )
    session.add(item)
    session.flush()
    audit(session, actor, "FICHA_BIEN_CREADA", "ItemCard", item.id)
    return item


def new_unit(session: Session, data: UnitCreate, actor: Person) -> PhysicalUnit:
    item = session.get(ItemCard, data.item_card_id)
    if item is None or not item.active:
        raise UseCaseError(404, "Ficha de bien no encontrada o inactiva")
    unit = PhysicalUnit(
        item_card_id=item.id,
        inventory_code=data.inventory_code,
        serial_number=data.serial_number,
        location=data.location,
        custody=data.custody,
        condition=data.condition,
        accessories=data.accessories,
    )
    session.add(unit)
    session.flush()
    audit(session, actor, "UNIDAD_FISICA_CREADA", "PhysicalUnit", unit.id)
    return unit


def create_reservation(
    session: Session,
    applicant: Person,
    unit_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    intended_use: str,
) -> Reservation:
    starts_at = _aware_utc(starts_at, "starts_at")
    ends_at = _aware_utc(ends_at, "ends_at")
    if starts_at <= datetime.now(UTC) or ends_at <= starts_at:
        raise UseCaseError(422, "La reserva debe tener un intervalo futuro válido")
    if applicant.role not in (Role.STUDENT, Role.TEACHER):
        raise UseCaseError(403, "Solo estudiantes y docentes pueden solicitar reservas")
    if (
        applicant.state != PersonState.ACTIVE
        or applicant.account is None
        or not applicant.account.active
    ):
        raise UseCaseError(409, "Se requiere una cuenta de usuario activa")

    unit = session.get(PhysicalUnit, unit_id)
    if unit is None:
        raise UseCaseError(404, "Unidad física no encontrada")
    item = session.get(ItemCard, unit.item_card_id)
    item_type = session.get(ItemType, item.item_type_id) if item is not None else None
    if (
        unit.state != UnitState.AVAILABLE
        or item is None
        or not item.active
        or item_type is None
        or not item_type.active
        or not item_type.lendable
    ):
        raise UseCaseError(409, "La unidad no está disponible para reservar")

    reservation = Reservation(
        applicant_id=applicant.id,
        unit_id=unit.id,
        starts_at=starts_at,
        ends_at=ends_at,
        intended_use=intended_use,
    )
    session.add(reservation)
    session.flush()
    audit(session, applicant, "RESERVA_SOLICITADA", "Reservation", reservation.id)
    return reservation


def _active_person(session: Session, person_id: UUID) -> Person:
    person = session.scalar(
        select(Person)
        .where(Person.id == person_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if person is None or person.state != PersonState.ACTIVE:
        raise UseCaseError(409, "La persona solicitante no está activa")
    return person


def _active_unit(session: Session, unit_id: UUID) -> PhysicalUnit:
    unit = session.scalar(
        select(PhysicalUnit)
        .where(PhysicalUnit.id == unit_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if unit is None:
        raise UseCaseError(404, "Unidad física no encontrada")
    if unit.state != UnitState.AVAILABLE:
        raise UseCaseError(409, "La unidad no está disponible")
    return unit


def decide_reservation(
    session: Session,
    reservation_id: UUID,
    administrator: Person,
    confirm: bool,
    reason: str | None,
) -> Reservation:
    existing = session.get(Reservation, reservation_id)
    if existing is None:
        raise UseCaseError(404, "Reserva no encontrada")

    applicant: Person | None = None
    unit: PhysicalUnit | None = None
    if confirm:
        applicant = _active_person(session, existing.applicant_id)
        if applicant.account is None or not applicant.account.active:
            raise UseCaseError(409, "La persona solicitante no tiene cuenta activa")
        unit = _active_unit(session, existing.unit_id)

    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if reservation is None:
        raise UseCaseError(404, "Reserva no encontrada")
    if reservation.state != ReservationState.PENDING:
        raise UseCaseError(409, "Solo se pueden decidir reservas pendientes")
    if not confirm and not reason:
        raise UseCaseError(422, "El rechazo requiere un motivo")

    if confirm:
        assert unit is not None
        starts_at = _aware_utc(reservation.starts_at, "starts_at")
        ends_at = _aware_utc(reservation.ends_at, "ends_at")
        if ends_at <= datetime.now(UTC):
            raise UseCaseError(409, "La reserva ya venció")
        conflict = session.scalar(
            select(Reservation.id)
            .where(
                Reservation.unit_id == unit.id,
                Reservation.id != reservation.id,
                Reservation.state == ReservationState.CONFIRMED,
                Reservation.starts_at < ends_at,
                Reservation.ends_at > starts_at,
            )
            .limit(1)
        )
        if conflict is not None:
            raise UseCaseError(409, "La unidad ya tiene una reserva confirmada en ese intervalo")
        item = session.get(ItemCard, unit.item_card_id)
        item_type = session.get(ItemType, item.item_type_id) if item is not None else None
        if (
            item is None
            or not item.active
            or item_type is None
            or not item_type.active
            or not item_type.lendable
        ):
            raise UseCaseError(409, "La unidad no está habilitada para reservas")
        reservation.state = ReservationState.CONFIRMED
    else:
        reservation.state = ReservationState.REJECTED
        reservation.decision_reason = reason

    audit(
        session,
        administrator,
        "RESERVA_CONFIRMADA" if confirm else "RESERVA_RECHAZADA",
        "Reservation",
        reservation.id,
        {"reason": reason} if reason else {},
    )
    return reservation


def cancel_reservation(
    session: Session, reservation_id: UUID, actor: Person, reason: str | None
) -> Reservation:
    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if reservation is None:
        raise UseCaseError(404, "Reserva no encontrada")
    if reservation.applicant_id != actor.id and actor.role != Role.INVENTORY_ADMIN:
        raise UseCaseError(403, "Solo el titular o personal autorizado puede cancelar la reserva")
    if reservation.state not in (ReservationState.PENDING, ReservationState.CONFIRMED):
        raise UseCaseError(409, "La reserva ya no puede cancelarse")
    reservation.state = ReservationState.CANCELLED
    reservation.decision_reason = reason
    audit(session, actor, "RESERVA_CANCELADA", "Reservation", reservation.id)
    return reservation
