"""Compatibilidad con imports anteriores; la lógica está separada por módulo."""

from app.application.basic_use_cases import (
    cancel_reservation as cancel_reservation,
)
from app.application.basic_use_cases import (
    create_person as create_person,
)
from app.application.basic_use_cases import (
    create_reservation as create_reservation,
)
from app.application.basic_use_cases import (
    decide_reservation as decide_reservation,
)
from app.application.basic_use_cases import (
    new_category as new_category,
)
from app.application.basic_use_cases import (
    new_item as new_item,
)
from app.application.basic_use_cases import (
    new_item_type as new_item_type,
)
from app.application.basic_use_cases import (
    new_unit as new_unit,
)
from app.application.comun import UseCaseError as UseCaseError
from app.application.comun import audit as audit
from app.application.politicas import asegurar_sin_cruces
from app.application.prestamos import devolver as return_loan
from app.application.prestamos import entregar as create_loan

__all__ = [
    "UseCaseError",
    "audit",
    "cancel_reservation",
    "create_loan",
    "create_person",
    "create_reservation",
    "decide_reservation",
    "ensure_no_unit_conflict",
    "new_category",
    "new_item",
    "new_item_type",
    "new_unit",
    "return_loan",
]


def ensure_no_unit_conflict(session, unit_id, starts_at, ends_at):  # type: ignore[no-untyped-def]
    asegurar_sin_cruces(session, unit_id, starts_at, ends_at)
