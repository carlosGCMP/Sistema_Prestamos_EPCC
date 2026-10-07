from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.infrastructure.models import (
    LoanState,
    PersonState,
    ReservationState,
    Role,
    TimeUnit,
    UnitState,
    UseMode,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PersonCreate(BaseModel):
    cui: str = Field(min_length=4, max_length=20)
    document_type: str = Field(min_length=2, max_length=20)
    document_number: str = Field(min_length=2, max_length=30)
    full_name: str = Field(min_length=3, max_length=200)
    institutional_email: str = Field(min_length=5, max_length=150)
    role: Role
    school_affiliation: str = Field(min_length=2, max_length=100)
    start_date: date
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=12, max_length=128)
    student_code: str | None = None
    program: str | None = None
    semester: int | None = Field(default=None, ge=1, le=20)
    teacher_code: str | None = None
    specialty: str | None = None
    academic_status: str | None = None
    academic_term: str | None = None

    @model_validator(mode="after")
    def validate_credentials_and_profile(self) -> "PersonCreate":
        if (self.username is None) != (self.password is None):
            raise ValueError("username y password deben enviarse juntos")
        if self.role == Role.STUDENT and not all((self.student_code, self.program, self.semester)):
            raise ValueError("El perfil de estudiante requiere código, programa y semestre")
        if self.role == Role.TEACHER and not all((self.teacher_code, self.specialty)):
            raise ValueError("El perfil docente requiere código y especialidad")
        if self.role in (Role.ADMINISTRATIVE, Role.INVENTORY_ADMIN) and (
            self.student_code or self.teacher_code
        ):
            raise ValueError("El personal administrativo no usa perfil académico de solicitante")
        return self


class PersonOut(ORMModel):
    id: UUID
    cui: str
    full_name: str
    institutional_email: str
    role: Role
    state: PersonState


class AccountOut(ORMModel):
    id: UUID
    person_id: UUID
    username: str
    active: bool


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class CategoryOut(ORMModel):
    id: UUID
    name: str
    description: str | None
    active: bool


class TypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category_id: UUID
    lendable: bool = True


class TypeOut(ORMModel):
    id: UUID
    category_id: UUID
    name: str
    lendable: bool
    active: bool


class ItemCreate(BaseModel):
    item_type_id: UUID
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ItemOut(ORMModel):
    id: UUID
    item_type_id: UUID
    name: str
    description: str | None
    attributes: dict[str, Any]
    active: bool


class UnitCreate(BaseModel):
    item_card_id: UUID
    inventory_code: str = Field(min_length=2, max_length=50)
    serial_number: str | None = None
    location: str = Field(min_length=1, max_length=100)
    custody: str = Field(min_length=2, max_length=150)
    condition: str = Field(min_length=2, max_length=100)
    accessories: list[str] = Field(default_factory=list)


class UnitOut(ORMModel):
    id: UUID
    item_card_id: UUID
    inventory_code: str
    location: str
    custody: str
    condition: str
    accessories: list[str]
    state: UnitState


class PolicyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: Role | None = None
    item_type_id: UUID | None = None
    max_units: int = Field(ge=1, le=100)
    max_duration: int = Field(ge=1, le=365)
    duration_unit: TimeUnit
    allowed_modes: list[UseMode] = Field(min_length=1)
    requires_academic_eligibility: bool = False
    allows_renewal: bool = False
    max_renewals: int = Field(default=0, ge=0, le=20)
    late_grace_minutes: int = Field(default=0, ge=0, le=10080)
    fine_per_day: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=2)
    valid_from: datetime
    valid_until: datetime | None = None


class PolicyOut(ORMModel):
    id: UUID
    name: str
    role: Role | None
    item_type_id: UUID | None
    version: int
    max_units: int
    max_duration: int
    duration_unit: TimeUnit
    allowed_modes: list[str]
    requires_academic_eligibility: bool
    allows_renewal: bool
    max_renewals: int
    late_grace_minutes: int
    fine_per_day: Decimal
    valid_from: datetime
    valid_until: datetime | None
    active: bool


class ReservationCreate(BaseModel):
    unit_id: UUID
    starts_at: datetime
    ends_at: datetime
    intended_use: str = Field(min_length=3, max_length=300)


class ReservationDecision(BaseModel):
    confirm: bool
    reason: str | None = Field(default=None, max_length=1000)


class ReservationOut(ORMModel):
    id: UUID
    applicant_id: UUID
    unit_id: UUID
    starts_at: datetime
    ends_at: datetime
    intended_use: str
    state: ReservationState
    decision_reason: str | None


class LoanCreate(BaseModel):
    applicant_id: UUID
    unit_id: UUID
    origin_reservation_id: UUID | None = None
    due_at: datetime
    use_mode: UseMode
    delivered_condition: str = Field(min_length=2, max_length=200)
    delivered_accessories: list[str] = Field(default_factory=list)


class RenewalCreate(BaseModel):
    new_due_at: datetime


class ReturnCreate(BaseModel):
    returned_at: datetime | None = None
    condition: str = Field(min_length=2, max_length=200)
    accessories: list[str] = Field(default_factory=list)
    disposition: UnitState = UnitState.AVAILABLE


class LoanOut(ORMModel):
    id: UUID
    applicant_id: UUID
    administrator_id: UUID
    unit_id: UUID
    origin_reservation_id: UUID | None
    starts_at: datetime
    due_at: datetime
    use_mode: UseMode
    state: LoanState
    returned_at: datetime | None
    returned_condition: str | None


class RenewalOut(ORMModel):
    id: UUID
    loan_id: UUID
    sequence: int
    previous_due_at: datetime
    new_due_at: datetime
    administrator_id: UUID
    authorized_at: datetime


class AuditOut(ORMModel):
    id: UUID
    actor_id: UUID | None
    actor_type: str
    action: str
    entity_type: str
    entity_id: str
    result: str
    details: dict[str, Any]
    occurred_at: datetime
