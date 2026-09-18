# Sistema de Préstamos EPCC

Sistema para gestionar el préstamo de bienes de la Escuela Profesional de Ciencia de la Computación (EPCC): usuarios, inventario, reservas, préstamos, devoluciones, garantías, incidencias, sanciones y trazabilidad.

El proyecto se iniciará como un **monolito modular** en Python y PostgreSQL. Conserva los límites de los contextos definidos en el modelo de dominio, sin introducir la complejidad operativa de microservicios antes de necesitarla.

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

La API quedará disponible en `http://localhost:8000` y su contrato navegable en `http://localhost:8000/docs`.

## Documentación

- [Visión y alcance](docs/01-vision-y-alcance.md)
- [Arquitectura y tecnologías](docs/02-arquitectura-y-tecnologias.md)
- [Modelo de dominio y módulos](docs/03-dominio-y-modulos.md)
- [Plan de implementación](docs/04-plan-de-implementacion.md)
- [Decisiones de arquitectura](docs/adr/README.md)

## Estado

Se ha creado la base técnica y documental. El siguiente incremento implementará identidad y acceso, y el catálogo de inventario mínimo necesario para habilitar préstamos.
