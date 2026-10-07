from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AcademicRecord,
    Account,
    AuditEvent,
    Category,
    ItemCard,
    ItemType,
    Loan,
    LoanPolicy,
    LoanState,
    Person,
    PersonState,
    PhysicalUnit,
    Renewal,
    Reservation,
    ReservationState,
    Role,
    StudentProfile,
    TeacherProfile,
    TimeUnit,
    UnitState,
)
from app.schemas import PersonCreate, PolicyCreate
from app.security import hash_password


class UseCaseError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def now_utc() -> datetime:
    return datetime.now(UTC)


def require_aware(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise UseCaseError(422, f"{field_name} debe incluir zona horaria")
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


def active_person(session: Session, person_id: UUID, *, lock: bool = False) -> Person:
    statement = select(Person).where(Person.id == person_id)
    if lock:
        statement = statement.with_for_update()
    person = session.scalar(statement)
    if person is None:
        raise UseCaseError(404, "Persona no encontrada")
    if person.state != PersonState.ACTIVE:
        raise UseCaseError(409, "La persona está inactiva")
    return person


def active_unit(session: Session, unit_id: UUID, *, lock: bool = False) -> PhysicalUnit:
    statement = select(PhysicalUnit).where(PhysicalUnit.id == unit_id)
    if lock:
        statement = statement.with_for_update()
    unit = session.scalar(statement)
    if unit is None:
        raise UseCaseError(404, "Unidad física no encontrada")
    if unit.state in (UnitState.MAINTENANCE, UnitState.RETIRED):
        raise UseCaseError(409, "La unidad no se encuentra habilitada para préstamo")
    return unit


def resolve_policy(
    session: Session,
    role: Role,
    item_type_id: UUID,
    at: datetime,
    *,
    limit_only: bool = False,
) -> LoanPolicy:
    at = require_aware(at, "at")
    query = select(LoanPolicy).where(
        LoanPolicy.active.is_(True),
        LoanPolicy.valid_from <= at,
        (LoanPolicy.valid_until.is_(None) | (LoanPolicy.valid_until > at)),
    )
    if limit_only:
        query = query.where(LoanPolicy.item_type_id.is_(None))
    else:
        query = query.where(
            (LoanPolicy.item_type_id == item_type_id) | LoanPolicy.item_type_id.is_(None)
        )
    policies = session.scalars(query).all()
    priorities = (
        ((role, item_type_id), (role, None), (None, None))
        if not limit_only
        else ((role, None), (None, None))
    )
    for target_role, target_type in priorities:
        matching = [p for p in policies if p.role == target_role and p.item_type_id == target_type]
        if matching:
            return max(matching, key=lambda item: item.version)
    raise UseCaseError(409, "No existe una política aprobada aplicable")


def max_duration_delta(policy: LoanPolicy) -> timedelta:
    if policy.duration_unit == TimeUnit.HOURS:
        return timedelta(hours=policy.max_duration)
    return timedelta(days=policy.max_duration)


def assert_eligible(session: Session, person: Person, policy: LoanPolicy, at: datetime) -> None:
    if person.role not in (Role.STUDENT, Role.TEACHER):
        raise UseCaseError(403, "El rol de personal administrativo no puede solicitar préstamos")
    if person.account is None or not person.account.active:
        raise UseCaseError(409, "La persona no tiene una cuenta activa")
    if policy.requires_academic_eligibility and person.role == Role.STUDENT:
        record = session.get(AcademicRecord, person.id)
        if (
            record is None
            or record.status.upper() not in {"MATRICULADO", "VIGENTE", "ACTIVO"}
            or (record.valid_until and require_aware(record.valid_until, "valid_until") <= at)
        ):
            raise UseCaseError(409, "La condición académica del solicitante no está vigente")


def assert_unit_type_lendable(session: Session, unit: PhysicalUnit) -> ItemType:
    item = session.get(ItemCard, unit.item_card_id)
    if item is None or not item.active:
        raise UseCaseError(409, "La ficha del bien está inactiva")
    item_type = session.get(ItemType, item.item_type_id)
    if item_type is None or not item_type.active or not item_type.lendable:
        raise UseCaseError(409, "El tipo de bien no está habilitado para préstamo")
    return item_type


def ensure_no_unit_conflict(
    session: Session,
    unit_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    *,
    except_reservation_id: UUID | None = None,
    except_loan_id: UUID | None = None,
) -> None:
    overlap = (Reservation.starts_at < ends_at) & (Reservation.ends_at > starts_at)
    statement = select(Reservation.id).where(
        Reservation.unit_id == unit_id,
        Reservation.state == ReservationState.CONFIRMED,
        overlap,
    )
    if except_reservation_id:
        statement = statement.where(Reservation.id != except_reservation_id)
    if session.scalar(statement.limit(1)) is not None:
        raise UseCaseError(409, "El intervalo se cruza con una reserva confirmada")

    # Open loans remain commitments until an actual return or loss closure, even if overdue.
    open_loan_query = select(Loan.id).where(
        Loan.unit_id == unit_id,
        Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE)),
    )
    if except_loan_id:
        open_loan_query = open_loan_query.where(Loan.id != except_loan_id)
    if session.scalar(open_loan_query.limit(1)) is not None:
        raise UseCaseError(409, "La unidad tiene un préstamo abierto")


