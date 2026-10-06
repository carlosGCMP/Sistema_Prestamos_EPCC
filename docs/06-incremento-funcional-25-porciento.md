# Incremento funcional — 25 %

## Objetivo

Pasar de la base técnica del 10 % a un primer backend utilizable que conecte identidad, inventario, políticas, reservas y el ciclo básico del préstamo. El porcentaje es una referencia de avance del proyecto completo, no una afirmación de que el sistema esté listo para producción.

## Incluido

- API modular en FastAPI y persistencia SQLAlchemy sobre PostgreSQL.
- Migración inicial Alembic y configuración por variables de entorno.
- Personas, perfiles mínimos, cuentas locales, contraseñas Argon2id, JWT, roles, bloqueo de sesión y comando interactivo para el primer administrador.
- Catálogo de categorías, tipos, fichas y unidades con código patrimonial único.
- Políticas versionadas por rol/tipo, duración, cupos, modalidad, elegibilidad y renovaciones; el préstamo conserva una instantánea de la política aplicada.
- Reserva solicitada, confirmada/rechazada y cancelada.
- Entrega, renovación y devolución de unidades.
- Reglas: intervalos semiabiertos `[inicio, fin)`, unidad con un préstamo abierto como máximo, validación de cupo concurrente del solicitante, vencimiento que no libera el bien, y transacciones con bloqueo de filas en PostgreSQL.
- Auditoría para eventos principales, health check/readiness, OpenAPI y pruebas automatizadas iniciales.

## Fuera de alcance

Garantías, incidencias, sanciones/apelaciones, integración con matrícula o directorio institucional, frontend, notificaciones programadas, operación de mora automatizada, despliegue productivo, observabilidad, backup y pruebas de carga. La elegibilidad académica es un dato manual temporal; no sustituye una integración institucional.

## Verificación y limitaciones

Las pruebas locales usan SQLite en memoria para validar API, autenticación y ciclo de dependencias. La base productiva objetivo sigue siendo PostgreSQL; antes de integrar a `main` debe ejecutarse `alembic upgrade head` y la suite de integración con PostgreSQL 16 mediante Docker Compose. La máquina donde se realizó este incremento no tenía activo el daemon Docker, así que esa comprobación queda pendiente.

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

## Siguiente corte sugerido

Probar migraciones y flujo completo en PostgreSQL 16; implementar vencimiento automático y reportes operativos; formalizar reglas de mora y garantizar que las transiciones de estado, cupos y reservas reflejen los acuerdos institucionales.
