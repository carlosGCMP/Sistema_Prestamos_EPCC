# Entrega ZIP por Classroom y ejecución

## 1. Preparar el código que vas a entregar

Desde el repositorio original:

```bash
git switch feat/frontend-basico
git status --short
```

La salida del segundo comando debe estar vacía. Si modificaste código después de esta integración, revísalo y haz commit antes de empaquetar: `git archive` incluye el último commit, no cambios sin guardar/versionar.

Comprueba el proyecto:

```bash
python3 scripts/iniciar.py --prepare-only
.venv/bin/python -m pip install -c constraints.txt -e '.[dev]'
.venv/bin/python -m pytest
.venv/bin/ruff check app tests scripts/iniciar.py
.venv/bin/mypy app
```

En Windows sustituye `.venv/bin/python` por `.venv\Scripts\python.exe`, `.venv/bin/ruff` por `.venv\Scripts\ruff.exe` y `.venv/bin/mypy` por `.venv\Scripts\mypy.exe`.

## 2. Crear y subir el ZIP

```bash
git archive --format=zip --prefix=Sistema_Prestamos_EPCC/ --output=../Sistema_Prestamos_EPCC.zip HEAD
```

El archivo queda en la carpeta superior al repositorio. Ábrelo para comprobar que lleva `README.md`, `pyproject.toml`, `constraints.txt`, `.env.example`, `docker-compose.yml`, `alembic.ini`, `app/`, `frontend/`, `migrations/` y `scripts/iniciar.py`.

Este método incluye solamente archivos versionados. No incluye `.git`, `.venv`, `.env`, cachés ni volúmenes Docker. No agregues estos archivos privados al repositorio para incluirlos en la entrega.

1. Abre la tarea de Google Classroom.
2. Selecciona **Añadir o crear → Archivo → Subir**.
3. Elige `Sistema_Prestamos_EPCC.zip`, espera a que termine la carga y pulsa **Entregar**.
4. En las instrucciones de la tarea indica: «Extraer el ZIP, instalar Python 3.13+ y Docker, iniciar Docker y ejecutar `python3 scripts/iniciar.py` (Windows: `py -3 scripts/iniciar.py`)».

## 3. Descargar en otro equipo

Requisitos del equipo receptor:

- Python **3.13 o posterior**, con `pip` y `venv`. En Linux puede ser necesario instalar el paquete `python3-venv` correspondiente a esa versión.
- Docker Engine con el complemento Compose o Docker Desktop iniciado, usando contenedores Linux. `docker compose version` debe funcionar y admitir `up --wait`.
- Internet para descargar dependencias e imagen PostgreSQL en la primera ejecución.
- Puertos locales **5433** y **8000** libres. No es necesario instalar PostgreSQL nativo, Node.js, Git ni VS Code para ejecutar el ZIP.

Descarga el archivo desde Classroom y **extráelo por completo** a una carpeta local con permisos de escritura. No ejecutes scripts dentro del visor del ZIP. Abre una terminal en la carpeta extraída que contiene `pyproject.toml`.

Linux/macOS:

```bash
python3 --version
docker compose version
python3 scripts/iniciar.py
```

Windows (PowerShell):

```powershell
py -3 --version
docker compose version
py -3 scripts/iniciar.py
```

No necesitas activar `.venv` en PowerShell: el script utiliza directamente el Python del entorno virtual, evitando problemas con la política de ejecución de scripts.

## 4. Qué hace el arranque

1. Genera `.env` desde `.env.example`, con una clave JWT aleatoria propia. Si `.env` existe, **no lo sobrescribe**.
2. Crea el entorno virtual local `.venv` e instala el proyecto con las versiones verificadas de `constraints.txt`.
3. Ejecuta `docker compose up -d --wait --wait-timeout 90 db` y espera a que PostgreSQL esté saludable.
4. Ejecuta `alembic upgrade head`. No debes ejecutar manualmente los SQL de `base de datos/`: son un diseño de referencia alternativo, no las migraciones de la API.
5. Solicita los datos del primer administrador y una contraseña de al menos 12 caracteres. No hay usuario/contraseña web predeterminados. Si ya existe administrador, conserva el existente.
6. Inicia FastAPI y sirve el frontend en el mismo proceso.

La contraseña no se muestra al escribirla; es normal. Guarda tus credenciales. La cuenta `epcc/epcc` es la del motor PostgreSQL local, **no** una cuenta para iniciar sesión en la web.

Abre:

- **Web:** <http://127.0.0.1:8000/>
- **API interactiva:** <http://127.0.0.1:8000/docs>
- **Conexión a PostgreSQL:** <http://127.0.0.1:8000/health/ready>, que debe responder `{"status":"ready"}`.

El puerto **5433 pertenece a PostgreSQL**, no a la web. Docker traduce `127.0.0.1:5433` del equipo al `5432` interno del contenedor. La API y Alembic leen:

