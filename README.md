# Sistema de Préstamos EPCC

Sistema de préstamos de bienes de la EPCC con interfaz web y API en Python.

## Estado actual

Están habilitados usuarios, catálogo/inventario, reservas, **políticas, préstamos y vinculación académica**. La interfaz utiliza HTML, CSS y JavaScript nativo y consume la API desde el mismo servidor.

El recorrido es **solicitar reserva → confirmar → entregar → devolver**. Se aplican siete políticas: cuentas activas, bienes disponibles, máximo inicial de **2 bienes simultáneos por persona y tipo**, duración de **3 días corridos para estudiantes y 7 para docentes**, sin cruces, aprobación administrativa sin autoconfirmación y cancelación controlada. Las políticas se publican por versiones; las reservas confirmadas y los préstamos conservan las condiciones aprobadas.

La vinculación académica permite registrar manualmente períodos, información académica y matrículas. No incluye consulta institucional automática, bloqueos académicos, multas, garantías, incidentes, sanciones, renovaciones ni prórrogas. Consulta la explicación sencilla en [políticas y guía de uso](docs/13-politicas-y-guia-de-uso.md).

El esquema físico utiliza las 43 tablas de los SQL originales, más `bien` y `prestamo`, con nombres y columnas en español e identificadores BIGINT. Los módulos nuevos reutilizan esas 45 tablas sin cambiar columnas. El arranque valida las tablas existentes, crea solo las faltantes y carga catálogos y políticas iniciales sin ejecutar migraciones ni borrar datos. Si ya existe una versión para un rol y tipo, no la reemplaza. Los SQL originales, la conexión protegida y las migraciones históricas se conservan intactos. Consulta las relaciones en [esquema en español](docs/12-esquema-espanol.md).

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

El esquema anterior con UUID y tablas en inglés no se transforma automáticamente ni se mezcla con el nuevo. Su recreación requiere autorización y respaldo. Las tablas de capacidades fuera del alcance no habilitan sus procesos por sí solas.

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

Introduce documento, nombres, apellidos, correo y usuario; no hay valores predeterminados.
Los campos vacíos o inválidos se vuelven a pedir. La contraseña debe tener entre 12 y
128 caracteres y no se muestra al escribirla. Usa `Ctrl+C` para cancelar sin crear cuentas.
Espera el mensaje de creación exitosa antes de iniciar sesión en la plataforma.

Si el comando falla **antes de pedir los datos**, revisa el aviso de configuración:
indicará la variable que falta o es inválida, sin mostrar su valor. `.env` se carga
desde el directorio actual, así que ejecuta el comando desde la raíz del proyecto.
Para asegurar el intérprete correcto en Linux puedes usar directamente:

```bash
./.venv/bin/python -m app.bootstrap_admin
```

En Windows, el equivalente es `.\.venv\Scripts\python.exe -m app.bootstrap_admin`.
No sobrescribas tu `.env` existente ni compartas sus contraseñas para diagnosticarlo.

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
tests/               Pruebas de conexión, permisos y recorridos funcionales
docs/                Arquitectura, planificación y entregables
.vscode/             Preferencias para ocultar artefactos locales del explorador
```

La documentación personal y los informes históricos no vigentes se conservan fuera del repositorio, en la carpeta hermana `Sistema_Prestamos_EPCC_material_local/`.

La separación actual es técnica; los módulos activos comparten una API, una base PostgreSQL y transacciones SQLAlchemy. El navegador consume el backend por HTTP en el mismo origen; no se conecta directamente a PostgreSQL. Las capacidades diferidas no deben interpretarse como funciones disponibles.

Para entender el código, comienza por [conexión y flujo del aplicativo](docs/11-conexion-y-flujo.md): explica el arranque, las sesiones, las transacciones y el recorrido de un formulario hasta PostgreSQL.

## Verificación

```bash
source .venv/bin/activate
pytest
ruff check app tests
ruff format --check app tests
mypy app
```

La suite utiliza SQLite aislado, sin acceder a PostgreSQL local. Comprueba las 45 tablas y sus claves foráneas, BIGINT, arranque, transacciones, permisos, inventario, reservas, versiones de políticas, entregas, devoluciones y registros académicos. No exige instalar herramientas de navegador ni Node.js.

## Documentación

Comienza por [políticas y guía de uso](docs/13-politicas-y-guia-de-uso.md) o por el [índice de documentación](docs/README.md). Los planes básicos y documentos de incrementos anteriores se conservan como referencias históricas, no como descripción de funciones pendientes actuales.
