"""Prepara y ejecuta la entrega, incluso después de extraerla de un ZIP."""

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


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
    parser.add_argument(
        "--prepare-only", action="store_true", help="Preparar sin iniciar el servidor HTTP"
    )
    args = parser.parse_args()
    if sys.version_info < (3, 13):  # noqa: UP036 -- también se ejecuta antes de instalar el proyecto
        raise SystemExit("Se requiere Python 3.13 o posterior.")
    if shutil.which("docker") is None:
        raise SystemExit("Instala Docker y Docker Compose antes de continuar.")
    run("docker", "compose", "version")
    prepare_env(ROOT)

    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("Creando el entorno virtual local…", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    executable = str(python)
    run(executable, "-m", "pip", "install", "-c", "constraints.txt", "-e", ".")
    run("docker", "compose", "up", "-d", "--wait", "--wait-timeout", "90", "db")
    run(executable, "-m", "alembic", "upgrade", "head")
    run(executable, "-m", "app.bootstrap_admin")
    if not args.prepare_only:
        print("Interfaz: http://127.0.0.1:8000/ · PostgreSQL local: puerto 5433", flush=True)
        run(executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "No se pudo completar el arranque. Revisa el error anterior, que Docker esté "
            "iniciado y que los puertos 5433 y 8000 estén libres."
        ) from error
    except KeyboardInterrupt:
        print("\nAPI detenida. PostgreSQL conserva sus datos; para detenerlo: docker compose down")
