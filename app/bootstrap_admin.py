"""Crea la primera persona, cuenta, solicitante y atribución administrativa."""

import re
from datetime import date
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.basic_use_cases import create_person
from app.application.schemas import PersonCreate
from app.infrastructure.database import abrir_sesion, inicializar_base_datos
from app.infrastructure.models import Administrador, Role


def explicar_validacion(error: ValidationError, *, configuracion: bool) -> str:
    """Describe campos y causas conocidas sin imprimir valores recibidos ni secretos."""
    campos = (
        {
            "database_url": "DATABASE_URL",
            "database_wait_seconds": "DATABASE_WAIT_SECONDS",
            "access_token_minutes": "ACCESS_TOKEN_MINUTES",
            "jwt_secret": "JWT_SECRET",
            "app_env": "APP_ENV",
        }
        if configuracion
        else {
            "document_number": "Número de documento",
            "first_names": "Nombres",
            "last_names": "Apellidos",
            "institutional_email": "Correo institucional",
            "username": "Usuario",
            "password": "Contraseña",
        }
    )
    causas = {
        "missing": "es obligatorio",
        "string_type": "debe ser texto",
        "string_too_short": "no alcanza la longitud mínima",
        "string_too_long": "supera la longitud máxima",
        "int_parsing": "debe ser un número entero",
        "int_type": "debe ser un número entero",
        "greater_than_equal": "es menor que el mínimo permitido",
        "less_than_equal": "supera el máximo permitido",
    }
    encabezado = (
        "Configuración de inicio no válida" if configuracion else "Datos de la cuenta no válidos"
    )
    lineas = [f"{encabezado}:"]
    for detalle in error.errors(include_input=False, include_context=False, include_url=False):
        ubicacion = detalle["loc"]
        nombre = str(ubicacion[0]).lower() if ubicacion else ""
        campo = campos.get(nombre, "Configuración" if configuracion else "Datos de la cuenta")
        causa = causas.get(detalle["type"], "no cumple los requisitos de validación")
        lineas.append(f"- {campo}: {causa}.")
    if configuracion:
        lineas.append(
            "Revisa .env y las variables de entorno. Ejecuta desde la raíz del proyecto "
            "con el Python de .venv. Si falta .env, créalo a partir de .env.example."
        )
    else:
        lineas.append("Corrige los campos indicados y vuelve a ejecutar el comando.")
    lineas.append("No se creó ninguna cuenta.")
    return "\n".join(lineas)


def leer_texto(etiqueta: str, minimo: int, maximo: int) -> str:
    """Vuelve a pedir un campo obligatorio hasta que su longitud sea válida."""
    while True:
        valor = input(f"{etiqueta}: ").strip()
        if not valor:
            print(f"{etiqueta}: este campo es obligatorio.")
        elif len(valor) < minimo:
            print(f"{etiqueta}: debe tener al menos {minimo} caracteres.")
        elif len(valor) > maximo:
            print(f"{etiqueta}: no debe superar los {maximo} caracteres.")
        else:
            return valor


def leer_correo() -> str:
    """Comprueba el formato sin necesitar paquetes adicionales."""
    while True:
        correo = leer_texto("Correo institucional", 5, 150)
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo):
            return correo
        print("Correo institucional: indica una dirección válida, por ejemplo usuario@unsa.edu.pe.")


def leer_clave() -> str:
    """No muestra ni recorta la contraseña; permite corregirla sin abortar el alta."""
    while True:
        clave = getpass("Contraseña (mínimo 12 caracteres): ")
        if not clave.strip():
            print("La contraseña es obligatoria.")
        elif not 12 <= len(clave) <= 128:
            print("La contraseña debe tener entre 12 y 128 caracteres.")
        elif clave != getpass("Confirmar contraseña: "):
            print("Las contraseñas no coinciden. Vuelve a escribirlas.")
        else:
            return clave


def solicitar_datos() -> PersonCreate:
    """Recoge datos antes de abrir la transacción que creará la cuenta."""
    print("Todos los campos son obligatorios. Usa tus datos; Ctrl+C cancela la creación.")
    documento = leer_texto("Número de documento", 2, 20)
    nombres = leer_texto("Nombres", 1, 100)
    apellidos = leer_texto("Apellidos", 1, 100)
    correo = leer_correo()
    usuario = leer_texto("Usuario", 3, 50)
    try:
        return PersonCreate(
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
            password=leer_clave(),
        )
    except ValidationError as error:
        raise SystemExit(explicar_validacion(error, configuracion=False)) from None


def comprobar_sin_administrador(sesion: Session) -> None:
    if sesion.scalar(select(Administrador.id)) is not None:
        raise SystemExit("Ya existe una cuenta administrativa; no se creó otra.")


def main() -> None:
    try:
        inicializar_base_datos()
        with abrir_sesion() as sesion:
            comprobar_sin_administrador(sesion)

        datos = solicitar_datos()

        with abrir_sesion() as sesion:
            if sesion.get_bind().dialect.name == "postgresql":
                # Serializar únicamente el alta, no la espera de las respuestas del usuario.
                sesion.execute(text("SELECT pg_advisory_xact_lock(73421002)"))
            comprobar_sin_administrador(sesion)
            create_person(sesion, datos, None)
    except (EOFError, KeyboardInterrupt):
        raise SystemExit("\nCreación cancelada. No se creó ninguna cuenta.") from None
    except ValidationError as error:
        # La validación de PersonCreate ya se atiende al recoger los datos.
        raise SystemExit(explicar_validacion(error, configuracion=True)) from None
    except IntegrityError:
        raise SystemExit(
            "El documento, correo o usuario ya está registrado, o los datos no cumplen "
            "las restricciones de la base. No se creó ninguna cuenta."
        ) from None
    print(f"Cuenta administrativa '{datos.username}' creada. Ya puedes iniciar sesión.")


if __name__ == "__main__":
    main()
