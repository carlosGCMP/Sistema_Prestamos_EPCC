"""Inicia el proyecto; en Windows 11 requiere Docker Desktop con contenedores Linux."""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StartupError(Exception):
    """Error de preparación que se puede mostrar sin un traceback."""


def run(
    *command: str, capture_output: bool = False, timeout: int | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=capture_output,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def find_docker() -> str:
    if executable := shutil.which("docker"):
        return executable
    if sys.platform == "win32":
        # Docker Desktop puede estar instalado sin que la terminal haya actualizado PATH.
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        executable_path = program_files / "Docker/Docker/resources/bin/docker.exe"
        if executable_path.is_file():
            return str(executable_path)
    raise StartupError(
        "No se encontró Docker. Instala Docker Desktop en Windows 11 "
        "y vuelve a abrir la terminal. En Linux, instala Docker Engine y Compose."
    )


def check_docker(docker: str) -> None:
    try:
        server = run(docker, "info", "--format", "{{.OSType}}", capture_output=True, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise StartupError(
            "No se puede acceder al motor Docker. En Windows 11 abre Docker Desktop "
            "y espera a que indique 'Engine running'. Usa el motor WSL 2 "
            "(Settings > General > Use the WSL 2 based engine). "
            "En Linux comprueba el servicio y los permisos con 'docker info'."
        ) from error
    if server.stdout.strip() != "linux":
        raise StartupError(
            "PostgreSQL necesita contenedores Linux. En Docker Desktop selecciona "
            "'Switch to Linux containers' y vuelve a ejecutar el script."
        )
    try:
        help_text = run(docker, "compose", "up", "--help", capture_output=True, timeout=20)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        raise StartupError(
            "Docker Compose no está disponible. Actualiza Docker Desktop o instala "
            "el complemento Compose de Docker Engine."
        ) from error
    if not all(flag in help_text.stdout.split() for flag in ("--wait", "--wait-timeout")):
        raise StartupError(
            "Docker Compose es demasiado antiguo: debe admitir --wait y --wait-timeout. "
            "Actualiza Docker Desktop o el complemento Compose."
        )


def compose(docker: str, *arguments: str, timeout: int | None = None) -> None:
    # La ruta explícita evita usar otro proyecto indicado en COMPOSE_FILE o en la terminal.
    run(docker, "compose", "--file", str(ROOT / "docker-compose.yml"), *arguments, timeout=timeout)


def start_database(docker: str) -> None:
    compose(docker, "config", "--quiet", timeout=20)
    print("Iniciando PostgreSQL en 127.0.0.1:5433 y esperando a que esté saludable…", flush=True)
    try:
        compose(docker, "up", "-d", "--wait", "--wait-timeout", "90", "db")
    except subprocess.CalledProcessError as error:
        diagnostic = f'docker compose --file "{ROOT / "docker-compose.yml"}"'
        raise StartupError(
            "PostgreSQL no pudo arrancar o no quedó saludable en el tiempo permitido. "
            "Comprueba que el puerto 5433 no lo ocupe otro servicio y revisa, desde esta carpeta:\n"
            f"  {diagnostic} ps -a db\n"
            f"  {diagnostic} logs --tail 50 db\n"
            "No borres el volumen ni uses 'down -v': los datos existentes se conservan."
        ) from error
    print("PostgreSQL está saludable. Los datos se conservan en el volumen Docker.", flush=True)


def prepare_env(root: Path) -> None:
    destination = root / ".env"
    if destination.exists():
        return
    content = (root / ".env.example").read_text(encoding="utf-8")
    content = content.replace(
        "replace-with-a-random-secret-of-at-least-32-characters", secrets.token_urlsafe(48)
    )
    with destination.open("x", encoding="utf-8") as output:
        output.write(content)
    if os.name != "nt":
        destination.chmod(0o600)
    print("Configuración .env creada con una clave JWT propia.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--prepare-only", action="store_true", help="Preparar sin iniciar el servidor HTTP"
    )
    mode.add_argument(
        "--docker-only",
        action="store_true",
        help="Iniciar solo PostgreSQL, sin crear .env ni instalar Python ni ejecutar migraciones",
    )
    args = parser.parse_args()
    if sys.version_info < (3, 13):  # noqa: UP036 -- también se ejecuta antes de instalar el proyecto
        raise SystemExit("Se requiere Python 3.13 o posterior.")
    docker = find_docker()
    check_docker(docker)
    if args.docker_only:
        start_database(docker)
        return
    prepare_env(ROOT)

    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creando el entorno virtual local…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    executable = str(python)
    run(executable, "-m", "pip", "install", "-c", "constraints.txt", "-e", ".")
    start_database(docker)
    run(executable, "-m", "alembic", "upgrade", "head")
    run(executable, "-m", "app.bootstrap_admin")
    if not args.prepare_only:
        print("Interfaz: http://127.0.0.1:8000/ · PostgreSQL local: puerto 5433", flush=True)
        run(executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")


if __name__ == "__main__":
    try:
        main()
    except StartupError as error:
        raise SystemExit(str(error)) from error
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"Un comando terminó con código {error.returncode}. Revisa el error anterior. "
            "No se han eliminado contenedores ni volúmenes automáticamente."
        ) from error
    except subprocess.TimeoutExpired as error:
        raise SystemExit(
            "Docker tardó demasiado en responder. Comprueba Docker Desktop."
        ) from error
    except OSError as error:
        raise SystemExit(
            f"No se pudo preparar el proyecto. Revisa las rutas y permisos: {error}"
        ) from error
    except KeyboardInterrupt:
        print("\nAPI detenida. PostgreSQL conserva sus datos; para detenerlo: docker compose down")
