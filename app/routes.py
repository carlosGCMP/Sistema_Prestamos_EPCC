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

from app.application.use_cases import (
    UseCaseError,
    audit,
    cancel_reservation,
    create_loan,
    create_person,
    create_policy,
    create_reservation,
    decide_reservation,
    new_category,
    new_item,
    new_item_type,
    new_unit,
    renew_loan,
    return_loan,
)
from app.database import get_session
from app.models import (
    Account,
    AuditEvent,
    Category,
    ItemCard,
    ItemType,
    Loan,
    LoanPolicy,
    Person,
    PersonState,
    PhysicalUnit,
    Renewal,
    Reservation,
    Role,
    UnitState,
)
from app.schemas import (
    AuditOut,
    CategoryCreate,
    CategoryOut,
    ItemCreate,
    ItemOut,
    LoanCreate,
    LoanOut,
    PersonCreate,
    PersonOut,
    PolicyCreate,
    PolicyOut,
    RenewalCreate,
    RenewalOut,
    ReservationCreate,
    ReservationDecision,
    ReservationOut,
    ReturnCreate,
    TokenResponse,
    TypeCreate,
    TypeOut,
    UnitCreate,
    UnitOut,
)
from app.security import (
    AdminActor,
    CurrentAccount,
    MemberActor,
    create_access_token,
    verify_password,
)
from app.settings import get_settings

router = APIRouter()
SessionDep = Annotated[Session, Depends(get_session)]


@router.post("/auth/token", response_model=TokenResponse, tags=["autenticación"])
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


@router.post("/auth/logout", status_code=204, tags=["autenticación"])
def logout(account: CurrentAccount) -> None:
    # Incrementing the version invalidates all previously issued access tokens.
    account.session_version += 1


@router.get("/me", response_model=PersonOut, tags=["identidad"])
def me(actor: MemberActor) -> Person:
    return actor


@router.post("/people", response_model=PersonOut, status_code=201, tags=["identidad"])
def register_person(data: PersonCreate, actor: AdminActor, session: SessionDep) -> Person:
    return create_person(session, data, actor)


@router.get("/people/{person_id}", response_model=PersonOut, tags=["identidad"])
def get_person(person_id: UUID, _actor: AdminActor, session: SessionDep) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return person


@router.post("/people/{person_id}/deactivate", response_model=PersonOut, tags=["identidad"])
def deactivate_person(person_id: UUID, actor: AdminActor, session: SessionDep) -> Person:
    person = session.get(Person, person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    person.state = PersonState.INACTIVE
    if person.account:
        person.account.active = False
        person.account.session_version += 1
    audit(session, actor, "PERSONA_DESACTIVADA", "Person", person.id)
    return person


@router.post(
    "/inventory/categories", response_model=CategoryOut, status_code=201, tags=["inventario"]
)
def create_category(data: CategoryCreate, actor: AdminActor, session: SessionDep) -> Category:
    return new_category(session, data.name, data.description, actor)


@router.get("/inventory/categories", response_model=list[CategoryOut], tags=["inventario"])
def list_categories(_actor: MemberActor, session: SessionDep) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)).all())


@router.post("/inventory/types", response_model=TypeOut, status_code=201, tags=["inventario"])
def create_type(data: TypeCreate, actor: AdminActor, session: SessionDep) -> ItemType:
    return new_item_type(session, data.name, data.category_id, data.lendable, actor)


@router.get("/inventory/types", response_model=list[TypeOut], tags=["inventario"])
def list_types(_actor: MemberActor, session: SessionDep) -> list[ItemType]:
    return list(session.scalars(select(ItemType).order_by(ItemType.name)).all())


@router.post("/inventory/items", response_model=ItemOut, status_code=201, tags=["inventario"])
def create_item(data: ItemCreate, actor: AdminActor, session: SessionDep) -> ItemCard:
    return new_item(session, data, actor)


@router.get("/inventory/items", response_model=list[ItemOut], tags=["inventario"])
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
) -> list[PhysicalUnit]:
    statement = select(PhysicalUnit)
    if search:
        statement = statement.where(PhysicalUnit.inventory_code.ilike(f"%{search}%"))
    if state:
        statement = statement.where(PhysicalUnit.state == state)
    if item_type_id:
        statement = statement.join(ItemCard).where(ItemCard.item_type_id == item_type_id)
    return list(session.scalars(statement.order_by(PhysicalUnit.inventory_code)).all())