```dotenv
DATABASE_URL=postgresql+psycopg://epcc:epcc@localhost:5433/epcc_prestamos
```

Las variables de entorno de la terminal tienen prioridad sobre `.env`. Si habías exportado otra `DATABASE_URL`, elimínala o corrígela antes de arrancar. La API se ejecuta en el equipo, no en un contenedor de aplicación; no cambies `localhost` por `db` en este flujo.

## 5. Comprobación funcional

1. Inicia sesión con el administrador creado.
2. Crea, en orden, una categoría, un tipo reservable, una ficha de catálogo y una unidad física.
3. Crea un usuario estudiante con CUI/identificador, código universitario, programa y semestre; o un docente con identificador, código y especialidad.
4. Cierra sesión, entra como ese usuario y solicita una reserva con fechas futuras.
5. Entra como administrador y confirma o rechaza la reserva.
6. Como solicitante, comprueba su estado y cancélala si corresponde.

El alcance ejecutable es **usuarios, inventario y reservas**. Préstamos/devoluciones, políticas y vinculación académica siguen pendientes; sus pantallas borrador no se presentan como funciones operativas.

## 6. Detener y volver a ejecutar

Detén la API con `Ctrl+C`. Para detener PostgreSQL sin borrar información:

```bash
docker compose down
```

Para volver a arrancar, desde la **misma carpeta**:

```bash
python3 scripts/iniciar.py
```

En Windows usa `py -3`. Se conservan `.env`, la cuenta inicial y los datos del volumen. No uses `docker compose down -v`: elimina los datos. Si cambias de nombre/carpeta o de proyecto Compose, puedes estar seleccionando otro volumen y ver una base vacía.

## 7. Los datos no viajan dentro del ZIP

El ZIP transporta código y migraciones, no la base local ni las cuentas. En otro equipo se crea una base nueva y un administrador nuevo. No compartas datos personales reales en una entrega académica. Si necesitas conservar datos de demostración, acuerda un respaldo anonimizado por separado; copiar `.venv` o el directorio interno del volumen no es un respaldo portable.

## 8. Solución de problemas

| Error | Qué comprobar |
| --- | --- |
| Python anterior a 3.13 | Instala una versión compatible y vuelve a crear únicamente el entorno virtual de esta copia. |
| Docker no disponible/permisos | Inicia Docker Desktop o el servicio Docker y comprueba `docker info`. En Linux, configura los permisos de tu usuario sobre Docker. |
| Puerto 5433 ocupado | Comprueba `docker ps`. Detén solo la instancia anterior de este proyecto u otro servicio que reconozcas; no borres contenedores o volúmenes ajenos. |
| Puerto 8000 ocupado | Detén el servidor anterior con `Ctrl+C`, o arranca manualmente Uvicorn con otro puerto. |
| Conexión rechazada o contraseña PostgreSQL incorrecta | Revisa `.env`, variables exportadas, `docker compose ps` y `docker compose logs db`. La contraseña de un volumen ya inicializado no cambia por editar Compose. No elimines el volumen para «arreglarlo» si contiene información necesaria. |
| Falta `frontend/` o una migración | Extrae de nuevo el ZIP completo y ejecuta desde la raíz del proyecto. |
| Red bloqueada | La primera instalación necesita acceso a PyPI y al registro de imágenes Docker; este ZIP no es un instalador sin conexión. |

Si necesitas cambiar credenciales del motor, actualiza tanto Compose como `.env` y realiza explícitamente el cambio en PostgreSQL si el volumen ya existía. Las credenciales del ejemplo y el servidor HTTP local no son una configuración de producción.

## 9. Pruebas con PostgreSQL en 5433

Además de `pytest` con SQLite, puedes usar una base **exclusiva de pruebas**:

```bash
docker compose exec -T db createdb -U epcc epcc_pruebas
DATABASE_URL=postgresql+psycopg://epcc:epcc@localhost:5433/epcc_pruebas .venv/bin/python -m alembic upgrade head
EPCC_TEST_DATABASE_URL=postgresql+psycopg://epcc:epcc@localhost:5433/epcc_pruebas .venv/bin/python -m pytest
```

Los comandos de asignación de variables anteriores son para Linux/macOS. En PowerShell usa `$env:DATABASE_URL = "..."` / `$env:EPCC_TEST_DATABASE_URL = "..."` y elimina esas variables con `Remove-Item Env:DATABASE_URL` / `Remove-Item Env:EPCC_TEST_DATABASE_URL` al terminar. Usa `.venv\Scripts\python.exe`.

Cada prueba PostgreSQL crea un esquema con nombre aleatorio y elimina solo ese esquema. Las migraciones deben comprobarse contra la base de pruebas, no contra datos reales.
