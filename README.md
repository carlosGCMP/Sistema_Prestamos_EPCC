# Sistema de Préstamos EPCC

API para una implementación inicial del sistema de préstamos de bienes de la EPCC. El alcance activo se limita a usuarios, catálogo/inventario y reservas.

## Estado actual

La rama `implementacion-basica` restablece un alcance inicial y acotado. Los porcentajes estiman alcance del proyecto; no representan cobertura de pruebas ni preparación para producción.

El flujo habilitado permite registrar y autenticar usuarios, administrar categorías/tipos/fichas/unidades de inventario, y solicitar, aprobar, rechazar y cancelar reservas con control de intervalos y disponibilidad. No incluye políticas configurables, préstamos, garantías, incidentes, sanciones ni integraciones institucionales. Los servicios avanzados de iteraciones anteriores se conservan en el historial técnico, pero no están expuestos por la API básica.

Las migraciones versionadas existentes se conservan para evitar eliminar datos o reescribir el historial; el esquema físico aún contiene tablas de capacidades aplazadas. No se ejecuta una migración destructiva para borrarlas.

## Tecnologías

- Python 3.13 y FastAPI.
- SQLAlchemy 2, Psycopg 3, PostgreSQL 16 y Alembic.
- Pydantic, JWT y Argon2id.
- pytest, Ruff, mypy y Docker Compose.

## Inicio rápido

Requisitos: Python 3.13+, Docker y Docker Compose.

```bash
test -f .env || cp .env.example .env
docker compose up -d db
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
python -m app.bootstrap_admin
uvicorn app.main:app --reload
```

La documentación interactiva está en `http://127.0.0.1:8000/docs`; readiness está en `http://127.0.0.1:8000/health/ready`. El comando de bootstrap crea la primera cuenta de administración de forma interactiva; no hay credenciales predeterminadas.

Para detener la API, usa `Ctrl+C`. Para detener PostgreSQL conservando los datos, ejecuta `docker compose down` (no agregues `-v` salvo que quieras eliminar el volumen local).

## Estructura

```text
app/
  api/               Rutas HTTP y composición de la API
  application/       Casos de uso y esquemas de entrada/salida
  core/              Seguridad y configuración transversal
  infrastructure/    Persistencia SQLAlchemy y modelos ORM
  main.py            Construcción de la aplicación FastAPI
  bootstrap_admin.py Alta interactiva del primer administrador
migrations/          Historial versionado del esquema PostgreSQL
tests/               Pruebas automatizadas anteriores, pendientes de ajustar al corte
docs/                Arquitectura, planificación y entregables
```

La separación actual es técnica; los módulos activos comparten una API, una base PostgreSQL y transacciones SQLAlchemy. Las capacidades diferidas no deben interpretarse como funciones disponibles.

## Verificación estática disponible

```bash
source .venv/bin/activate
ruff check app
ruff format --check app
mypy app
```

La suite actual contiene escenarios de módulos avanzados anteriores y debe alinearse con el corte básico antes de usar `pytest` o `scripts/verify_postgresql.sh`; ese trabajo está en el issue [#15](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/15). Ruff y mypy pasan; no se ejecutó la suite automatizada.

## Documentación

Comienza por el [índice de documentación](docs/README.md), revisa el [plan básico](docs/09-alcance-basico-y-plan.md) y el [tablero Kanban](docs/10-tablero-kanban-local.md). Los documentos de incrementos anteriores se conservan como referencias históricas.
