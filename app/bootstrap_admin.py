"""Create the first administrative identity interactively."""

from datetime import date
from getpass import getpass

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Account, Person, Role
from app.security import hash_password


def main() -> None:
    with SessionLocal.begin() as session:
        if session.scalar(
            select(Account.id).join(Person).where(Person.role == Role.INVENTORY_ADMIN)
        ):
            raise SystemExit("Ya existe una cuenta administrativa; no se creó otra.")
        cui = input("CUI: ").strip()
        document_type = input("Tipo de documento [DNI]: ").strip() or "DNI"
        document_number = input("Número de documento: ").strip()
        full_name = input("Nombre completo: ").strip()
        email = input("Correo institucional: ").strip()
        username = input("Usuario: ").strip()
        password = getpass("Contraseña (mínimo 12 caracteres): ")
        confirmation = getpass("Confirmar contraseña: ")
        if password != confirmation:
            raise SystemExit("Las contraseñas no coinciden.")
        person = Person(
            cui=cui,
            document_type=document_type,
            document_number=document_number,
            full_name=full_name,
            institutional_email=email,
            role=Role.INVENTORY_ADMIN,
            school_affiliation="EPCC",
            start_date=date.today(),
        )
        session.add(person)
        session.flush()
        session.add(
            Account(person_id=person.id, username=username, password_hash=hash_password(password))
        )
    print(f"Cuenta administrativa '{username}' creada.")


if __name__ == "__main__":
    main()
