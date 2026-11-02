from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.infrastructure.models import (
    LoanState,
    PersonState,
    ReservationState,
    Role,
    TimeUnit,
    UnitState,
    UseMode,
)


def identificador_texto(valor: int) -> str:
    return str(valor)


# PostgreSQL BIGINT supera la precisión numérica de JavaScript: enviarlo como texto.
Id = Annotated[
    int,
    Field(ge=1, le=9223372036854775807),
    PlainSerializer(identificador_texto, return_type=str),
]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class PersonCreate(BaseModel):
    cui: str | None = Field(default=None, min_length=4, max_length=20)
    document_type: str = Field(min_length=2, max_length=20)
    document_number: str = Field(min_length=2, max_length=20)
    first_names: str | None = Field(default=None, min_length=1, max_length=100)
    last_names: str | None = Field(default=None, min_length=1, max_length=100)
    full_name: str | None = Field(default=None, min_length=3, max_length=100)
    phone: str | None = Field(default=None, max_length=20)
    institutional_email: str = Field(min_length=5, max_length=150)
    role: Role
    school_affiliation: str = Field(min_length=2, max_length=100)
    start_date: date
    end_date: date | None = None
    is_admin: bool = False
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=12, max_length=128)
    student_code: str | None = Field(default=None, min_length=1, max_length=20)
    program: str | None = Field(default=None, min_length=1, max_length=100)
    semester: int | None = Field(default=None, ge=1, le=20)
    teacher_code: str | None = Field(default=None, min_length=1, max_length=20)
    specialty: str | None = Field(default=None, min_length=1, max_length=120)
    staff_code: str | None = Field(default=None, max_length=20)
    department: str = Field(default="EPCC", min_length=1, max_length=100)
    position: str = Field(default="Personal EPCC", min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_credentials_and_profile(self) -> "PersonCreate":
        if not (self.first_names and self.last_names) and not self.full_name:
            raise ValueError("Indica los nombres y apellidos")
        if self.role == Role.INVENTORY_ADMIN:
            raise ValueError(
                "El administrador es una atribución de docente o personal administrativo"
            )
        if self.is_admin and self.role not in (Role.TEACHER, Role.ADMINISTRATIVE):
            raise ValueError("Solo docentes o personal administrativo pueden ser administradores")
        if self.end_date is not None and self.end_date <= self.start_date:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        if self.role == Role.STUDENT and not self.cui:
            raise ValueError("El estudiante requiere CUI")
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
    id: Id
    cui: str | None
    first_names: str
    last_names: str
    full_name: str
    institutional_email: str
    role: Role
    state: PersonState
    is_admin: bool


class AccountOut(ORMModel):
    id: Id
    person_id: Id
    username: str
    active: bool


class CategoryCreate(BaseModel):
    item_type_id: Id
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class CategoryOut(ORMModel):
    id: Id
    item_type_id: Id
    name: str
    description: str | None
    active: bool


class TypeCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    lendable: bool = True


class TypeOut(ORMModel):
    id: Id
    name: str
    lendable: bool
    active: bool


class ItemCreate(BaseModel):
    category_id: Id
    name: str = Field(min_length=2, max_length=150)
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class ItemOut(ORMModel):
    id: Id
    item_type_id: Id
    category_id: Id
    name: str
    description: str | None
    attributes: dict[str, Any]
    active: bool


class UnitCreate(BaseModel):
    item_card_id: Id
    inventory_code: str = Field(min_length=2, max_length=50)
    serial_number: str = Field(min_length=1, max_length=100)
    acquisition_date: date | None = None
    location: str = Field(min_length=1, max_length=100)
    custody: str = Field(min_length=2, max_length=150)
    condition: str = Field(min_length=2, max_length=100)
    accessories: list[str] = Field(default_factory=list)


class UnitOut(ORMModel):
    id: Id
    item_card_id: Id
    serial_number: str
    acquisition_date: date | None
    inventory_code: str
    location: str
    custody: str
    condition: str
    accessories: list[str]
    state: UnitState


class PolicyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    role: Role | None = None
    item_type_id: Id | None = None
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
    id: Id
    name: str
    role: Role | None
    item_type_id: Id | None
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
    unit_id: Id
    starts_at: datetime
    ends_at: datetime
    intended_use: str = Field(min_length=3, max_length=300)


class ReservationDecision(BaseModel):
    confirm: bool
    reason: str | None = Field(default=None, max_length=1000)


class ReservationOut(ORMModel):
    id: Id
    applicant_id: Id
    unit_id: Id
    starts_at: datetime
    ends_at: datetime
    intended_use: str
    state: ReservationState
    decision_reason: str | None


class LoanCreate(BaseModel):
    applicant_id: Id
    unit_id: Id
    origin_reservation_id: Id | None = None
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
    id: Id
    applicant_id: Id
    administrator_id: Id
    unit_id: Id
    origin_reservation_id: Id | None
    starts_at: datetime
    due_at: datetime
    use_mode: UseMode
    state: LoanState
    returned_at: datetime | None
    returned_condition: str | None


class RenewalOut(ORMModel):
    id: Id
    loan_id: Id
    sequence: int
    previous_due_at: datetime
    new_due_at: datetime
    administrator_id: Id
    authorized_at: datetime


class AuditOut(ORMModel):
    id: Id
    actor_id: Id | None
    actor_type: str
    action: str
    entity_type: str
    entity_id: str
    result: str
    details: dict[str, Any]
    occurred_at: datetime