def assert_applicant_capacity(
    session: Session,
    applicant_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    max_units: int,
    *,
    except_reservation_id: UUID | None = None,
    except_loan_id: UUID | None = None,
) -> None:
    events: list[tuple[datetime, int]] = [(starts_at, 1), (ends_at, -1)]
    open_loan_query = select(Loan).where(
        Loan.applicant_id == applicant_id,
        Loan.state.in_((LoanState.ACTIVE, LoanState.OVERDUE)),
    )
    if except_loan_id:
        open_loan_query = open_loan_query.where(Loan.id != except_loan_id)
    open_loans = session.scalars(open_loan_query).all()
    for _loan in open_loans:
        events.extend(((starts_at, 1), (ends_at, -1)))
    reservations = session.scalars(
        select(Reservation).where(
            Reservation.applicant_id == applicant_id,
            Reservation.state == ReservationState.CONFIRMED,
            Reservation.starts_at < ends_at,
            Reservation.ends_at > starts_at,
        )
    ).all()
    for reservation in reservations:
        if reservation.id == except_reservation_id:
            continue
        clipped_start = max(
            starts_at, require_aware(reservation.starts_at, "reservation.starts_at")
        )
        clipped_end = min(ends_at, require_aware(reservation.ends_at, "reservation.ends_at"))
        events.extend(((clipped_start, 1), (clipped_end, -1)))
    events.sort(key=lambda event: (event[0], event[1]))  # Ends precede starts for [start, end).
    concurrent = 0
    for _instant, delta in events:
        concurrent += delta
        if concurrent > max_units:
            raise UseCaseError(409, "El solicitante excedería el cupo durante el intervalo")


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
    if data.username and data.password:
        account = Account(
            person_id=person.id,
            username=data.username,
            password_hash=hash_password(data.password),
        )
        session.add(account)
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
    if data.academic_status and data.academic_term:
        session.add(
            AcademicRecord(
                person_id=person.id,
                status=data.academic_status,
                term=data.academic_term,
            )
        )
    audit(session, actor, "PERSONA_REGISTRADA", "Persona", person.id, {"role": person.role.value})
    return person


def policy_snapshot(policy: LoanPolicy) -> dict[str, Any]:
    return {
        "policy_id": str(policy.id),
        "version": policy.version,
        "name": policy.name,
        "max_duration": policy.max_duration,
        "duration_unit": policy.duration_unit.value,
        "max_units": policy.max_units,
        "allowed_modes": policy.allowed_modes,
        "requires_academic_eligibility": policy.requires_academic_eligibility,
        "guarantee_required": policy.guarantee_required,
        "allows_renewal": policy.allows_renewal,
        "max_renewals": policy.max_renewals,
        "late_grace_minutes": policy.late_grace_minutes,
        "fine_per_day": str(policy.fine_per_day),
    }


