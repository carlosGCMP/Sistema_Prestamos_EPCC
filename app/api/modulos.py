"""Rutas de políticas, préstamos y vinculación académica."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application import academico, politicas, prestamos
from app.application.comun import UseCaseError
from app.application.schemas import Id, LoanCreate, LoanOut, PolicyCreate, PolicyOut, ReturnCreate
from app.application.schemas_academicos import (
    MatriculaCrear,
    MatriculaSalida,
    PeriodoCrear,
    PeriodoSalida,
    RegistroAcademicoCrear,
    RegistroAcademicoSalida,
)
from app.core.security import AdminActor, MemberActor
from app.infrastructure.database import obtener_sesion
from app.infrastructure.modelos_sql import (
    MatriculaRealizada,
    SemestreAcademico,
    VersionDeLaPolitica,
)
from app.infrastructure.models import AcademicRecord, Loan, LoanPolicy, Person, Role

router = APIRouter()
Sesion = Annotated[Session, Depends(obtener_sesion, scope="function")]


@router.get("/policies", response_model=list[PolicyOut], tags=["políticas"])
def listar_politicas(_actor: MemberActor, sesion: Sesion) -> list[PolicyOut]:
    filas = sesion.scalars(
        select(LoanPolicy).order_by(LoanPolicy.item_type_id, LoanPolicy.role, LoanPolicy.version)
    ).all()
    return [politicas.salida_politica(sesion, fila) for fila in filas]


@router.post("/policies", response_model=PolicyOut, status_code=201, tags=["políticas"])
def publicar_politica(datos: PolicyCreate, actor: AdminActor, sesion: Sesion) -> PolicyOut:
    return politicas.salida_politica(sesion, politicas.publicar_politica(sesion, datos, actor))


@router.get("/policies/{identificador}/history", tags=["políticas"])
def historial_politica(identificador: Id, _actor: AdminActor, sesion: Sesion) -> list[str]:
    if sesion.get(LoanPolicy, identificador) is None:
        raise UseCaseError(404, "Política no encontrada")
    return list(
        sesion.scalars(
            select(VersionDeLaPolitica.contenido)
            .where(
                VersionDeLaPolitica.id_politica == identificador,
            )
            .order_by(VersionDeLaPolitica.id_version)
        )
    )


@router.get("/loans", response_model=list[LoanOut], tags=["préstamos"])
def listar_prestamos(
    actor: MemberActor, sesion: Sesion, limit: int = Query(default=100, ge=1, le=500)
) -> list[LoanOut]:
    consulta = select(Loan)
    if not actor.is_admin:
        if actor.applicant is None:
            return []
        consulta = consulta.where(Loan.applicant_id == actor.applicant.id)
    return [
        prestamos.salida_prestamo(sesion, fila)
        for fila in sesion.scalars(consulta.order_by(Loan.created_at.desc()).limit(limit))
    ]


@router.post("/loans", response_model=LoanOut, status_code=201, tags=["préstamos"])
def entregar_prestamo(datos: LoanCreate, actor: AdminActor, sesion: Sesion) -> LoanOut:
    return prestamos.salida_prestamo(sesion, prestamos.entregar(sesion, datos, actor))


@router.post("/loans/{identificador}/return", response_model=LoanOut, tags=["préstamos"])
def devolver_prestamo(
    identificador: Id, datos: ReturnCreate, actor: AdminActor, sesion: Sesion
) -> LoanOut:
    return prestamos.salida_prestamo(
        sesion, prestamos.devolver(sesion, identificador, datos, actor)
    )


@router.get(
    "/academic/students", response_model=list[dict[str, str | None]], tags=["vinculación académica"]
)
def listar_estudiantes(_actor: AdminActor, sesion: Sesion) -> list[dict[str, str | None]]:
    return [
        {"id": str(persona.id), "name": persona.full_name, "cui": persona.cui}
        for persona in sesion.scalars(
            select(Person).where(Person.role == Role.STUDENT).order_by(Person.full_name)
        )
    ]


@router.get("/academic/terms", response_model=list[PeriodoSalida], tags=["vinculación académica"])
def listar_periodos(_actor: AdminActor, sesion: Sesion) -> list[SemestreAcademico]:
    return list(
        sesion.scalars(select(SemestreAcademico).order_by(SemestreAcademico.fecha_inicio.desc()))
    )


@router.post(
    "/academic/terms", response_model=PeriodoSalida, status_code=201, tags=["vinculación académica"]
)
def crear_periodo(datos: PeriodoCrear, actor: AdminActor, sesion: Sesion) -> SemestreAcademico:
    return academico.crear_periodo(sesion, datos, actor)


@router.get(
    "/academic/records",
    response_model=list[RegistroAcademicoSalida],
    tags=["vinculación académica"],
)
def listar_registros(_actor: AdminActor, sesion: Sesion) -> list[RegistroAcademicoSalida]:
    return [
        academico.salida_registro(sesion, fila) for fila in sesion.scalars(select(AcademicRecord))
    ]


@router.post(
    "/academic/records", response_model=RegistroAcademicoSalida, tags=["vinculación académica"]
)
def guardar_registro(
    datos: RegistroAcademicoCrear, actor: AdminActor, sesion: Sesion
) -> RegistroAcademicoSalida:
    return academico.salida_registro(sesion, academico.guardar_registro(sesion, datos, actor))


@router.get(
    "/academic/enrollments", response_model=list[MatriculaSalida], tags=["vinculación académica"]
)
def listar_matriculas(_actor: AdminActor, sesion: Sesion) -> list[MatriculaSalida]:
    return [
        academico.salida_matricula(sesion, fila)
        for fila in sesion.scalars(select(MatriculaRealizada))
    ]


@router.post(
    "/academic/enrollments",
    response_model=MatriculaSalida,
    status_code=201,
    tags=["vinculación académica"],
)
def registrar_matricula(
    datos: MatriculaCrear, actor: AdminActor, sesion: Sesion
) -> MatriculaSalida:
    return academico.salida_matricula(sesion, academico.registrar_matricula(sesion, datos, actor))
