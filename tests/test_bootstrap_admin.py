"""El alta interactiva permite corregir entradas sin tocar PostgreSQL local."""

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import bootstrap_admin
from app.core.security import verify_password
from app.infrastructure import database
from app.infrastructure.models import Account, Administrador, Person, Role, Solicitante

ENTRADAS = ["87654321", "Ana", "Pérez", "ana@unsa.edu.pe", "admin"]
CLAVE = "clave-administrativa-de-prueba"


@pytest.fixture
def interaccion(
    monkeypatch: pytest.MonkeyPatch, session_factory: sessionmaker[Session]
) -> Callable[[list[str], list[str]], tuple[Mock, Mock]]:
    motor = session_factory.kw["bind"]
    monkeypatch.setattr(bootstrap_admin, "inicializar_base_datos", lambda: motor)
    monkeypatch.setattr(database, "crear_sesion", session_factory)

    def configurar(entradas: list[str], claves: list[str]) -> tuple[Mock, Mock]:
        leer = Mock(side_effect=entradas)
        secreto = Mock(side_effect=claves)
        monkeypatch.setattr("builtins.input", leer)
        monkeypatch.setattr(bootstrap_admin, "getpass", secreto)
        return leer, secreto

    return configurar


def comprobar_cuenta(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as sesion:
        cuenta = sesion.scalar(select(Account))
        assert cuenta is not None and cuenta.username == "admin"
        assert verify_password(CLAVE, cuenta.password_hash)
        assert cuenta.person.first_names == "Ana"
        assert cuenta.person.last_names == "Pérez"
        assert cuenta.person.is_admin
        assert cuenta.person.role == Role.ADMINISTRATIVE
        assert cuenta.person.applicant is not None
        assert sesion.scalar(select(func.count()).select_from(Administrador)) == 1


def comprobar_sin_cuentas(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as sesion:
        for modelo in (Person, Account, Administrador, Solicitante):
            assert sesion.scalar(select(func.count()).select_from(modelo)) == 0


def test_crear_administrador_con_datos_validos(
    interaccion, session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    interaccion(ENTRADAS, [CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)
    salida = capsys.readouterr().out
    assert "Cuenta administrativa 'admin' creada" in salida
    assert CLAVE not in salida


@pytest.mark.parametrize("indice", range(5))
def test_campos_vacios_se_vuelven_a_pedir(
    indice: int,
    interaccion,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:  # type: ignore[no-untyped-def]
    entradas = ENTRADAS[:indice] + ["", "   "] + ENTRADAS[indice:]
    leer, _ = interaccion(entradas, [CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)
    assert leer.call_count == 7
    assert capsys.readouterr().out.count("este campo es obligatorio") == 2


@pytest.mark.parametrize(
    ("indice", "invalido"),
    [
        (0, "1"),
        (0, "1" * 21),
        (1, "A" * 101),
        (2, "A" * 101),
        (3, "a@b"),
        (3, "a" * 151),
        (4, "ab"),
        (4, "a" * 51),
    ],
)
def test_longitudes_invalidas_se_pueden_corregir(
    indice: int,
    invalido: str,
    interaccion,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    entradas = ENTRADAS[:indice] + [invalido] + ENTRADAS[indice:]
    interaccion(entradas, [CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)


def test_correo_sin_formato_se_puede_corregir(
    interaccion, session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    interaccion(ENTRADAS[:3] + ["correo-invalido", ENTRADAS[3], ENTRADAS[4]], [CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)
    assert "dirección válida" in capsys.readouterr().out


@pytest.mark.parametrize("invalida", ["", " " * 12, "corta", "SECRETO" * 30])
def test_clave_invalida_no_se_muestra_y_se_puede_corregir(
    invalida: str,
    interaccion,
    session_factory: sessionmaker[Session],
    capsys: pytest.CaptureFixture[str],
) -> None:  # type: ignore[no-untyped-def]
    _, secreto = interaccion(ENTRADAS, [invalida, CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)
    assert secreto.call_count == 3
    salida = capsys.readouterr().out
    if invalida.strip():
        assert invalida not in salida
    assert CLAVE not in salida


def test_confirmacion_distinta_no_aborta_el_alta(
    interaccion, session_factory: sessionmaker[Session], capsys: pytest.CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    interaccion(ENTRADAS, [CLAVE, "otra-clave", CLAVE, CLAVE])
    bootstrap_admin.main()
    comprobar_cuenta(session_factory)
    assert "Las contraseñas no coinciden" in capsys.readouterr().out


@pytest.mark.parametrize("error", [EOFError, KeyboardInterrupt])
@pytest.mark.parametrize("en_clave", [False, True])
def test_cancelar_no_crea_registros_parciales(
    error: type[BaseException],
    en_clave: bool,
    interaccion,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    leer, secreto = interaccion(ENTRADAS, [CLAVE, CLAVE])
    if en_clave:
        secreto.side_effect = error
    else:
        leer.side_effect = error
    with pytest.raises(SystemExit, match="Creación cancelada"):
        bootstrap_admin.main()
    comprobar_sin_cuentas(session_factory)


def test_validacion_final_no_muestra_contrasena_ni_traza(
    interaccion,
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    interaccion(ENTRADAS, [CLAVE, CLAVE])
    error = ValidationError.from_exception_data(
        "PersonCreate",
        [
            {
                "type": "string_too_short",
                "loc": ("password",),
                "input": CLAVE,
                "ctx": {"min_length": 100},
            }
        ],
    )
    monkeypatch.setattr(bootstrap_admin, "PersonCreate", Mock(side_effect=error))
    with pytest.raises(SystemExit, match="No se creó ninguna cuenta") as resultado:
        bootstrap_admin.main()
    assert CLAVE not in str(resultado.value)
    assert "ValidationError" not in str(resultado.value)
    assert "Datos de la cuenta no válidos" in str(resultado.value)
    assert "Contraseña: no alcanza la longitud mínima" in str(resultado.value)
    assert "Configuración de inicio" not in str(resultado.value)
    comprobar_sin_cuentas(session_factory)


@pytest.mark.parametrize(
    ("campo", "tipo", "variable"),
    [
        ("database_wait_seconds", "int_parsing", "DATABASE_WAIT_SECONDS"),
        ("access_token_minutes", "int_parsing", "ACCESS_TOKEN_MINUTES"),
        ("DATABASE_URL", "missing", "DATABASE_URL"),
        ("jwt_secret", "string_type", "JWT_SECRET"),
    ],
)
def test_error_de_configuracion_no_se_confunde_con_datos_del_usuario(
    campo: str,
    tipo: str,
    variable: str,
    interaccion,
    monkeypatch: pytest.MonkeyPatch,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    leer, secreto = interaccion([], [])
    error = ValidationError.from_exception_data(
        "Settings", [{"type": tipo, "loc": (campo,), "input": CLAVE}]
    )
    monkeypatch.setattr(bootstrap_admin, "inicializar_base_datos", Mock(side_effect=error))
    with pytest.raises(SystemExit) as resultado:
        bootstrap_admin.main()
    mensaje = str(resultado.value)
    assert "Configuración de inicio no válida" in mensaje
    assert variable in mensaje
    assert ".env" in mensaje
    assert CLAVE not in mensaje
    assert "Datos de la cuenta no válidos" not in mensaje
    leer.assert_not_called()
    secreto.assert_not_called()
    comprobar_sin_cuentas(session_factory)


def test_fuera_de_la_raiz_indica_database_url_faltante(tmp_path: Path) -> None:
    raiz = Path(__file__).resolve().parents[1]
    configuracion = {
        "DATABASE_URL",
        "APP_ENV",
        "DATABASE_WAIT_SECONDS",
        "JWT_SECRET",
        "ACCESS_TOKEN_MINUTES",
    }
    entorno = {clave: valor for clave, valor in os.environ.items() if clave not in configuracion}
    entorno["PYTHONPATH"] = str(raiz)
    codigo = """
import app.infrastructure.database as database
# No contactar PostgreSQL: interesa la carga del archivo .env, no la conectividad.
database.esperar_base_datos = lambda: None
from app.bootstrap_admin import main
main()
"""
    resultado = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=tmp_path,
        env=entorno,
        input="",
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert resultado.returncode == 1
    assert "Configuración de inicio no válida" in resultado.stderr
    assert "DATABASE_URL: es obligatorio" in resultado.stderr
    assert "raíz del proyecto" in resultado.stderr
    assert "Traceback" not in resultado.stderr
    assert resultado.stdout == ""


def test_no_crea_un_segundo_administrador(
    interaccion,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    interaccion(ENTRADAS, [CLAVE, CLAVE])
    bootstrap_admin.main()
    leer, secreto = interaccion([], [])
    with pytest.raises(SystemExit, match="Ya existe una cuenta administrativa"):
        bootstrap_admin.main()
    leer.assert_not_called()
    secreto.assert_not_called()
    comprobar_cuenta(session_factory)


def test_usuario_duplicado_revierte_el_alta_sin_traza(
    interaccion,
    session_factory: sessionmaker[Session],
) -> None:  # type: ignore[no-untyped-def]
    from datetime import date

    with session_factory.begin() as sesion:
        persona = Person(
            first_names="Existente",
            last_names="Sin administrador",
            document_type="DNI",
            document_number="11111111",
            institutional_email="existente@example.test",
            role=Role.ADMINISTRATIVE,
            school_affiliation="EPCC",
            start_date=date.today(),
        )
        sesion.add(persona)
        sesion.flush()
        sesion.add(Account(person_id=persona.id, username="admin", password_hash="no-es-una-clave"))
    interaccion(ENTRADAS, [CLAVE, CLAVE])
    with pytest.raises(SystemExit, match="ya está registrado"):
        bootstrap_admin.main()
    with session_factory() as sesion:
        assert sesion.scalar(select(func.count()).select_from(Person)) == 1
        assert sesion.scalar(select(func.count()).select_from(Account)) == 1
        assert sesion.scalar(select(func.count()).select_from(Administrador)) == 0
