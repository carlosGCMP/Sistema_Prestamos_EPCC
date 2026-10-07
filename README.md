# Sistema de Préstamos EPCC

Sistema para gestionar el préstamo de bienes de la Escuela Profesional de Ciencia de la Computación (EPCC): usuarios, inventario, reservas, préstamos, devoluciones, garantías, incidencias, sanciones y trazabilidad.

El proyecto se iniciará como un **monolito modular** en Python y PostgreSQL. Conserva los límites de los contextos definidos en el modelo de dominio, sin introducir la complejidad operativa de microservicios antes de necesitarla.

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

La API quedará disponible en `http://localhost:8000` y su contrato navegable en `http://localhost:8000/docs`.

Para detenerla, interrumpe Uvicorn con `Ctrl+C`. PostgreSQL se puede detener sin borrar sus datos con `docker compose down`.

## Documentación

- [Visión y alcance](docs/01-vision-y-alcance.md)
- [Arquitectura y tecnologías](docs/02-arquitectura-y-tecnologias.md)
- [Modelo de dominio y módulos](docs/03-dominio-y-modulos.md)
- [Plan de implementación](docs/04-plan-de-implementacion.md)
- [Incremento inicial (10 %)](docs/05-incremento-inicial-10-porciento.md)
- [Incremento funcional (25 %)](docs/06-incremento-funcional-25-porciento.md)
- [Base para elaborar el informe del 25 %](docs/07-contexto-para-informe-25-porciento.md)
- [Paso a paso para tu muestra manual](docs/08-demostracion-manual-25-porciento.md)
- [Informe presentable del primer examen](docs/entregables/informe-primer-examen.pdf)
- [Decisiones de arquitectura](docs/adr/README.md)

## Estado

El incremento funcional del 25 % implementa identidad local, catálogo e inventario, políticas versionadas, reservas, entrega/renovación/devolución de préstamos, auditoría y migración inicial. Garantías, incidencias, sanciones, apelaciones, integración académica institucional e interfaz web quedan fuera de este corte.