def create_policy(session: Session, data: PolicyCreate, actor: Person) -> LoanPolicy:
    valid_from = require_aware(data.valid_from, "valid_from")
    valid_until = require_aware(data.valid_until, "valid_until") if data.valid_until else None
    if valid_until and valid_until <= valid_from:
        raise UseCaseError(422, "valid_until debe ser posterior a valid_from")
    if not data.allows_renewal and data.max_renewals:
        raise UseCaseError(
            422, "max_renewals debe ser cero cuando las renovaciones están deshabilitadas"
        )
    all_versions = session.scalars(
        select(LoanPolicy).where(
            LoanPolicy.role == data.role,
            LoanPolicy.item_type_id == data.item_type_id,
        )
    ).all()
    version = max((policy.version for policy in all_versions), default=0) + 1
    current = [
        policy
        for policy in all_versions
        if policy.active
        and (
            policy.valid_until is None
            or require_aware(policy.valid_until, "valid_until") > valid_from
        )
    ]
    for policy in current:
        if (
            policy.valid_until is None
            or require_aware(policy.valid_until, "valid_until") > valid_from
        ):
            if require_aware(policy.valid_from, "valid_from") >= valid_from:
                raise UseCaseError(
                    409, "La nueva versión debe iniciar después de la versión vigente"
                )
            policy.valid_until = valid_from
            policy.active = False
    policy = LoanPolicy(
        name=data.name,
        role=data.role,
        item_type_id=data.item_type_id,
        version=version,
        max_units=data.max_units,
        max_duration=data.max_duration,
        duration_unit=data.duration_unit,
        allowed_modes=[mode.value for mode in data.allowed_modes],
        requires_academic_eligibility=data.requires_academic_eligibility,
        allows_renewal=data.allows_renewal,
        max_renewals=data.max_renewals,
        late_grace_minutes=data.late_grace_minutes,
        fine_per_day=data.fine_per_day or Decimal("0"),
        valid_from=valid_from,
        valid_until=valid_until,
    )
    session.add(policy)
    session.flush()
    audit(session, actor, "POLITICA_CREADA", "LoanPolicy", policy.id, {"version": version})
    return policy


def create_reservation(
    session: Session,
    applicant: Person,
    unit_id: UUID,
    starts_at: datetime,
    ends_at: datetime,
    use: str,
) -> Reservation:
    starts_at = require_aware(starts_at, "starts_at")
    ends_at = require_aware(ends_at, "ends_at")
    now = now_utc()
    if starts_at <= now or ends_at <= starts_at:
        raise UseCaseError(422, "La reserva debe tener un intervalo futuro válido")
    unit = active_unit(session, unit_id)
    item_type = assert_unit_type_lendable(session, unit)
    policy = resolve_policy(session, applicant.role, item_type.id, starts_at)
    assert_eligible(session, applicant, policy, starts_at)
    if ends_at - starts_at > max_duration_delta(policy):
        raise UseCaseError(422, "La reserva supera la duración máxima permitida")
    reservation = Reservation(
        applicant_id=applicant.id,
        unit_id=unit.id,
        starts_at=starts_at,
        ends_at=ends_at,
        intended_use=use,
    )
    session.add(reservation)
    session.flush()
    audit(session, applicant, "RESERVA_SOLICITADA", "Reservation", reservation.id)
    return reservation


def decide_reservation(
    session: Session, reservation_id: UUID, administrator: Person, confirm: bool, reason: str | None
) -> Reservation:
    reservation = session.scalar(
        select(Reservation).where(Reservation.id == reservation_id).with_for_update()
    )
    if reservation is None:
        raise UseCaseError(404, "Reserva no encontrada")
    if reservation.state != ReservationState.PENDING:
        raise UseCaseError(409, "Solo se pueden decidir reservas pendientes")
    if not confirm and not reason:
        raise UseCaseError(422, "El rechazo requiere un motivo")
    if confirm:
        unit = active_unit(session, reservation.unit_id, lock=True)
        item_type = assert_unit_type_lendable(session, unit)
        applicant = active_person(session, reservation.applicant_id, lock=True)
        policy = resolve_policy(
            session,
            applicant.role,
            item_type.id,
            require_aware(reservation.starts_at, "starts_at"),
        )
        assert_eligible(
            session,
            applicant,
            policy,
            require_aware(reservation.starts_at, "starts_at"),
        )
        ensure_no_unit_conflict(
            session,
            unit.id,
            require_aware(reservation.starts_at, "starts_at"),
            require_aware(reservation.ends_at, "ends_at"),
        )
        limit_policy = resolve_policy(
            session,
            applicant.role,
            item_type.id,
            require_aware(reservation.starts_at, "starts_at"),
            limit_only=True,
        )
        assert_applicant_capacity(
            session,
            reservation.applicant_id,
            require_aware(reservation.starts_at, "starts_at"),
            require_aware(reservation.ends_at, "ends_at"),
            limit_policy.max_units,
        )
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
        select(Reservation).where(Reservation.id == reservation_id).with_for_update()
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


