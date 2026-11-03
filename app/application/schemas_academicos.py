"""Entradas y salidas de períodos, información académica y matrículas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.application.schemas import Id, ORMModel


class PeriodoCrear(BaseModel):
    nombre_semestre: str = Field(min_length=2, max_length=50)
    fecha_inicio: date
    fecha_fin: date

    @model_validator(mode="after")
    def validar_fechas(self) -> "PeriodoCrear":
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("La fecha de fin debe ser posterior a la fecha de inicio")
        return self


class PeriodoSalida(PeriodoCrear, ORMModel):
    id_semestre: Id


class RegistroAcademicoCrear(BaseModel):
    persona_id: Id
    situacion: Literal[
        "MATRICULADO", "NO_MATRICULADO", "EGRESADO", "GRADUADO", "RETIRADO", "SUSPENDIDO"
    ]
    periodo: str = Field(min_length=2, max_length=30)
    promedio_acumulado: Decimal = Field(default=Decimal("0"), ge=0, le=99.99, decimal_places=2)
    creditos_aprobados: int = Field(default=0, ge=0)
    creditos_reprobados: int = Field(default=0, ge=0)
    creditos_cursando: int = Field(default=0, ge=0)


class RegistroAcademicoSalida(RegistroAcademicoCrear):
    id: Id
    estudiante: str
    cui: str | None
    fecha_verificacion: datetime


class MatriculaCrear(BaseModel):
    persona_id: Id
    id_semestre: Id


class MatriculaSalida(MatriculaCrear):
    id_matricula: Id
    estudiante: str
    cui: str | None
    nombre_semestre: str
    fecha_matricula: datetime
