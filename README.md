# Sistema de Préstamos EPCC

API para una implementación inicial del sistema de préstamos de bienes de la EPCC. El alcance activo se limita a usuarios, catálogo/inventario y reservas.

## Estado actual

La rama `implementacion-basica` fija un alcance inicial y acotado; `feat/frontend-basico` añade la primera interfaz web sobre esa base. Los porcentajes estiman alcance del proyecto; no representan cobertura de pruebas ni preparación para producción.

El flujo habilitado permite registrar y autenticar usuarios, administrar categorías/tipos/fichas/unidades de inventario, y solicitar, aprobar, rechazar y cancelar reservas con control de intervalos y disponibilidad. Incluye una interfaz web básica en HTML, CSS y JavaScript que consume la API. No incluye políticas configurables, préstamos, garantías, incidentes, sanciones ni integraciones institucionales. Los borradores de pantallas sin backend se conservan, pero sus accesos están deshabilitados y marcados como pendientes.

Las migraciones versionadas existentes se conservan para evitar eliminar datos o reescribir el historial; el esquema físico aún contiene tablas de capacidades aplazadas. No se ejecuta una migración destructiva para borrarlas.

## Tecnologías

- Python 3.13 y FastAPI.
- HTML, CSS y JavaScript nativo para el frontend básico, servido por FastAPI.
- SQLAlchemy 2, Psycopg 3, PostgreSQL 16 y Alembic.
- Pydantic, JWT y Argon2id.
- pytest, Ruff, mypy y Docker Compose.

## Inicio rápido

Requisitos: Python 3.13+, Docker con Docker Compose moderno e Internet para la primera instalación. Docker debe estar iniciado y los puertos locales **5433** (PostgreSQL) y **8000** (web) disponibles.

Desde la raíz del proyecto, incluso si lo descargaste como ZIP:

```bash
python3 scripts/iniciar.py
```

En Windows: `py -3 scripts/iniciar.py`. No hace falta activar el entorno virtual ni instalar Node.js o PostgreSQL por separado.

El script crea `.env` con una clave JWT aleatoria si no existe, crea `.venv`, instala las versiones de `constraints.txt`, espera a que PostgreSQL esté listo, aplica las migraciones y pide crear el primer administrador. Si ya hay administrador, conserva la cuenta existente. Por último inicia la web en `http://127.0.0.1:8000/`.

Para preparar sin dejar el servidor ejecutándose: `python3 scripts/iniciar.py --prepare-only`.

### Arranque manual (Linux/macOS)

```bash
test -f .env || cp .env.example .env
docker compose up -d --wait db
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -c constraints.txt -e '.[dev]'
# Sustituye el JWT_SECRET de ejemplo por una clave propia antes de compartir el acceso.
alembic upgrade head
python -m app.bootstrap_admin
uvicorn app.main:app --reload
```

La documentación interactiva está en `http://127.0.0.1:8000/docs`; readiness está en `http://127.0.0.1:8000/health/ready`. El comando de bootstrap crea la primera cuenta de administración de forma interactiva; no hay credenciales predeterminadas.

La interfaz web está en `http://127.0.0.1:8000/`. No requiere Node.js ni un proceso de frontend separado.

PostgreSQL se publica en `127.0.0.1:5433`; dentro del contenedor sigue usando `5432`. La URL local predeterminada es `postgresql+psycopg://epcc:epcc@localhost:5433/epcc_prestamos`. Las credenciales `epcc/epcc` son solo para la demostración local, no para producción.

Para detener la API, usa `Ctrl+C`. Para detener PostgreSQL conservando los datos, ejecuta `docker compose down` (no agregues `-v` salvo que quieras eliminar el volumen local).

## Entrega por Classroom

Consulta la [guía de ZIP, Classroom y ejecución en otro equipo](docs/11-entrega-classroom.md). El ZIP debe llevar el código versionado y `.env.example`, **no** `.env`, `.venv`, `.git` ni datos personales. La base de datos vive en Docker y **no viaja con el código**.

## Estructura

```text
app/
  api/               Rutas HTTP y composición de la API
  application/       Casos de uso y esquemas de entrada/salida
  core/              Seguridad y configuración transversal
  infrastructure/    Persistencia SQLAlchemy y modelos ORM
  main.py            Construcción de la aplicación FastAPI
  bootstrap_admin.py Alta interactiva del primer administrador
frontend/            Interfaz HTML, CSS y JavaScript servida por FastAPI
migrations/          Historial versionado del esquema PostgreSQL
tests/               Pruebas de usuarios, inventario, reservas y configuración
scripts/iniciar.py   Preparación y arranque multiplataforma desde el ZIP
constraints.txt      Versiones verificadas de dependencias
docs/                Arquitectura, planificación y entregables
.vscode/             Preferencias para ocultar artefactos locales del explorador
```

La documentación personal y los informes históricos no vigentes se conservan fuera del repositorio, en la carpeta hermana `Sistema_Prestamos_EPCC_material_local/`.

La separación actual es técnica; los módulos activos comparten una API, una base PostgreSQL y transacciones SQLAlchemy. El navegador consume el backend por HTTP en el mismo origen; no se conecta directamente a PostgreSQL. Las capacidades diferidas no deben interpretarse como funciones disponibles.

## Verificación

```bash
source .venv/bin/activate
python -m pip install -c constraints.txt -e '.[dev]'
ruff check app tests scripts/iniciar.py
ruff format --check app tests scripts/iniciar.py
mypy app
pytest
node --check frontend/app.js  # Opcional: Node.js solo para comprobar sintaxis
```

Las pruebas HTTP cubren el alcance básico activo, incluidos login/logout, permisos, inventario, confirmación/rechazo/cancelación de reservas y conflictos de intervalos. Por defecto usan SQLite en memoria. Para comprobar PostgreSQL se puede definir `EPCC_TEST_DATABASE_URL` apuntando a una base exclusiva de pruebas: cada caso crea y elimina únicamente su propio esquema temporal. Consulta la guía de entrega para los comandos. No se reactivaron las funciones avanzadas para satisfacer pruebas antiguas.

## Documentación

Comienza por el [índice de documentación](docs/README.md), revisa el [plan básico](docs/09-alcance-basico-y-plan.md) y el [tablero Kanban](docs/10-tablero-kanban-local.md). Los documentos de incrementos anteriores se conservan como referencias históricas.
