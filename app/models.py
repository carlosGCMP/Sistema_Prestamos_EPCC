"""Persistence models for the first operational slice of the domain."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Role(StrEnum):
    STUDENT = "ESTUDIANTE"
    TEACHER = "DOCENTE"
    ADMIN = "PERSONAL_ADMINISTRATIVO"


class PersonState(StrEnum):
    ACTIVE = "ACTIVA"
    INACTIVE = "INACTIVA"


class UnitState(StrEnum):
    AVAILABLE = "DISPONIBLE"
    LOANED = "PRESTADA"
    MAINTENANCE = "MANTENIMIENTO"
    RETIRED = "BAJA"


class ReservationState(StrEnum):
    PENDING = "PENDIENTE"
    CONFIRMED = "CONFIRMADA"
    REJECTED = "RECHAZADA"
    CANCELLED = "CANCELADA"
    FULFILLED = "ATENDIDA"
    EXPIRED = "VENCIDA"


class LoanState(StrEnum):
    ACTIVE = "ACTIVO"
    OVERDUE = "VENCIDO"
    RETURNED = "DEVUELTO"
    LOST = "CERRADO_POR_PERDIDA"


class UseMode(StrEnum):
    ON_SITE = "EN_SITIO"
    TAKE_HOME = "RETIRO"


class TimeUnit(StrEnum):
    HOURS = "HORAS"
    DAYS = "DIAS"


def enum_type(enum_class: type[StrEnum], name: str) -> Enum:
    return Enum(enum_class, name=name, values_callable=lambda items: [item.value for item in items])


class UTCDateTime(TypeDecorator[datetime]):
    """Store timezone-aware UTC instants; normalize SQLite's naive result values for tests."""

    impl = DateTime
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        return dialect.type_descriptor(DateTime(timezone=True))

    def process_bind_param(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Los instantes deben incluir zona horaria")
        return value.astimezone(UTC)

    def process_result_value(self, value: datetime | None, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Person(Base):
    __tablename__ = "personas"
    __table_args__ = (
        UniqueConstraint("document_type", "document_number", name="uq_person_document"),
        CheckConstraint("end_date IS NULL OR end_date > start_date", name="ck_person_dates"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    cui: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    document_type: Mapped[str] = mapped_column(String(20))
    document_number: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(200))
    institutional_email: Mapped[str] = mapped_column(String(150), unique=True)
    role: Mapped[Role] = mapped_column(enum_type(Role, "person_role"))
    school_affiliation: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[PersonState] = mapped_column(
        enum_type(PersonState, "person_state"), default=PersonState.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())

    account: Mapped[Account | None] = relationship(back_populates="person", uselist=False)
    student_profile: Mapped[StudentProfile | None] = relationship(
        back_populates="person", uselist=False
    )
    teacher_profile: Mapped[TeacherProfile | None] = relationship(
        back_populates="person", uselist=False
    )
    academic_record: Mapped[AcademicRecord | None] = relationship(
        back_populates="person", uselist=False
    )


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    person_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), unique=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    person: Mapped[Person] = relationship(back_populates="account")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    person_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), primary_key=True)
    university_code: Mapped[str] = mapped_column(String(30), unique=True)
    program: Mapped[str] = mapped_column(String(120))
    semester: Mapped[int] = mapped_column(Integer)
    person: Mapped[Person] = relationship(back_populates="student_profile")


class TeacherProfile(Base):
    __tablename__ = "teacher_profiles"

    person_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), primary_key=True)
    institutional_code: Mapped[str] = mapped_column(String(30), unique=True)
    specialty: Mapped[str] = mapped_column(String(120))
    person: Mapped[Person] = relationship(back_populates="teacher_profile")


class AcademicRecord(Base):
    """Manually maintained eligibility snapshot until institutional integration exists."""

    __tablename__ = "academic_records"

    person_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(30))
    term: Mapped[str] = mapped_column(String(30))
    checked_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    person: Mapped[Person] = relationship(back_populates="academic_record")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    item_types: Mapped[list[ItemType]] = relationship(back_populates="category")


