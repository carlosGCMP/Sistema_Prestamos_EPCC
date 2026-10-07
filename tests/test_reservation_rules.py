from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.application.use_cases import UseCaseError, ensure_no_unit_conflict
from app.infrastructure.models import (
    Category,
    ItemCard,
    ItemType,
    Person,
    PhysicalUnit,
    Reservation,
    ReservationState,
    Role,
    UnitState,
)


def test_confirmed_reservations_use_half_open_intervals(
    session_factory: sessionmaker[Session],
) -> None:
    start = datetime.now(UTC) + timedelta(days=2)
    finish = start + timedelta(hours=2)
    with session_factory.begin() as session:
        person = Person(
            cui="cui-estudiante",
            document_type="DNI",
            document_number="12345678",
            full_name="Estudiante de Prueba",
            institutional_email="estudiante@epcc.edu.pe",
            role=Role.STUDENT,
            school_affiliation="EPCC",
            start_date=date(2026, 1, 1),
        )
        category = Category(name="Computación")
        session.add_all([person, category])
        session.flush()
        item_type = ItemType(category_id=category.id, name="Laptop")
        session.add(item_type)
        session.flush()
        item = ItemCard(item_type_id=item_type.id, name="Laptop estándar")
        session.add(item)
        session.flush()
        unit = PhysicalUnit(
            item_card_id=item.id,
            inventory_code="EPCC-TEST-001",
            location="Laboratorio",
            custody="Almacén",
            condition="Operativa",
            state=UnitState.AVAILABLE,
        )
        session.add(unit)
        session.flush()
        session.add(
            Reservation(
                applicant_id=person.id,
                unit_id=unit.id,
                starts_at=start,
                ends_at=finish,
                intended_use="Prueba de intervalo semiabierto",
                state=ReservationState.CONFIRMED,
            )
        )
        session.flush()
        ensure_no_unit_conflict(session, unit.id, finish, finish + timedelta(hours=1))
        with pytest.raises(UseCaseError, match="se cruza"):
            ensure_no_unit_conflict(
                session, unit.id, start + timedelta(minutes=30), finish + timedelta(minutes=30)
            )
