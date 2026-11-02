"""Modelos operativos: tablas y columnas en español basadas en `base de datos/`.

Los atributos Python históricos se conservan para no cambiar innecesariamente el
contrato HTTP. Los identificadores reales son BIGINT, no UUID. Las tablas de apoyo
del diseño SQL se encuentran en modelos_sql.py.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
    case,
    func,
    select,
    text,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.elements import ColumnElement

from app.infrastructure.database import Base

# SQLite necesita INTEGER para autoincrementar durante las pruebas; PostgreSQL usa BIGINT.
IDENTIFICADOR = BigInteger().with_variant(Integer, "sqlite")


class Role(StrEnum):
    STUDENT = "ESTUDIANTE"
    TEACHER = "DOCENTE"
    ADMINISTRATIVE = "PERSONAL_ADMINISTRATIVO"
    INVENTORY_ADMIN = "ADMIN_INVENTARIO"  # Compatibilidad con procesos históricos.


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
    """Estados legibles almacenados como VARCHAR con una restricción CHECK."""
    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        values_callable=lambda items: [item.value for item in items],
    )


class UTCDateTime(TypeDecorator[datetime]):
    """Guarda instantes UTC y conserva la zona horaria también en las pruebas."""

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
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Person(Base):
    __tablename__ = "persona"
    __table_args__ = (
        CheckConstraint("fecha_fin IS NULL OR fecha_fin > fecha_inicio", name="ck_fechas_persona"),
    )
    id: Mapped[int] = mapped_column("id_persona", IDENTIFICADOR, Identity(), primary_key=True)
    first_names: Mapped[str] = mapped_column("nombres", String(100))
    last_names: Mapped[str] = mapped_column("apellidos", String(100), default="")
    cui: Mapped[str | None] = mapped_column(String(20), unique=True)
    document_type: Mapped[str] = mapped_column("tipo_documento", String(20))
    document_number: Mapped[str] = mapped_column("documento_identidad", String(20), unique=True)
    institutional_email: Mapped[str] = mapped_column("correo", String(150), unique=True)
    phone: Mapped[str | None] = mapped_column("telefono", String(20))
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)
    role: Mapped[Role] = mapped_column("rol", enum_type(Role, "rol_persona"))
    school_affiliation: Mapped[str] = mapped_column("afiliacion", String(100))
    start_date: Mapped[date] = mapped_column("fecha_inicio", Date)
    end_date: Mapped[date | None] = mapped_column("fecha_fin", Date)
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", UTCDateTime(), server_default=func.now()
    )
    account: Mapped[Account | None] = relationship(back_populates="person", uselist=False)
    applicant: Mapped[Solicitante | None] = relationship(back_populates="person", uselist=False)
    student_profile: Mapped[StudentProfile | None] = relationship(uselist=False)
    teacher_profile: Mapped[TeacherProfile | None] = relationship(uselist=False)
    academic_record: Mapped[AcademicRecord | None] = relationship(uselist=False)

    @hybrid_property
    def full_name(self) -> str:
        return f"{self.first_names} {self.last_names}".strip()

    @full_name.inplace.setter
    def _nombre_completo(self, value: str) -> None:
        # Compatibilidad: no inventar apellidos al recibir un nombre sin desglosar.
        self.first_names, self.last_names = value, ""

    @full_name.inplace.expression
    @classmethod
    def _expresion_nombre(cls) -> ColumnElement[str]:
        return func.trim(cls.first_names + " " + cls.last_names)

    @hybrid_property
    def state(self) -> PersonState:
        return PersonState.ACTIVE if self.active else PersonState.INACTIVE

    @state.inplace.setter
    def _estado(self, value: PersonState) -> None:
        self.active = value == PersonState.ACTIVE

    @state.inplace.expression
    @classmethod
    def _expresion_estado(cls) -> ColumnElement[str]:
        return case(
            (cls.active.is_(True), PersonState.ACTIVE.value), else_=PersonState.INACTIVE.value
        )

    @property
    def is_admin(self) -> bool:
        return self.account is not None and self.account.administrator is not None


class Account(Base):
    __tablename__ = "cuenta"
    id: Mapped[int] = mapped_column("id_cuenta", IDENTIFICADOR, Identity(), primary_key=True)
    person_id: Mapped[int] = mapped_column(
        "id_persona", ForeignKey("persona.id_persona"), unique=True
    )
    username: Mapped[str] = mapped_column("nombre_usuario", String(50), unique=True)
    password_hash: Mapped[str] = mapped_column("contrasena_hash", String(255))
    status: Mapped[str] = mapped_column("estado", String(20), default="activa")
    session_version: Mapped[int] = mapped_column("version_sesion", Integer, default=0)
    last_login_at: Mapped[datetime | None] = mapped_column("ultimo_acceso", UTCDateTime())
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", UTCDateTime(), server_default=func.now()
    )
    person: Mapped[Person] = relationship(back_populates="account")
    administrator: Mapped[Administrador | None] = relationship(uselist=False)

    @property
    def active(self) -> bool:
        return self.status == "activa"

    @active.setter
    def active(self, valor: bool) -> None:
        self.status = "activa" if valor else "inactiva"


class Solicitante(Base):
    """Identidad del solicitante; las credenciales pertenecen solamente a cuenta."""

    __tablename__ = "solicitante"
    id: Mapped[int] = mapped_column("id_solicitante", IDENTIFICADOR, Identity(), primary_key=True)
    person_id: Mapped[int] = mapped_column(
        "id_persona", ForeignKey("persona.id_persona"), unique=True
    )
    account_id: Mapped[int] = mapped_column(
        "id_cuenta", ForeignKey("cuenta.id_cuenta"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha_creacion", UTCDateTime(), server_default=func.now()
    )
    person: Mapped[Person] = relationship(back_populates="applicant")


class Administrador(Base):
    __tablename__ = "administrador"
    id: Mapped[int] = mapped_column("id_administrador", IDENTIFICADOR, Identity(), primary_key=True)
    account_id: Mapped[int] = mapped_column(
        "id_cuenta", ForeignKey("cuenta.id_cuenta"), unique=True
    )


class StudentProfile(Base):
    __tablename__ = "solicitante_estudiante"
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante.id_solicitante"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        "id_persona", ForeignKey("persona.id_persona"), unique=True
    )
    university_code: Mapped[str] = mapped_column("codigo_universitario", String(20), unique=True)
    program: Mapped[str] = mapped_column("programa_academico", String(100))
    semester: Mapped[int] = mapped_column("semestre", Integer)


class TeacherProfile(Base):
    __tablename__ = "solicitante_docente"
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante.id_solicitante"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        "id_persona", ForeignKey("persona.id_persona"), unique=True
    )
    institutional_code: Mapped[str] = mapped_column("codigo_docente", String(20), unique=True)
    specialty: Mapped[str] = mapped_column("especialidad", String(120))
    department: Mapped[str] = mapped_column("departamento", String(100), default="EPCC")
    position: Mapped[str] = mapped_column("cargo", String(100), default="Docente")


class AcademicRecord(Base):
    __tablename__ = "informacion_estudiante"
    id: Mapped[int] = mapped_column("id_informacion", IDENTIFICADOR, Identity(), primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante_estudiante.id_solicitante"), unique=True
    )
    person_id: Mapped[int] = mapped_column(
        "id_persona", ForeignKey("persona.id_persona"), unique=True
    )
    average: Mapped[Decimal] = mapped_column("promedio_acumulado", Numeric(4, 2), default=0)
    passed_credits: Mapped[int] = mapped_column("creditos_aprobados", Integer, default=0)
    failed_credits: Mapped[int] = mapped_column("creditos_reprobados", Integer, default=0)
    current_credits: Mapped[int] = mapped_column("creditos_cursando", Integer, default=0)
    status: Mapped[str] = mapped_column("situacion", String(30))
    term: Mapped[str] = mapped_column("periodo", String(30))
    checked_at: Mapped[datetime] = mapped_column(
        "fecha_verificacion", UTCDateTime(), server_default=func.now()
    )
    valid_until: Mapped[datetime | None] = mapped_column("valido_hasta", UTCDateTime())
    __table_args__ = (
        CheckConstraint(
            "promedio_acumulado >= 0 AND creditos_aprobados >= 0 "
            "AND creditos_reprobados >= 0 AND creditos_cursando >= 0",
            name="ck_creditos_estudiante",
        ),
    )


class ItemType(Base):
    __tablename__ = "tipo_de_bien"
    id: Mapped[int] = mapped_column("id_tipo_bien", IDENTIFICADOR, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column("nombre_tipo_bien", String(100), unique=True)
    lendable: Mapped[bool] = mapped_column("prestable", Boolean, default=True)
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)
    categories: Mapped[list[Category]] = relationship(back_populates="item_type")


class Category(Base):
    __tablename__ = "categoria_del_bien"
    __table_args__ = (
        UniqueConstraint("id_tipo_bien", "nombre_categoria", name="uq_categoria_tipo"),
    )
    id: Mapped[int] = mapped_column("id_categoria", IDENTIFICADOR, Identity(), primary_key=True)
    item_type_id: Mapped[int] = mapped_column(
        "id_tipo_bien", ForeignKey("tipo_de_bien.id_tipo_bien")
    )
    name: Mapped[str] = mapped_column("nombre_categoria", String(100))
    description: Mapped[str | None] = mapped_column("descripcion", Text)
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)
    item_type: Mapped[ItemType] = relationship(back_populates="categories")


class Bien(Base):
    __tablename__ = "bien"
    id: Mapped[int] = mapped_column("id_bien", IDENTIFICADOR, Identity(), primary_key=True)
    category_id: Mapped[int] = mapped_column(
        "id_categoria", ForeignKey("categoria_del_bien.id_categoria")
    )
    name: Mapped[str] = mapped_column("nombre_bien", String(150))
    description: Mapped[str | None] = mapped_column("descripcion", Text)
    attributes: Mapped[dict[str, Any]] = mapped_column("caracteristicas", JSON, default=dict)
    category: Mapped[Category] = relationship()


class ItemCard(Base):
    __tablename__ = "ficha_de_bien"
    id: Mapped[int] = mapped_column("id_ficha", IDENTIFICADOR, Identity(), primary_key=True)
    bien_id: Mapped[int] = mapped_column("id_bien", ForeignKey("bien.id_bien"), unique=True)
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante.id_solicitante")
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha_registro", UTCDateTime(), server_default=func.now()
    )
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)
    bien: Mapped[Bien] = relationship()
    units: Mapped[list[PhysicalUnit]] = relationship(back_populates="item_card")

    @hybrid_property
    def name(self) -> str:
        return self.bien.name

    @name.inplace.expression
    @classmethod
    def _nombre_bien(cls) -> ColumnElement[str]:
        return select(Bien.name).where(Bien.id == cls.bien_id).scalar_subquery()

    @property
    def description(self) -> str | None:
        return self.bien.description

    @property
    def attributes(self) -> dict[str, Any]:
        return self.bien.attributes

    @property
    def category_id(self) -> int:
        return self.bien.category_id

    @property
    def item_type_id(self) -> int:
        return self.bien.category.item_type_id


class PhysicalUnit(Base):
    __tablename__ = "unidad_fisica"
    id: Mapped[int] = mapped_column("id_unidad_fisica", IDENTIFICADOR, Identity(), primary_key=True)
    item_card_id: Mapped[int] = mapped_column(
        "id_ficha", ForeignKey("ficha_de_bien.id_ficha"), unique=True
    )
    inventory_code: Mapped[str] = mapped_column("codigo_inventario", String(50), unique=True)
    serial_number: Mapped[str] = mapped_column("numero_serie", String(100))
    location: Mapped[str] = mapped_column("ubicacion_actual", String(100))
    custody: Mapped[str] = mapped_column("responsable_custodia", String(150))
    condition: Mapped[str] = mapped_column("condicion", String(100))
    accessories: Mapped[list[str]] = mapped_column("accesorios", JSON, default=list)
    acquisition_date: Mapped[date | None] = mapped_column("fecha_adquisicion", Date)
    state: Mapped[UnitState] = mapped_column(
        "estado", enum_type(UnitState, "estado_unidad"), default=UnitState.AVAILABLE
    )
    created_at: Mapped[datetime] = mapped_column(
        "fecha_registro", UTCDateTime(), server_default=func.now()
    )
    item_card: Mapped[ItemCard] = relationship(back_populates="units")


class LoanPolicy(Base):
    __tablename__ = "politicas_del_prestamo"
    __table_args__ = (
        UniqueConstraint(
            "id_tipo_bien", "tipo_solicitante", "numero_version", name="uq_version_politica"
        ),
        CheckConstraint(
            "cantidad_maxima_bienes >= 1 AND tiempo_maximo_prestamo > 0 "
            "AND cantidad_maxima_prorrogas >= 0",
            name="ck_limites_politica",
        ),
    )
    id: Mapped[int] = mapped_column("id_politica", IDENTIFICADOR, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column("nombre_politica", String(120))
    role: Mapped[Role | None] = mapped_column("tipo_solicitante", enum_type(Role, "rol_politica"))
    item_type_id: Mapped[int | None] = mapped_column(
        "id_tipo_bien", ForeignKey("tipo_de_bien.id_tipo_bien")
    )
    version: Mapped[int] = mapped_column("numero_version", Integer, default=1)
    max_units: Mapped[int] = mapped_column("cantidad_maxima_bienes", Integer)
    max_duration: Mapped[int] = mapped_column("tiempo_maximo_prestamo", Integer)
    max_extension: Mapped[int] = mapped_column("tiempo_maximo_prorroga", Integer, default=0)
    duration_unit: Mapped[TimeUnit] = mapped_column(
        "unidad_tiempo", enum_type(TimeUnit, "unidad_tiempo")
    )
    allowed_modes: Mapped[list[str]] = mapped_column("modalidades_permitidas", JSON, default=list)
    requires_academic_eligibility: Mapped[bool] = mapped_column(
        "requiere_vigencia_academica", Boolean, default=False
    )
    guarantee_required: Mapped[bool] = mapped_column("requiere_garantia", Boolean, default=False)
    allows_renewal: Mapped[bool] = mapped_column("permite_prorroga", Boolean, default=False)
    max_renewals: Mapped[int] = mapped_column("cantidad_maxima_prorrogas", Integer, default=0)
    late_grace_minutes: Mapped[int] = mapped_column("tolerancia_minutos", Integer, default=0)
    fine_per_day: Mapped[Decimal] = mapped_column("multa_diaria", Numeric(10, 2), default=0)
    valid_from: Mapped[datetime] = mapped_column("vigencia_inicio", UTCDateTime())
    valid_until: Mapped[datetime | None] = mapped_column("vigencia_fin", UTCDateTime())
    active: Mapped[bool] = mapped_column("activo", Boolean, default=True)


class Reservation(Base):
    __tablename__ = "solicitud_de_reserva"
    __table_args__ = (
        CheckConstraint("fecha_reserva < fecha_expiracion", name="ck_intervalo_solicitud"),
        Index("ix_intervalo_reserva", "id_unidad_fisica", "fecha_reserva", "fecha_expiracion"),
    )
    id: Mapped[int] = mapped_column("id_solicitud", IDENTIFICADOR, Identity(), primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante.id_solicitante")
    )
    unit_id: Mapped[int] = mapped_column(
        "id_unidad_fisica", ForeignKey("unidad_fisica.id_unidad_fisica")
    )
    starts_at: Mapped[datetime] = mapped_column("fecha_reserva", UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column("fecha_expiracion", UTCDateTime())
    intended_use: Mapped[str] = mapped_column("uso_previsto", String(300))
    state: Mapped[ReservationState] = mapped_column(
        "estado",
        enum_type(ReservationState, "estado_solicitud"),
        ForeignKey("estado_de_la_reserva.nombre_estado"),
        default=ReservationState.PENDING,
    )
    decision_reason: Mapped[str | None] = mapped_column("motivo_decision", Text)
    created_at: Mapped[datetime] = mapped_column(
        "fecha_solicitud", UTCDateTime(), server_default=func.now()
    )


class Loan(Base):
    __tablename__ = "prestamo"
    __table_args__ = (
        CheckConstraint("fecha_inicio < fecha_vencimiento", name="ck_intervalo_prestamo"),
        Index(
            "uq_prestamo_abierto_unidad",
            "id_unidad_fisica",
            unique=True,
            postgresql_where=text("estado IN ('ACTIVO', 'VENCIDO')"),
            sqlite_where=text("estado IN ('ACTIVO', 'VENCIDO')"),
        ),
    )
    id: Mapped[int] = mapped_column("id_prestamo", IDENTIFICADOR, Identity(), primary_key=True)
    applicant_id: Mapped[int] = mapped_column(
        "id_solicitante", ForeignKey("solicitante.id_solicitante")
    )
    administrator_id: Mapped[int] = mapped_column(
        "id_administrador", ForeignKey("administrador.id_administrador")
    )
    unit_id: Mapped[int] = mapped_column(
        "id_unidad_fisica", ForeignKey("unidad_fisica.id_unidad_fisica")
    )
    origin_reservation_id: Mapped[int | None] = mapped_column(
        "id_solicitud_origen", ForeignKey("solicitud_de_reserva.id_solicitud"), unique=True
    )
    approval_id: Mapped[int | None] = mapped_column(
        "id_prestamo_aprobado",
        ForeignKey("prestamo_aprobado_de_reserva.id_prestamo_aprobado"),
        unique=True,
    )
    starts_at: Mapped[datetime] = mapped_column("fecha_inicio", UTCDateTime())
    due_at: Mapped[datetime] = mapped_column("fecha_vencimiento", UTCDateTime())
    use_mode: Mapped[UseMode] = mapped_column("modalidad_uso", enum_type(UseMode, "modalidad_uso"))
    delivered_condition: Mapped[str] = mapped_column("condicion_entrega", String(200))
    delivered_accessories: Mapped[list[str]] = mapped_column(
        "accesorios_entregados", JSON, default=list
    )
    applied_policy: Mapped[dict[str, Any]] = mapped_column("politica_aplicada", JSON)
    state: Mapped[LoanState] = mapped_column(
        "estado",
        enum_type(LoanState, "estado_prestamo"),
        ForeignKey("estado_del_prestamo.nombre_estado"),
        default=LoanState.ACTIVE,
    )
    returned_at: Mapped[datetime | None] = mapped_column("fecha_devolucion", UTCDateTime())
    returned_condition: Mapped[str | None] = mapped_column("condicion_devolucion", String(200))
    returned_accessories: Mapped[list[str] | None] = mapped_column("accesorios_recibidos", JSON)
    unit_disposition: Mapped[UnitState | None] = mapped_column(
        "destino_unidad", enum_type(UnitState, "destino_unidad")
    )
    closed_at: Mapped[datetime | None] = mapped_column("fecha_cierre", UTCDateTime())
    closure_reason: Mapped[str | None] = mapped_column("motivo_cierre", Text)
    created_at: Mapped[datetime] = mapped_column(
        "fecha_registro", UTCDateTime(), server_default=func.now()
    )
    renewals: Mapped[list[Renewal]] = relationship(
        back_populates="loan", order_by="Renewal.sequence"
    )


class Renewal(Base):
    __tablename__ = "ampliacion_devolucion_prestamo"
    __table_args__ = (
        UniqueConstraint("id_prestamo", "numero_ampliacion", name="uq_numero_ampliacion"),
        CheckConstraint(
            "nueva_fecha_devolucion > fecha_devolucion_anterior", name="ck_fechas_ampliacion"
        ),
    )
    id: Mapped[int] = mapped_column("id_ampliacion", IDENTIFICADOR, Identity(), primary_key=True)
    loan_id: Mapped[int] = mapped_column("id_prestamo", ForeignKey("prestamo.id_prestamo"))
    sequence: Mapped[int] = mapped_column("numero_ampliacion", Integer)
    previous_due_at: Mapped[datetime] = mapped_column("fecha_devolucion_anterior", UTCDateTime())
    new_due_at: Mapped[datetime] = mapped_column("nueva_fecha_devolucion", UTCDateTime())
    administrator_id: Mapped[int] = mapped_column(
        "id_administrador", ForeignKey("administrador.id_administrador")
    )
    authorized_at: Mapped[datetime] = mapped_column(
        "fecha_ampliacion", UTCDateTime(), server_default=func.now()
    )
    notes: Mapped[str | None] = mapped_column("observaciones", Text)
    loan: Mapped[Loan] = relationship(back_populates="renewals")


class AuditEvent(Base):
    __tablename__ = "registro_auditoria"
    id: Mapped[int] = mapped_column("id_registro", IDENTIFICADOR, Identity(), primary_key=True)
    actor_id: Mapped[int | None] = mapped_column("id_cuenta", ForeignKey("cuenta.id_cuenta"))
    event_type_id: Mapped[int] = mapped_column(
        "id_tipo_evento", ForeignKey("tipo_de_evento.id_tipo_evento")
    )
    actor_type: Mapped[str] = mapped_column("tipo_actor", String(30))
    action: Mapped[str] = mapped_column("accion", String(100))
    entity_type: Mapped[str] = mapped_column("tipo_entidad", String(80))
    entity_id: Mapped[str] = mapped_column("id_entidad", String(30))
    result: Mapped[str] = mapped_column("resultado", String(30), default="OK")
    description: Mapped[str] = mapped_column("descripcion", Text, default="{}")
    occurred_at: Mapped[datetime] = mapped_column("fecha", UTCDateTime(), server_default=func.now())

    @property
    def details(self) -> dict[str, Any]:
        try:
            valor = json.loads(self.description)
        except ValueError:
            return {"descripcion": self.description}
        return dict(valor) if isinstance(valor, dict) else {"descripcion": valor}

    @details.setter
    def details(self, valor: dict[str, Any]) -> None:
        self.description = json.dumps(valor, ensure_ascii=False)


# Registrar también las tablas de apoyo; este import no ejecuta consultas.
from app.infrastructure import modelos_sql  # noqa: E402, F401