class ItemType(Base):
    __tablename__ = "item_types"
    __table_args__ = (UniqueConstraint("category_id", "name", name="uq_type_category_name"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    category_id: Mapped[UUID] = mapped_column(ForeignKey("categories.id"))
    name: Mapped[str] = mapped_column(String(120))
    lendable: Mapped[bool] = mapped_column(Boolean, default=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    category: Mapped[Category] = relationship(back_populates="item_types")
    items: Mapped[list[ItemCard]] = relationship(back_populates="item_type")


class ItemCard(Base):
    __tablename__ = "item_cards"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    item_type_id: Mapped[UUID] = mapped_column(ForeignKey("item_types.id"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    item_type: Mapped[ItemType] = relationship(back_populates="items")
    units: Mapped[list[PhysicalUnit]] = relationship(back_populates="item_card")


class PhysicalUnit(Base):
    __tablename__ = "physical_units"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    item_card_id: Mapped[UUID] = mapped_column(ForeignKey("item_cards.id"), index=True)
    inventory_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(100))
    custody: Mapped[str] = mapped_column(String(150))
    condition: Mapped[str] = mapped_column(String(100))
    accessories: Mapped[list[str]] = mapped_column(JSON, default=list)
    state: Mapped[UnitState] = mapped_column(
        enum_type(UnitState, "unit_state"), default=UnitState.AVAILABLE, index=True
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    item_card: Mapped[ItemCard] = relationship(back_populates="units")


class LoanPolicy(Base):
    __tablename__ = "loan_policies"
    __table_args__ = (
        CheckConstraint("max_units >= 1", name="ck_policy_max_units"),
        CheckConstraint("max_duration > 0", name="ck_policy_duration"),
        CheckConstraint("max_renewals >= 0", name="ck_policy_renewals"),
        CheckConstraint("late_grace_minutes >= 0", name="ck_policy_grace"),
        CheckConstraint("fine_per_day >= 0", name="ck_policy_fine"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role | None] = mapped_column(enum_type(Role, "policy_role"), nullable=True)
    item_type_id: Mapped[UUID | None] = mapped_column(ForeignKey("item_types.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    max_units: Mapped[int] = mapped_column(Integer)
    max_duration: Mapped[int] = mapped_column(Integer)
    duration_unit: Mapped[TimeUnit] = mapped_column(enum_type(TimeUnit, "time_unit"))
    allowed_modes: Mapped[list[str]] = mapped_column(JSON, default=list)
    requires_academic_eligibility: Mapped[bool] = mapped_column(Boolean, default=False)
    guarantee_required: Mapped[bool] = mapped_column(Boolean, default=False)
    allows_renewal: Mapped[bool] = mapped_column(Boolean, default=False)
    max_renewals: Mapped[int] = mapped_column(Integer, default=0)
    late_grace_minutes: Mapped[int] = mapped_column(Integer, default=0)
    fine_per_day: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    valid_from: Mapped[datetime] = mapped_column(UTCDateTime())
    valid_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Reservation(Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint("starts_at < ends_at", name="ck_reservation_interval"),
        Index("ix_reservation_unit_interval", "unit_id", "starts_at", "ends_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    applicant_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), index=True)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("physical_units.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())
    intended_use: Mapped[str] = mapped_column(String(300))
    state: Mapped[ReservationState] = mapped_column(
        enum_type(ReservationState, "reservation_state"), default=ReservationState.PENDING
    )
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())


class Loan(Base):
    __tablename__ = "loans"
    __table_args__ = (
        CheckConstraint("starts_at < due_at", name="ck_loan_interval"),
        Index(
            "uq_open_loan_per_unit",
            "unit_id",
            unique=True,
            postgresql_where=text("state IN ('ACTIVO', 'VENCIDO')"),
            sqlite_where=text("state IN ('ACTIVO', 'VENCIDO')"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    applicant_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), index=True)
    administrator_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"), index=True)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("physical_units.id"), index=True)
    origin_reservation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("reservations.id"), unique=True, nullable=True
    )
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    use_mode: Mapped[UseMode] = mapped_column(enum_type(UseMode, "use_mode"))
    delivered_condition: Mapped[str] = mapped_column(String(200))
    delivered_accessories: Mapped[list[str]] = mapped_column(JSON, default=list)
    applied_policy: Mapped[dict[str, Any]] = mapped_column(JSON)
    state: Mapped[LoanState] = mapped_column(
        enum_type(LoanState, "loan_state"), default=LoanState.ACTIVE, index=True
    )
    returned_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    returned_condition: Mapped[str | None] = mapped_column(String(200), nullable=True)
    returned_accessories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    unit_disposition: Mapped[UnitState | None] = mapped_column(
        enum_type(UnitState, "unit_disposition"), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    closure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    renewals: Mapped[list[Renewal]] = relationship(
        back_populates="loan", order_by="Renewal.sequence"
    )


class Renewal(Base):
    __tablename__ = "renewals"
    __table_args__ = (
        UniqueConstraint("loan_id", "sequence", name="uq_renewal_sequence"),
        CheckConstraint("new_due_at > previous_due_at", name="ck_renewal_dates"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    loan_id: Mapped[UUID] = mapped_column(ForeignKey("loans.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    previous_due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    new_due_at: Mapped[datetime] = mapped_column(UTCDateTime())
    administrator_id: Mapped[UUID] = mapped_column(ForeignKey("personas.id"))
    authorized_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
    loan: Mapped[Loan] = relationship(back_populates="renewals")


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_entity_time", "entity_type", "entity_id", "occurred_at"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("personas.id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(30))
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str] = mapped_column(String(36))
    result: Mapped[str] = mapped_column(String(30), default="OK")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), server_default=func.now())
