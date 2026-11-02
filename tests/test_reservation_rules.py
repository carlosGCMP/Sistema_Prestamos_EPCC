from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.application.use_cases import UseCaseError, ensure_no_unit_conflict
from app.infrastructure.models import Reservation, ReservationState


def test_confirmed_reservations_use_half_open_intervals(
    session_factory: sessionmaker[Session],
    flujo_basico: dict[str, str],
) -> None:
    inicio = datetime.now(UTC) + timedelta(days=2)
    fin = inicio + timedelta(hours=2)
    with session_factory.begin() as sesion:
        sesion.add(
            Reservation(
                applicant_id=int(flujo_basico["solicitante"]),
                unit_id=int(flujo_basico["unidad"]),
                starts_at=inicio,
                ends_at=fin,
                intended_use="Intervalo semiabierto",
                state=ReservationState.CONFIRMED,
            )
        )
        sesion.flush()
        ensure_no_unit_conflict(sesion, int(flujo_basico["unidad"]), fin, fin + timedelta(hours=1))
        with pytest.raises(UseCaseError, match="se cruza"):
            ensure_no_unit_conflict(
                sesion,
                int(flujo_basico["unidad"]),
                inicio + timedelta(minutes=30),
                fin + timedelta(minutes=30),
            )
