"""Crea la primera persona, cuenta, solicitante y atribución administrativa."""

from datetime import date
from getpass import getpass

from sqlalchemy import select

from app.application.basic_use_cases import create_person
from app.application.schemas import PersonCreate
from app.infrastructure.database import abrir_sesion, inicializar_base_datos
from app.infrastructure.models import Administrador, Role


def main() -> None:
    inicializar_base_datos()
    with abrir_sesion() as sesion:
        if sesion.scalar(select(Administrador.id)):
            raise SystemExit("Ya existe una cuenta administrativa; no se creó otra.")
        documento = input("Número de documento: ").strip()
        nombres = input("Nombres: ").strip()
        apellidos = input("Apellidos: ").strip()
        correo = input("Correo institucional: ").strip()
        usuario = input("Usuario: ").strip()
        clave = getpass("Contraseña (mínimo 12 caracteres): ")
        if clave != getpass("Confirmar contraseña: "):
            raise SystemExit("Las contraseñas no coinciden.")
        datos = PersonCreate(
            document_type="DNI",
            document_number=documento,
            first_names=nombres,
            last_names=apellidos,
            institutional_email=correo,
            role=Role.ADMINISTRATIVE,
            is_admin=True,
            school_affiliation="EPCC",
            start_date=date.today(),
            username=usuario,
            password=clave,
        )
        create_person(sesion, datos, None)
    print(f"Cuenta administrativa '{usuario}' creada.")


if __name__ == "__main__":
    main()