def create_loan(session: Session, data: Any, administrator: Person) -> Loan:
    starts_at = now_utc()
    due_at = require_aware(data.due_at, "due_at")
    if due_at <= starts_at:
        raise UseCaseError(422, "El vencimiento debe ser posterior a la entrega")
    unit = active_unit(session, data.unit_id, lock=True)
    if unit.state != UnitState.AVAILABLE:
        raise UseCaseError(409, "La unidad no está disponible para entrega")
    # Serialize cupo checks even when concurrent requests target distinct units.
    applicant = active_person(session, data.applicant_id, lock=True)
    item_type = assert_unit_type_lendable(session, unit)
    policy = resolve_policy(session, applicant.role, item_type.id, starts_at)
    assert_eligible(session, applicant, policy, starts_at)
    if data.use_mode.value not in policy.allowed_modes:
        raise UseCaseError(409, "La modalidad de uso no está permitida por la política")
    if due_at > starts_at + max_duration_delta(policy):
        raise UseCaseError(422, "El vencimiento supera la duración máxima de la política")
    reservation = None
    if data.origin_reservation_id:
        reservation = session.scalar(
            select(Reservation)
            .where(Reservation.id == data.origin_reservation_id)
            .with_for_update()
        )
        if (
            reservation is None
            or reservation.state != ReservationState.CONFIRMED
            or reservation.unit_id != unit.id
            or reservation.applicant_id != applicant.id
            or not (
                require_aware(reservation.starts_at, "starts_at")
                <= starts_at
                < require_aware(reservation.ends_at, "ends_at")
            )
        ):
            raise UseCaseError(409, "La reserva no está vigente o no corresponde a esta entrega")
        if due_at > require_aware(reservation.ends_at, "ends_at"):
            raise UseCaseError(422, "El préstamo no puede superar el fin de la reserva")
    ensure_no_unit_conflict(
        session,
        unit.id,
        starts_at,
        due_at,
        except_reservation_id=reservation.id if reservation else None,
    )
    limit_policy = resolve_policy(session, applicant.role, item_type.id, starts_at, limit_only=True)
    assert_applicant_capacity(
        session,
        applicant.id,
        starts_at,
        due_at,
        limit_policy.max_units,
        except_reservation_id=reservation.id if reservation else None,
    )
    loan = Loan(
        applicant_id=applicant.id,
        administrator_id=administrator.id,
        unit_id=unit.id,
        origin_reservation_id=reservation.id if reservation else None,
        starts_at=starts_at,
        due_at=due_at,
        use_mode=data.use_mode,
        delivered_condition=data.delivered_condition,
        delivered_accessories=data.delivered_accessories,
        applied_policy=policy_snapshot(policy),
    )
    unit.state = UnitState.LOANED
    if reservation:
        reservation.state = ReservationState.FULFILLED
    session.add(loan)
    session.flush()
    audit(
        session,
        administrator,
        "PRESTAMO_ENTREGADO",
        "Loan",
        loan.id,
        {"unit_id": str(unit.id), "applicant_id": str(applicant.id)},
    )
    return loan


