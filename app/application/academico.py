"""Registro manual de períodos, información académica y matrículas; no consulta a la UNSA."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.comun import UseCaseError, ahora, audit
from app.application.schemas_academicos import (
    MatriculaCrear,
    MatriculaSalida,
    PeriodoCrear,
    RegistroAcademicoCrear,
    RegistroAcademicoSalida,
)
from app.infrastructure.modelos_sql import MatriculaRealizada, SemestreAcademico
from app.infrastructure.models import AcademicRecord, Person, Role, StudentProfile


def obtener_estudiante(sesion: Session, persona_id: int, *, bloquear: bool = False) -> Person:
    consulta = select(Person).where(Person.id == persona_id)
    if bloquear:
        consulta = consulta.with_for_update()
    persona = sesion.scalar(consulta)
    if persona is None:
        raise UseCaseError(404, "Persona no encontrada")
    if persona.role != Role.STUDENT or persona.student_profile is None or persona.applicant is None:
        raise UseCaseError(422, "La persona debe tener un perfil de estudiante")
    return persona


def crear_periodo(sesion: Session, datos: PeriodoCrear, actor: Person) -> SemestreAcademico:
    periodo = SemestreAcademico(**datos.model_dump())
    sesion.add(periodo)
    sesion.flush()
    audit(sesion, actor, "PERIODO_CREADO", "SemestreAcademico", periodo.id_semestre)
    return periodo


def guardar_registro(
    sesion: Session, datos: RegistroAcademicoCrear, actor: Person
) -> AcademicRecord:
    persona = obtener_estudiante(sesion, datos.persona_id, bloquear=True)
    assert persona.applicant is not None
    registro = sesion.scalar(select(AcademicRecord).where(AcademicRecord.person_id == persona.id))
    if registro is None:
        registro = AcademicRecord(person_id=persona.id, applicant_id=persona.applicant.id)
        sesion.add(registro)
    registro.status = datos.situacion
    registro.term = datos.periodo
    registro.average = datos.promedio_acumulado
    registro.passed_credits = datos.creditos_aprobados
    registro.failed_credits = datos.creditos_reprobados
    registro.current_credits = datos.creditos_cursando
    registro.checked_at = ahora()
    audit(sesion, actor, "REGISTRO_ACADEMICO_GUARDADO", "InformacionEstudiante", persona.id)
    return registro


def salida_registro(sesion: Session, registro: AcademicRecord) -> RegistroAcademicoSalida:
    persona = sesion.get(Person, registro.person_id)
    assert persona is not None
    return RegistroAcademicoSalida.model_validate(
        {
            "id": registro.id,
            "persona_id": persona.id,
            "estudiante": persona.full_name,
            "cui": persona.cui,
            "situacion": registro.status,
            "periodo": registro.term,
            "promedio_acumulado": registro.average,
            "creditos_aprobados": registro.passed_credits,
            "creditos_reprobados": registro.failed_credits,
            "creditos_cursando": registro.current_credits,
            "fecha_verificacion": registro.checked_at,
        }
    )


def registrar_matricula(
    sesion: Session, datos: MatriculaCrear, actor: Person
) -> MatriculaRealizada:
    persona = obtener_estudiante(sesion, datos.persona_id, bloquear=True)
    assert persona.applicant is not None
    if sesion.get(SemestreAcademico, datos.id_semestre) is None:
        raise UseCaseError(404, "Período académico no encontrado")
    if (
        sesion.scalar(
            select(MatriculaRealizada.id_matricula).where(
                MatriculaRealizada.id_solicitante == persona.applicant.id,
                MatriculaRealizada.id_semestre == datos.id_semestre,
            )
        )
        is not None
    ):
        raise UseCaseError(409, "El estudiante ya tiene matrícula en ese período")
    matricula = MatriculaRealizada(
        id_solicitante=persona.applicant.id, id_semestre=datos.id_semestre
    )
    sesion.add(matricula)
    sesion.flush()
    audit(sesion, actor, "MATRICULA_REGISTRADA", "MatriculaRealizada", matricula.id_matricula)
    return matricula


def salida_matricula(sesion: Session, matricula: MatriculaRealizada) -> MatriculaSalida:
    perfil = sesion.get(StudentProfile, matricula.id_solicitante)
    assert perfil is not None
    persona = sesion.get(Person, perfil.person_id)
    periodo = sesion.get(SemestreAcademico, matricula.id_semestre)
    assert persona is not None and periodo is not None
    return MatriculaSalida(
        id_matricula=matricula.id_matricula,
        persona_id=persona.id,
        estudiante=persona.full_name,
        cui=persona.cui,
        id_semestre=periodo.id_semestre,
        nombre_semestre=periodo.nombre_semestre,
        fecha_matricula=matricula.fecha_matricula,
    )
