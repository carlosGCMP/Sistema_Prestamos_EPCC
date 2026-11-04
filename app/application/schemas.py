from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from app.core.reglas import DIAS_POR_ROL, MAXIMO_BIENES
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
    # La malla de Ciencia de la Computación de la EPCC comprende diez semestres.
    semester: int | None = Field(default=None, ge=1, le=10)
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
    applicant_id: Id | None = None


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
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=120)
    role: Role
    item_type_id: Id
    max_units: int = Field(default=MAXIMO_BIENES, ge=1, le=MAXIMO_BIENES)
    max_duration: int = Field(ge=1, le=7)
    duration_unit: TimeUnit = TimeUnit.DAYS
    permitted: bool = True
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validar_limites(self) -> "PolicyCreate":
        if self.role.value not in DIAS_POR_ROL:
            raise ValueError("Las políticas se aplican a estudiantes o docentes")
        if self.duration_unit != TimeUnit.DAYS:
            raise ValueError("La duración se indica en días corridos")
        if self.max_duration > DIAS_POR_ROL[self.role.value]:
            raise ValueError(
                f"El máximo para {self.role.value.lower()} es {DIAS_POR_ROL[self.role.value]} días"
            )
        return self


class PolicyOut(ORMModel):
    id: Id
    name: str
    role: Role | None
    item_type_id: Id | None
    version: int
    max_units: int
    max_duration: int
    duration_unit: TimeUnit
    permitted: bool
    valid_from: datetime
    valid_until: datetime | None
    active: bool
    status: str


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
    model_config = ConfigDict(extra="forbid")
    origin_reservation_id: Id
    due_at: datetime
    use_mode: UseMode
    delivered_condition: str = Field(min_length=2, max_length=200)
    delivered_accessories: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=300)


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
    unit_code: str
    applicant_name: str
    administrator_name: str
    late_minutes: int
    delivered_condition: str
    delivered_accessories: list[str]
    returned_accessories: list[str] | None
    applied_policy: dict[str, Any]


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