def renew_loan(
    session: Session, loan_id: UUID, new_due_at: datetime, administrator: Person
) -> Renewal:
    loan = session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise UseCaseError(404, "Préstamo no encontrado")
    if loan.state != LoanState.ACTIVE:
        raise UseCaseError(409, "Solo se puede renovar un préstamo activo")
    now = now_utc()
    old_due = require_aware(loan.due_at, "due_at")
    new_due = require_aware(new_due_at, "new_due_at")
    if now >= old_due:
        raise UseCaseError(409, "La renovación debe autorizarse antes del vencimiento")
    policy = loan.applied_policy
    renewal_count = len(loan.renewals)
    if not policy["allows_renewal"] or renewal_count >= policy["max_renewals"]:
        raise UseCaseError(409, "La política del préstamo no permite más renovaciones")
    if new_due <= old_due or new_due > old_due + timedelta(
        hours=policy["max_duration"]
        if policy["duration_unit"] == TimeUnit.HOURS.value
        else policy["max_duration"] * 24
    ):
        raise UseCaseError(422, "La nueva fecha excede las condiciones conservadas")
    unit = active_unit(session, loan.unit_id, lock=True)
    item_type = assert_unit_type_lendable(session, unit)
    applicant = active_person(session, loan.applicant_id, lock=True)
    cap_policy = resolve_policy(session, applicant.role, item_type.id, now, limit_only=True)
    ensure_no_unit_conflict(session, loan.unit_id, old_due, new_due, except_loan_id=loan.id)
    assert_applicant_capacity(
        session,
        loan.applicant_id,
        old_due,
        new_due,
        cap_policy.max_units,
        except_loan_id=loan.id,
    )
    renewal = Renewal(
        loan_id=loan.id,
        sequence=renewal_count + 1,
        previous_due_at=old_due,
        new_due_at=new_due,
        administrator_id=administrator.id,
    )
    loan.due_at = new_due
    session.add(renewal)
    session.flush()
    audit(
        session,
        administrator,
        "PRESTAMO_RENOVADO",
        "Loan",
        loan.id,
        {"previous_due_at": old_due.isoformat(), "new_due_at": new_due.isoformat()},
    )
    return renewal


def return_loan(session: Session, loan_id: UUID, data: Any, administrator: Person) -> Loan:
    loan = session.scalar(select(Loan).where(Loan.id == loan_id).with_for_update())
    if loan is None:
        raise UseCaseError(404, "Préstamo no encontrado")
    if loan.state not in (LoanState.ACTIVE, LoanState.OVERDUE):
        raise UseCaseError(409, "El préstamo ya está cerrado")
    unit = active_unit(session, loan.unit_id, lock=True)
    returned_at = require_aware(data.returned_at, "returned_at") if data.returned_at else now_utc()
    starts_at = require_aware(loan.starts_at, "starts_at")
    if returned_at < starts_at:
        raise UseCaseError(422, "La devolución no puede anteceder a la entrega")
    if data.disposition == UnitState.LOANED:
        raise UseCaseError(422, "La unidad no puede conservar estado prestada tras la devolución")
    loan.returned_at = returned_at
    loan.returned_condition = data.condition
    loan.returned_accessories = data.accessories
    loan.unit_disposition = data.disposition
    loan.state = LoanState.RETURNED
    loan.closed_at = returned_at
    unit.state = data.disposition
    session.flush()
    audit(
        session,
        administrator,
        "PRESTAMO_DEVUELTO",
        "Loan",
        loan.id,
        {"unit_disposition": data.disposition.value},
    )
    return loan


def new_category(session: Session, name: str, description: str | None, actor: Person) -> Category:
    category = Category(name=name, description=description)
    session.add(category)
    session.flush()
    audit(session, actor, "CATEGORIA_CREADA", "Category", category.id)
    return category


def new_item_type(
    session: Session, name: str, category_id: UUID, lendable: bool, actor: Person
) -> ItemType:
    if session.get(Category, category_id) is None:
        raise UseCaseError(404, "Categoría no encontrada")
    item_type = ItemType(name=name, category_id=category_id, lendable=lendable)
    session.add(item_type)
    session.flush()
    audit(session, actor, "TIPO_BIEN_CREADO", "ItemType", item_type.id)
    return item_type


def new_item(session: Session, data: Any, actor: Person) -> ItemCard:
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


def new_unit(session: Session, data: Any, actor: Person) -> PhysicalUnit:
    item = session.get(ItemCard, data.item_card_id)
    if item is None or not item.active:
        raise UseCaseError(404, "Ficha de bien no encontrada o inactiva")
    unit = PhysicalUnit(
        item_card_id=data.item_card_id,
        inventory_code=data.inventory_code,
        serial_number=data.serial_number,
        location=data.location,
        custody=data.custody,
        condition=data.condition,
        accessories=data.accessories,
    )
    session.add(unit)
    session.flush()
    audit(
        session,
        actor,
        "UNIDAD_FISICA_CREADA",
        "PhysicalUnit",
        unit.id,
        {"inventory_code": unit.inventory_code},
    )
    return unit
