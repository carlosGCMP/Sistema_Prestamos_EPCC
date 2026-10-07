# Incremento funcional — 25 %

## Objetivo

Pasar de la base técnica del 10 % a un primer backend utilizable que conecte identidad, inventario, políticas, reservas y el ciclo básico del préstamo. El porcentaje es una referencia de avance del proyecto completo, no una afirmación de que el sistema esté listo para producción.

## Incluido

- API modular en FastAPI y persistencia SQLAlchemy sobre PostgreSQL.
- Migración inicial Alembic y configuración por variables de entorno.
- Personas, perfiles mínimos, cuentas locales, contraseñas Argon2id, JWT, bloqueo de sesión y roles diferenciados: la afiliación `PERSONAL_ADMINISTRATIVO` por sí sola no concede el permiso `ADMIN_INVENTARIO`.
- Catálogo de categorías, tipos, fichas y unidades con código patrimonial único.
- Políticas versionadas por rol/tipo, duración, cupos, modalidad, elegibilidad y renovaciones; el préstamo conserva una instantánea de la política aplicada.
- Reserva solicitada, confirmada/rechazada y cancelada.
- Entrega, renovación y devolución de unidades.
- Reglas: intervalos semiabiertos `[inicio, fin)`, unidad con un préstamo abierto como máximo, validación de cupo concurrente del solicitante, vencimiento que no libera el bien, y transacciones con bloqueo de filas en PostgreSQL.
- Auditoría para eventos principales, health check/readiness, OpenAPI y pruebas automatizadas iniciales.

## Fuera de alcance

Garantías, incidencias, sanciones/apelaciones, integración con matrícula o directorio institucional, frontend, notificaciones programadas, operación de mora automatizada, despliegue productivo, observabilidad, backup y pruebas de carga. La elegibilidad académica es un dato manual temporal; no sustituye una integración institucional.

## Verificación y limitaciones

La verificación ejecutada en el entorno de desarrollo incluye Python 3.13.15, PostgreSQL 16 en Docker Compose, `alembic upgrade head`, 7 pruebas automatizadas, Ruff y mypy. Se verificaron también la disponibilidad de la API y la conexión a PostgreSQL. La base se dejó sin cuentas ni registros de demostración: la muestra manual corresponde al estudiante y está descrita paso a paso en [08-demostracion-manual-25-porciento.md](08-demostracion-manual-25-porciento.md).

Las siete pruebas automatizadas usan SQLite en memoria; la migración se ejecutó contra PostgreSQL 16. No se ejecutaron pruebas de carga ni se verificó una instalación productiva. No se debe interpretar este 25 % como un sistema terminado. La CI de GitHub está configurada para repetir controles y migración en cada cambio, pendiente de pasar en el PR de este incremento.

## Puesta en marcha

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

OpenAPI: `http://localhost:8000/docs`. Estado de proceso: `/health`; disponibilidad de base de datos: `/health/ready`.

Guía para realizar personalmente el recorrido funcional en Swagger: [muestra manual del 25 %](08-demostracion-manual-25-porciento.md).

## Siguiente corte sugerido

Implementar vencimiento automático y reportes operativos; formalizar reglas de mora y validar con la EPCC las políticas, roles, cupos, plazos, consecuencias de retraso y tratamiento de pérdidas/daños antes de ampliar el dominio.
