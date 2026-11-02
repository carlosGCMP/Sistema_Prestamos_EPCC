"""HTTP routes for the current basic implementation scope."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.application.basic_use_cases import (
    UseCaseError,
    audit,
    cancel_reservation,
    create_person,
    create_reservation,
    decide_reservation,
    new_category,
    new_item,
    new_item_type,
    new_unit,
)
from app.application.schemas import (
    CategoryCreate,
    CategoryOut,
    ItemCreate,
    ItemOut,
    PersonCreate,
    PersonOut,
    ReservationCreate,
    ReservationDecision,
    ReservationOut,
    TokenResponse,
    TypeCreate,
    TypeOut,
    UnitCreate,
    UnitOut,
)
from app.core.security import (
    AdminActor,
    CurrentAccount,
    MemberActor,
    create_access_token,
    verify_password,
)
from app.core.settings import get_settings
from app.infrastructure.database import get_session
from app.infrastructure.models import (
    Account,
    Category,
    ItemCard,
    ItemType,
    Person,
    PersonState,
    PhysicalUnit,
    Reservation,
    Role,
    UnitState,
)

router = APIRouter()
# Confirmar la transacción antes de enviar la respuesta y de que la web recargue datos.
SessionDep = Annotated[Session, Depends(get_session, scope="function")]


@router.post("/auth/token", response_model=TokenResponse, tags=["usuarios"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep
) -> TokenResponse:
    account = session.scalar(select(Account).where(Account.username == form.username))
    if (
        account is None
        or not account.active
        or account.person.state != PersonState.ACTIVE
        or not verify_password(form.password, account.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    account.last_login_at = datetime.now(UTC)
    return TokenResponse(
        access_token=create_access_token(account),
        expires_in=get_settings().access_token_minutes * 60,
    )


@router.post("/auth/logout", status_code=204, tags=["usuarios"])
def logout(account: CurrentAccount) -> None:
    account.session_version += 1


@router.get("/me", response_model=PersonOut, tags=["usuarios"])
def me(actor: MemberActor) -> Person:
    return actor


@router.post("/people", response_model=PersonOut, status_code=201, tags=["usuarios"])
def register_person(data: PersonCreate, actor: AdminActor, session: SessionDep) -> Person:
    return create_person(session, data, actor)


@router.get("/people", response_model=list[PersonOut], tags=["usuarios"])
def list_people(
    _actor: AdminActor,
    session: SessionDep,
    state: PersonState | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Person]:
    statement = select(Person)
    if state is not None:
        statement = statement.where(Person.state == state)
    return list(session.scalars(statement.order_by(Person.full_name).limit(limit)).all())


@router.get("/people/{person_id}", response_model=PersonOut, tags=["usuarios"])
def get_person(person_id: UUID, _actor: AdminActor, session: SessionDep) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


@router.post("/people/{person_id}/deactivate", response_model=PersonOut, tags=["usuarios"])
def deactivate_person(person_id: UUID, actor: AdminActor, session: SessionDep) -> Person:
    person = session.scalar(
        select(Person)
        .where(Person.id == person_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    person.state = PersonState.INACTIVE
    if person.account:
        person.account.active = False
        person.account.session_version += 1
    audit(session, actor, "PERSONA_DESACTIVADA", "Person", person.id)
    return person


@router.post(
    "/inventory/categories", response_model=CategoryOut, status_code=201, tags=["catálogo"]
)
def create_category(data: CategoryCreate, actor: AdminActor, session: SessionDep) -> Category:
    return new_category(session, data.name, data.description, actor)


@router.get("/inventory/categories", response_model=list[CategoryOut], tags=["catálogo"])
def list_categories(_actor: MemberActor, session: SessionDep) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)).all())


@router.post("/inventory/types", response_model=TypeOut, status_code=201, tags=["catálogo"])
def create_type(data: TypeCreate, actor: AdminActor, session: SessionDep) -> ItemType:
    return new_item_type(session, data.name, data.category_id, data.lendable, actor)


@router.get("/inventory/types", response_model=list[TypeOut], tags=["catálogo"])
def list_types(_actor: MemberActor, session: SessionDep) -> list[ItemType]:
    return list(session.scalars(select(ItemType).order_by(ItemType.name)).all())


@router.post("/inventory/items", response_model=ItemOut, status_code=201, tags=["catálogo"])
def create_item(data: ItemCreate, actor: AdminActor, session: SessionDep) -> ItemCard:
    return new_item(session, data, actor)


@router.get("/inventory/items", response_model=list[ItemOut], tags=["catálogo"])
def list_items(_actor: MemberActor, session: SessionDep) -> list[ItemCard]:
    return list(
        session.scalars(
            select(ItemCard).where(ItemCard.active.is_(True)).order_by(ItemCard.name)
        ).all()
    )


@router.post("/inventory/units", response_model=UnitOut, status_code=201, tags=["inventario"])
def create_unit(data: UnitCreate, actor: AdminActor, session: SessionDep) -> PhysicalUnit:
    return new_unit(session, data, actor)


@router.get("/inventory/units", response_model=list[UnitOut], tags=["inventario"])
def list_units(
    _actor: MemberActor,
    session: SessionDep,
    search: str | None = Query(default=None, min_length=1, max_length=100),
    state: UnitState | None = None,
    item_type_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PhysicalUnit]:
    statement = select(PhysicalUnit)
    if search:
        statement = statement.where(PhysicalUnit.inventory_code.ilike(f"%{search}%"))
    if state is not None:
        statement = statement.where(PhysicalUnit.state == state)
    if item_type_id is not None:
        statement = statement.join(ItemCard).where(ItemCard.item_type_id == item_type_id)
    return list(session.scalars(statement.order_by(PhysicalUnit.inventory_code).limit(limit)).all())


@router.post("/reservations", response_model=ReservationOut, status_code=201, tags=["reservas"])
def request_reservation(
    data: ReservationCreate, actor: MemberActor, session: SessionDep
) -> Reservation:
    return create_reservation(
        session, actor, data.unit_id, data.starts_at, data.ends_at, data.intended_use
    )


@router.get("/reservations", response_model=list[ReservationOut], tags=["reservas"])
def list_reservations(
    actor: MemberActor,
    session: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[Reservation]:
    statement = select(Reservation)
    if actor.role != Role.INVENTORY_ADMIN:
        statement = statement.where(Reservation.applicant_id == actor.id)
    return list(
        session.scalars(statement.order_by(Reservation.starts_at.desc()).limit(limit)).all()
    )


@router.post(
    "/reservations/{reservation_id}/decision",
    response_model=ReservationOut,
    tags=["reservas"],
)
def decide_reservation_route(
    reservation_id: UUID,
    data: ReservationDecision,
    actor: AdminActor,
    session: SessionDep,
) -> Reservation:
    return decide_reservation(session, reservation_id, actor, data.confirm, data.reason)


@router.post(
    "/reservations/{reservation_id}/cancel",
    response_model=ReservationOut,
    tags=["reservas"],
)
def cancel_reservation_route(
    reservation_id: UUID,
    actor: MemberActor,
    session: SessionDep,
    reason: str | None = Query(default=None, max_length=1000),
) -> Reservation:
    return cancel_reservation(session, reservation_id, actor, reason)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UseCaseError)
    async def use_case_error_handler(_request: Request, error: UseCaseError) -> JSONResponse:
        return JSONResponse(status_code=error.status_code, content={"detail": error.detail})

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_request: Request, _error: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": "La operación viola una regla de unicidad o integridad"},
        )
