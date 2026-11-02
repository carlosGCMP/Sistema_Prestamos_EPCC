"""Small application services for users, inventory, and reservations."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.schemas import ItemCreate, PersonCreate, UnitCreate
from app.core.security import hash_password
from app.infrastructure.modelos_sql import (
    CaracteristicaDelBien,
    HistorialDeCambios,
    PersonalAdministrativo,
    RegistroDeReserva,
    TipoDeEvento,
    UbicacionDelBien,
)
from app.infrastructure.models import (
    Account,
    Administrador,
    AuditEvent,
    Bien,
    Category,
    ItemCard,
    ItemType,
    Person,
    PersonState,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    Solicitante,
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
    entity_id: int | str,
    details: dict[str, Any] | None = None,
) -> None:
    tipo = session.scalar(
        select(TipoDeEvento).where(TipoDeEvento.nombre_tipo_evento == "OPERACION")
    )
    if tipo is None:
        raise UseCaseError(500, "Falta inicializar el catálogo de auditoría")
    evento = AuditEvent(
        actor_id=actor.account.id if actor and actor.account else None,
        event_type_id=tipo.id_tipo_evento,
        actor_type="USUARIO" if actor else "PROCESO_AUTOMATICO",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=details or {},
    )
    session.add(evento)
    session.flush()
    session.add(HistorialDeCambios(id_registro=evento.id, descripcion=action))


def create_person(session: Session, data: PersonCreate, actor: Person | None) -> Person:
    person = Person(
        cui=data.cui,
        document_type=data.document_type,
        document_number=data.document_number,
        first_names=data.first_names or data.full_name,
        last_names=data.last_names or "",
        phone=data.phone,
        institutional_email=data.institutional_email,
        role=data.role,
        school_affiliation=data.school_affiliation,
        start_date=data.start_date,
        end_date=data.end_date,
    )
    session.add(person)
    session.flush()

    person.account = Account(
        person_id=person.id,
        username=data.username,
        password_hash=hash_password(data.password),
    )
    session.flush()
    person.applicant = Solicitante(person_id=person.id, account_id=person.account.id)
    if data.is_admin:
        person.account.administrator = Administrador(account_id=person.account.id)
    session.flush()
    if data.role == Role.STUDENT:
        session.add(
            StudentProfile(
                person_id=person.id,
                applicant_id=person.applicant.id,
                university_code=data.student_code,
                program=data.program,
                semester=data.semester,
            )
        )
    elif data.role == Role.TEACHER:
        session.add(
            TeacherProfile(
                person_id=person.id,
                applicant_id=person.applicant.id,
                institutional_code=data.teacher_code,
                specialty=data.specialty,
                department=data.department,
                position=data.position,
            )
        )
    else:
        session.add(
            PersonalAdministrativo(
                id_solicitante=person.applicant.id,
                id_persona=person.id,
                codigo_personal=data.staff_code or data.document_number,
                departamento=data.department,
                cargo=data.position,
            )
        )
    audit(session, actor or person, "PERSONA_REGISTRADA", "Persona", person.id)
    return person


def new_category(
    session: Session, name: str, description: str | None, actor: Person, item_type_id: int
) -> Category:
    tipo = session.get(ItemType, item_type_id)
    if tipo is None or not tipo.active:
        raise UseCaseError(404, "Tipo de bien no encontrado o inactivo")
    category = Category(name=name, description=description, item_type_id=tipo.id)
    session.add(category)
    session.flush()
    audit(session, actor, "CATEGORIA_CREADA", "CategoriaDelBien", category.id)
    return category


def new_item_type(session: Session, name: str, lendable: bool, actor: Person) -> ItemType:
    item_type = ItemType(name=name, lendable=lendable)
    session.add(item_type)
    session.flush()
    audit(session, actor, "TIPO_BIEN_CREADO", "TipoDeBien", item_type.id)
    return item_type


def new_item(session: Session, data: ItemCreate, actor: Person) -> ItemCard:
    categoria = session.scalar(
        select(Category).where(Category.id == data.category_id).with_for_update()
    )
    if categoria is None or not categoria.active or not categoria.item_type.active:
        raise UseCaseError(404, "Categoría o tipo de bien no encontrado o inactivo")
    if actor.applicant is None:
        raise UseCaseError(409, "El responsable no tiene un registro de solicitante")
    item = ItemCard(
        bien=Bien(
            category_id=categoria.id,
            name=data.name,
            description=data.description,
            attributes=data.attributes,
        ),
        applicant_id=actor.applicant.id,
    )
    existentes = set(
        session.scalars(
            select(CaracteristicaDelBien.nombre_caracteristica).where(
                CaracteristicaDelBien.id_categoria == categoria.id
            )
        )
    )
    for nombre in data.attributes:
        if not nombre.strip() or len(nombre) > 100:
            raise UseCaseError(
                422, "El nombre de cada característica debe tener de 1 a 100 caracteres"
            )
        if nombre not in existentes:
            session.add(
                CaracteristicaDelBien(id_categoria=categoria.id, nombre_caracteristica=nombre)
            )
    session.add(item)
    session.flush()
    audit(session, actor, "FICHA_BIEN_CREADA", "FichaDeBien", item.id)
    return item


def new_unit(session: Session, data: UnitCreate, actor: Person) -> PhysicalUnit:
    item = session.get(ItemCard, data.item_card_id)
    if item is None or not item.active:
        raise UseCaseError(404, "Ficha de bien no encontrada o inactiva")
    if session.scalar(select(PhysicalUnit.id).where(PhysicalUnit.item_card_id == item.id)):
        raise UseCaseError(409, "La ficha ya tiene una unidad física; registra una ficha nueva")
    unit = PhysicalUnit(
        item_card_id=item.id,
        inventory_code=data.inventory_code,
        serial_number=data.serial_number,
        location=data.location,
        custody=data.custody,
        condition=data.condition,
        accessories=data.accessories,
        acquisition_date=data.acquisition_date,
    )
    session.add(unit)
    session.flush()
    session.add(UbicacionDelBien(id_unidad_fisica=unit.id, ubicacion=unit.location))
    audit(session, actor, "UNIDAD_FISICA_CREADA", "UnidadFisica", unit.id)
    return unit


def create_reservation(
    session: Session,
    applicant: Person,
    unit_id: int,
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
        or applicant.applicant is None
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
        applicant_id=applicant.applicant.id,
        unit_id=unit.id,
        starts_at=starts_at,
        ends_at=ends_at,
        intended_use=intended_use,
    )
    session.add(reservation)
    session.flush()
    audit(session, applicant, "RESERVA_SOLICITADA", "SolicitudDeReserva", reservation.id)
    return reservation


def _active_person(session: Session, applicant_id: int) -> Person:
    solicitante = session.get(Solicitante, applicant_id)
    if solicitante is None:
        raise UseCaseError(409, "Solicitante no encontrado")
    person = session.scalar(
        select(Person)
        .where(Person.id == solicitante.person_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if person is None or person.state != PersonState.ACTIVE:
        raise UseCaseError(409, "La persona solicitante no está activa")
    return person


def _active_unit(session: Session, unit_id: int) -> PhysicalUnit:
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
    reservation_id: int,
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
        session.add(
            RegistroDeReserva(
                id_solicitud=reservation.id,
                id_solicitante=reservation.applicant_id,
                id_unidad_fisica=reservation.unit_id,
                fecha_reserva=reservation.starts_at,
                fecha_expiracion=reservation.ends_at,
                estado=ReservationState.CONFIRMED.value,
            )
        )
    else:
        reservation.state = ReservationState.REJECTED
        reservation.decision_reason = reason

    audit(
        session,
        administrator,
        "RESERVA_CONFIRMADA" if confirm else "RESERVA_RECHAZADA",
        "SolicitudDeReserva",
        reservation.id,
        {"reason": reason} if reason else {},
    )
    return reservation


def cancel_reservation(
    session: Session, reservation_id: int, actor: Person, reason: str | None
) -> Reservation:
    reservation = session.scalar(
        select(Reservation)
        .where(Reservation.id == reservation_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if reservation is None:
        raise UseCaseError(404, "Reserva no encontrada")
    titular = actor.applicant is not None and reservation.applicant_id == actor.applicant.id
    if not titular and not actor.is_admin:
        raise UseCaseError(403, "Solo el titular o personal autorizado puede cancelar la reserva")
    if reservation.state not in (ReservationState.PENDING, ReservationState.CONFIRMED):
        raise UseCaseError(409, "La reserva ya no puede cancelarse")
    reservation.state = ReservationState.CANCELLED
    reservation.decision_reason = reason
    registro = session.scalar(
        select(RegistroDeReserva).where(RegistroDeReserva.id_solicitud == reservation.id)
    )
    if registro is not None:
        registro.estado = ReservationState.CANCELLED.value
    audit(session, actor, "RESERVA_CANCELADA", "SolicitudDeReserva", reservation.id)
    return reservation
