# Sistema de Préstamos EPCC

API para administrar la identidad de solicitantes, inventario de bienes, políticas, reservas y préstamos de la Escuela Profesional de Ciencia de la Computación (EPCC).

## Estado actual

El repositorio contiene un primer incremento funcional de backend, estimado como alcance del 25 % del proyecto completo. Es una referencia de avance, no una certificación de completitud ni de preparación para producción. El trabajo está en la rama `implementacion-25-porciento` y se revisa en el [PR #12](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/pull/12).

Incluye autenticación local, catálogo e inventario, políticas versionadas, reservas, entrega/renovación/devolución, auditoría, migraciones y una API OpenAPI. Garantías, incidencias, sanciones, apelaciones, integración institucional, interfaz web y despliegue productivo aún no están implementados.

La verificación local registrada es: 7 pruebas aprobadas, Ruff sin errores, mypy sin errores en 11 módulos y migración aplicada en PostgreSQL 16. La CI de GitHub aún no está activa: el issue [#6](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/6) sigue abierto porque la credencial actual no puede publicar workflows.

## Tecnologías

- Python 3.13 y FastAPI.
- SQLAlchemy 2, Psycopg 3, PostgreSQL 16 y Alembic.
- Pydantic, JWT y Argon2id.
- pytest, Ruff, mypy y Docker Compose.

## Inicio rápido

Requisitos: Python 3.13+, Docker y Docker Compose.

```bash
cp .env.example .env
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
app/                 API, casos de uso, modelos, seguridad y configuración
migrations/          Historial versionado del esquema PostgreSQL
tests/               Pruebas automatizadas de API y reglas del dominio
docs/                Arquitectura, planificación, operación y entregables
  diagramas/         Diagramas de referencia
  informes/          PDF presentable del primer examen
  adr/               Decisiones de arquitectura
scripts/             Herramientas auxiliares para documentos
```

El código conserva una estructura pequeña para el incremento actual. La separación interna más granular por contextos delimitados es una evolución futura; no se deben interpretar todos los paquetes del diagrama objetivo como ya implementados.

## Documentación

Comienza por el [índice de documentación](docs/README.md). Para ejecutar la muestra por cuenta propia, sigue [la guía manual del 25 %](docs/08-demostracion-manual-25-porciento.md). Los README locales de estado y operación son deliberadamente excluidos de Git y no se publican.