@router.post("/policies", response_model=PolicyOut, status_code=201, tags=["políticas"])
def add_policy(data: PolicyCreate, actor: AdminActor, session: SessionDep) -> LoanPolicy:
    if data.item_type_id and session.get(ItemType, data.item_type_id) is None:
        raise HTTPException(status_code=404, detail="Tipo de bien no encontrado")
    return create_policy(session, data, actor)


@router.get("/policies", response_model=list[PolicyOut], tags=["políticas"])
def list_policies(_actor: AdminActor, session: SessionDep) -> list[LoanPolicy]:
    return list(
        session.scalars(
            select(LoanPolicy).order_by(LoanPolicy.role, LoanPolicy.name, LoanPolicy.version)
        ).all()
    )


@router.post("/reservations", response_model=ReservationOut, status_code=201, tags=["reservas"])
def request_reservation(
    data: ReservationCreate, actor: MemberActor, session: SessionDep
) -> Reservation:
    if actor.role in (Role.ADMINISTRATIVE, Role.INVENTORY_ADMIN):
        raise HTTPException(status_code=403, detail="El rol administrativo no solicita préstamos")
    return create_reservation(
        session, actor, data.unit_id, data.starts_at, data.ends_at, data.intended_use
    )


@router.get("/reservations", response_model=list[ReservationOut], tags=["reservas"])
def list_reservations(actor: MemberActor, session: SessionDep) -> list[Reservation]:
    statement = select(Reservation)
    if actor.role != Role.INVENTORY_ADMIN:
        statement = statement.where(Reservation.applicant_id == actor.id)
    return list(session.scalars(statement.order_by(Reservation.starts_at.desc())).all())


@router.post(
    "/reservations/{reservation_id}/decision", response_model=ReservationOut, tags=["reservas"]
)
def decide_reservation_route(
    reservation_id: UUID,
    data: ReservationDecision,
    actor: AdminActor,
    session: SessionDep,
) -> Reservation:
    return decide_reservation(session, reservation_id, actor, data.confirm, data.reason)


@router.post(
    "/reservations/{reservation_id}/cancel", response_model=ReservationOut, tags=["reservas"]
)
def cancel_reservation_route(
    reservation_id: UUID,
    actor: MemberActor,
    session: SessionDep,
    reason: str | None = Query(default=None, max_length=1000),
) -> Reservation:
    return cancel_reservation(session, reservation_id, actor, reason)


@router.post("/loans", response_model=LoanOut, status_code=201, tags=["préstamos"])
def register_loan(data: LoanCreate, actor: AdminActor, session: SessionDep) -> Loan:
    return create_loan(session, data, actor)


@router.get("/loans", response_model=list[LoanOut], tags=["préstamos"])
def list_loans(actor: AdminActor, session: SessionDep) -> list[Loan]:
    return list(session.scalars(select(Loan).order_by(Loan.created_at.desc())).all())


@router.get("/loans/mine", response_model=list[LoanOut], tags=["préstamos"])
def list_my_loans(actor: MemberActor, session: SessionDep) -> list[Loan]:
    statement = select(Loan)
    if actor.role != Role.INVENTORY_ADMIN:
        statement = statement.where(Loan.applicant_id == actor.id)
    return list(session.scalars(statement.order_by(Loan.created_at.desc())).all())


@router.post(
    "/loans/{loan_id}/renewals", response_model=RenewalOut, status_code=201, tags=["préstamos"]
)
def authorize_renewal(
    loan_id: UUID, data: RenewalCreate, actor: AdminActor, session: SessionDep
) -> Renewal:
    return renew_loan(session, loan_id, data.new_due_at, actor)


@router.post("/loans/{loan_id}/return", response_model=LoanOut, tags=["préstamos"])
def record_return(
    loan_id: UUID, data: ReturnCreate, actor: AdminActor, session: SessionDep
) -> Loan:
    return return_loan(session, loan_id, data, actor)


@router.get("/audit", response_model=list[AuditOut], tags=["auditoría"])
def list_audit(
    _actor: AdminActor,
    session: SessionDep,
    entity_type: str | None = Query(default=None, max_length=80),
    entity_id: str | None = Query(default=None, max_length=36),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditEvent]:
    statement = select(AuditEvent)
    if entity_type:
        statement = statement.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        statement = statement.where(AuditEvent.entity_id == entity_id)
    return list(
        session.scalars(statement.order_by(AuditEvent.occurred_at.desc()).limit(limit)).all()
    )


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
