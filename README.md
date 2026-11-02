# Sistema de Préstamos EPCC

API para una implementación inicial del sistema de préstamos de bienes de la EPCC. El alcance activo se limita a usuarios, catálogo/inventario y reservas.

## Estado actual

La rama `implementacion-basica` fija un alcance inicial y acotado; `feat/frontend-basico` añade la primera interfaz web sobre esa base. Los porcentajes estiman alcance del proyecto; no representan cobertura de pruebas ni preparación para producción.

El flujo habilitado permite registrar y autenticar usuarios, administrar categorías/tipos/fichas/unidades de inventario, y solicitar, aprobar, rechazar y cancelar reservas con control de intervalos y disponibilidad. Incluye una interfaz web básica en HTML, CSS y JavaScript que consume la API. No incluye políticas configurables, préstamos, garantías, incidentes, sanciones ni integraciones institucionales. Los servicios avanzados de iteraciones anteriores se conservan en el historial técnico, pero no están expuestos por la API básica.

El arranque valida las tablas existentes y crea las faltantes desde los modelos actuales, sin ejecutar migraciones ni borrar datos. Los SQL originales y las migraciones históricas se conservan intactos, pero no forman parte del arranque. La adaptación del nuevo diseño SQL al dominio todavía no está implementada.

## Tecnologías

- Python 3.13 y FastAPI.
- HTML, CSS y JavaScript nativo para el frontend básico, servido por FastAPI.
- SQLAlchemy 2, Psycopg 3 y PostgreSQL 16.
- Pydantic, JWT y Argon2id.
- pytest, Ruff, mypy y Docker Compose.

## Inicio rápido

Requisitos: Python 3.13+, Docker y Docker Compose.

```bash
cp .env.example .env
docker compose up -d db
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload
```

No sobrescribas `.env` si ya tiene tu configuración. PostgreSQL se espera hasta 30 segundos (configurable con `DATABASE_WAIT_SECONDS`). Si una tabla existente es incompatible, el arranque se detiene con una explicación; no modifica ni convierte sus datos.

En Windows 11 con Docker Desktop y contenedores Linux, usa PowerShell:

```powershell
Copy-Item .env.example .env
docker compose up -d db
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

La documentación interactiva está en `http://127.0.0.1:8000/docs`; readiness está en `http://127.0.0.1:8000/health/ready`.

Las tablas se crean automáticamente, pero no se inventan credenciales. Si todavía no existe un administrador, créalo una sola vez desde otra terminal con el entorno virtual activado:

```bash
python -m app.bootstrap_admin
```

La interfaz web está en `http://127.0.0.1:8000/`. No requiere Node.js ni un proceso de frontend separado.

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
frontend/            Interfaz HTML, CSS y JavaScript servida por FastAPI
migrations/          Historial versionado del esquema PostgreSQL
tests/               Pruebas de conexión y escenarios funcionales anteriores
docs/                Arquitectura, planificación y entregables
.vscode/             Preferencias para ocultar artefactos locales del explorador
```

La documentación personal y los informes históricos no vigentes se conservan fuera del repositorio, en la carpeta hermana `Sistema_Prestamos_EPCC_material_local/`.

La separación actual es técnica; los módulos activos comparten una API, una base PostgreSQL y transacciones SQLAlchemy. El navegador consume el backend por HTTP en el mismo origen; no se conecta directamente a PostgreSQL. Las capacidades diferidas no deben interpretarse como funciones disponibles.

Para entender el código, comienza por [conexión y flujo del aplicativo](docs/11-conexion-y-flujo.md): explica el arranque, las sesiones, las transacciones y el recorrido de un formulario hasta PostgreSQL.

## Verificación estática disponible

```bash
source .venv/bin/activate
pytest tests/test_database.py tests/test_health.py
ruff check app
ruff format --check app
mypy app
```

Las pruebas de conexión y salud se ejecutan sin PostgreSQL y verifican el arranque, la creación de tablas, el rechazo de esquemas incompatibles y las transacciones. La suite completa conserva dos fallos anteriores en `tests/test_auth_and_api.py` y `tests/test_lending_workflow.py`, porque esperan rutas de préstamos y políticas que la API básica no expone. La alineación de esos escenarios está pendiente en el issue [#15](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/15).

## Documentación

Comienza por el [índice de documentación](docs/README.md), revisa el [plan básico](docs/09-alcance-basico-y-plan.md) y el [tablero Kanban](docs/10-tablero-kanban-local.md). Los documentos de incrementos anteriores se conservan como referencias históricas.
