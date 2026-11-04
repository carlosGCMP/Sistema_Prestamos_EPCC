"""Datos ficticios para una instalación de evaluación, nunca para una base real."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.application import academico, prestamos
from app.application import basic_use_cases as basicos
from app.application.comun import audit
from app.application.politicas import validar_reserva
from app.application.schemas import ItemCreate, LoanCreate, PersonCreate, ReturnCreate, UnitCreate
from app.application.schemas_academicos import MatriculaCrear, PeriodoCrear, RegistroAcademicoCrear
from app.infrastructure.modelos_sql import RegistroDeReserva
from app.infrastructure.models import (
    Person,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    UseMode,
)

# Credenciales PÚBLICAS y exclusivas para esta demo local. Se almacenan con Argon2.
CLAVE_ADMIN_DEMO = "contra123456"
CLAVE_DEMO = "SoloDemo-EPCC-2026!"
USUARIOS_DEMO = ("admin", "demo_estudiante1", "demo_estudiante2", "demo_docente")


def _crear_personas(sesion: Session, fecha: date) -> list[Person]:
    personas: list[Person] = []
    perfiles = [
        ("Administración", Role.ADMINISTRATIVE),
        ("Estudiante Uno", Role.STUDENT),
        ("Estudiante Dos", Role.STUDENT),
        ("Docente", Role.TEACHER),
    ]
    for numero, (nombre, rol) in enumerate(perfiles, start=1):
        estudiante = rol == Role.STUDENT
        datos = PersonCreate(
            document_type="DEMO",
            document_number=f"DEMO-{numero:04}",
            first_names=nombre,
            last_names="Demostración",
            cui=f"DEMO-CUI-{numero}" if estudiante else None,
            institutional_email=f"{USUARIOS_DEMO[numero - 1]}@example.test",
            role=rol,
            is_admin=numero == 1,
            school_affiliation="EPCC",
            start_date=fecha,
            username=USUARIOS_DEMO[numero - 1],
            password=CLAVE_ADMIN_DEMO if numero == 1 else CLAVE_DEMO,
            student_code=f"DEMO-EST-{numero}" if estudiante else None,
            program="Ciencia de la Computación" if estudiante else None,
            semester=5 if estudiante else None,
            teacher_code="DEMO-DOC-01" if rol == Role.TEACHER else None,
            specialty="Computación" if rol == Role.TEACHER else None,
        )
        persona = basicos.create_person(sesion, datos, personas[0] if personas else None)
        personas.append(persona)
    return personas


def _crear_inventario(sesion: Session, admin: Person) -> list[PhysicalUnit]:
    unidades = []
    for nombre, prefijo, cantidad, accesorios in [
        ("Laptops", "LAP", 4, ["Cargador"]),
        ("Proyectores", "PRO", 2, ["Cable HDMI", "Control"]),
    ]:
        tipo = basicos.new_item_type(sesion, f"DEMO - {nombre}", True, admin)
        categoria = basicos.new_category(sesion, f"{nombre} de demostración", None, admin, tipo.id)
        for numero in range(1, cantidad + 1):
            codigo = f"DEMO-{prefijo}-{numero:03}"
            ficha = basicos.new_item(
                sesion,
                ItemCreate(
                    category_id=categoria.id,
                    name=f"{nombre} demo {numero}",
                    description="Bien ficticio para evaluación; no representa inventario real.",
                    attributes={"Uso": "Demostración"},
                ),
                admin,
            )
            unidades.append(
                basicos.new_unit(
                    sesion,
                    UnitCreate(
                        item_card_id=ficha.id,
                        inventory_code=codigo,
                        serial_number=f"SERIE-{codigo}",
                        location="Laboratorio de demostración",
                        custody="Administración demo",
                        condition="Bueno",
                        accessories=accesorios,
                    ),
                    admin,
                )
            )
    return unidades


def _reserva_en_curso(
    sesion: Session,
    persona: Person,
    unidad: PhysicalUnit,
    admin: Person,
    instante: datetime,
) -> Reservation:
    """Fotografía de una aprobación ficticia previa, útil para entregar hoy.

    Solo el cargador crea esta reserva ya iniciada. La API conserva su prohibición
    de solicitar o confirmar en el pasado; no se altera el reloj del aplicativo.
    """
    inicio = instante - timedelta(minutes=5)
    fin = instante + timedelta(hours=8)
    politica = validar_reserva(sesion, persona, unidad, inicio, fin)
    assert persona.applicant is not None
    reserva = Reservation(
        applicant_id=persona.applicant.id,
        unit_id=unidad.id,
        starts_at=inicio,
        ends_at=fin,
        intended_use="Demostración: reserva aprobada antes del inicio",
        state=ReservationState.CONFIRMED,
    )
    sesion.add(reserva)
    sesion.flush()
    sesion.add(
        RegistroDeReserva(
            id_solicitud=reserva.id,
            id_solicitante=reserva.applicant_id,
            id_unidad_fisica=unidad.id,
            fecha_reserva=inicio,
            fecha_expiracion=fin,
            estado=ReservationState.CONFIRMED.value,
        )
    )
    audit(
        sesion,
        admin,
        "RESERVA_CONFIRMADA",
        "SolicitudDeReserva",
        reserva.id,
        {"politica": politica, "demostracion": True},
    )
    return reserva


def crear_datos(sesion: Session) -> None:
    """El llamador garantiza una base vacía y confirma todo en una sola transacción."""
    instante = datetime.now(UTC)
    admin, estudiante1, estudiante2, docente = _crear_personas(sesion, instante.date())
    unidades = _crear_inventario(sesion, admin)

    # Uno activo y otro devuelto, ambos mediante los servicios reales de préstamo.
    for persona, unidad, devolver in [
        (estudiante1, unidades[0], False),
        (estudiante2, unidades[4], True),
    ]:
        reserva = _reserva_en_curso(sesion, persona, unidad, admin, instante)
        prestamo = prestamos.entregar(
            sesion,
            LoanCreate(
                origin_reservation_id=reserva.id,
                due_at=reserva.ends_at,
                use_mode=UseMode.TAKE_HOME,
                delivered_condition="Bueno",
                delivered_accessories=unidad.accessories,
                notes="Entrega ficticia de demostración",
            ),
            admin,
        )
        if devolver:
            prestamos.devolver(
                sesion,
                prestamo.id,
                ReturnCreate(
                    condition="Bueno",
                    accessories=unidad.accessories,
                ),
                admin,
            )

    # Lista para entregar desde la interfaz durante las ocho horas siguientes.
    _reserva_en_curso(sesion, estudiante1, unidades[1], admin, instante)
    basicos.create_reservation(
        sesion,
        estudiante2,
        unidades[2].id,
        instante + timedelta(hours=2),
        instante + timedelta(hours=4),
        "Demostración: solicitud pendiente de aprobación",
    )
    futura = basicos.create_reservation(
        sesion,
        docente,
        unidades[3].id,
        instante + timedelta(days=1),
        instante + timedelta(days=6),
        "Demostración: reserva docente de cinco días",
    )
    basicos.decide_reservation(sesion, futura.id, admin, True, None)

    periodo = academico.crear_periodo(
        sesion,
        PeriodoCrear(
            nombre_semestre=f"{instante.year}-DEMO",
            fecha_inicio=date(instante.year, 1, 1),
            fecha_fin=date(instante.year, 12, 31),
        ),
        admin,
    )
    for estudiante in (estudiante1, estudiante2):
        academico.guardar_registro(
            sesion,
            RegistroAcademicoCrear(
                persona_id=estudiante.id,
                situacion="MATRICULADO",
                periodo=periodo.nombre_semestre,
                promedio_acumulado=Decimal("15.50"),
                creditos_aprobados=90,
                creditos_cursando=20,
            ),
            admin,
        )
        academico.registrar_matricula(
            sesion,
            MatriculaCrear(
                persona_id=estudiante.id,
                id_semestre=periodo.id_semestre,
            ),
            admin,
        )
    sesion.flush()
