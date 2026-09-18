# Arquitectura y tecnologías

## Decisión principal: monolito modular

La especificación identifica diez contextos delimitados. Se implementarán como módulos internos con contratos explícitos, una API y una base PostgreSQL compartida **al inicio**. Así se acelera la entrega, las transacciones de inventario/préstamo son consistentes y se conserva una vía clara para extraer un contexto si la escala lo justifica.

No habrá dependencias directas entre modelos de dominio de módulos distintos. La coordinación se hará mediante casos de uso, interfaces (puertos) y eventos de dominio publicados dentro del proceso.

```text
Cliente web (pendiente de seleccionar)
          │ HTTPS / JSON
FastAPI ──┼── módulos de aplicación ── dominio
          │                              │
          └── infraestructura ───────── PostgreSQL
                         └───────────── auditoría / eventos
```

## Stack propuesto

| Área | Elección | Motivo |
| --- | --- | --- |
| Lenguaje | Python 3.13 | Tipado moderno, ecosistema sólido y productividad. |
| API | FastAPI | OpenAPI automático, validación con Pydantic y soporte asíncrono cuando se requiera. |
| Dominio | Python tipado + Pydantic solo en bordes | Entidades y reglas independientes del framework; DTOs validados en la API. |
| Persistencia | SQLAlchemy 2 + Psycopg 3 | ORM maduro, transacciones explícitas y buen soporte PostgreSQL. |
| Base de datos | PostgreSQL 16 | Integridad referencial, bloqueo/transacciones y tipos avanzados. |
| Migraciones | Alembic | Versiona el esquema junto al código. |
| Autenticación | OAuth2 password flow + JWT de corta vida | Adecuado para el inicio; después se puede federar con identidad institucional. |
| Pruebas | pytest + httpx | Pruebas unitarias del dominio e integración de API. |
| Calidad | Ruff + mypy | Formato/lint rápido y contratos de tipos. |
| Desarrollo local | Docker Compose | PostgreSQL reproducible sin instalarlo localmente. |
| Despliegue | Contenedores Docker + CI | Mismo artefacto entre desarrollo, pruebas y producción. |

## Frontend

La primera fase entrega una API documentada para validar reglas de negocio. Para el panel web se recomienda **React + TypeScript + Vite**, consumiendo OpenAPI; no se debe iniciar hasta estabilizar los flujos de catálogo y préstamo. Si el equipo prefiere reducir la superficie tecnológica, una interfaz administrativa renderizada en servidor es una alternativa válida que deberá decidirse antes de esa fase.

## Estructura de código objetivo

```text
app/
  shared/                 # value objects, errores y utilidades comunes
  identity_access/        # cada contexto con domain/application/infrastructure/api
  academic_link/
  inventory/
  loan_policies/
  reservations/
  loans/
  guarantees/
  incidents/
  sanctions/
  audit/
  main.py
```

Dentro de cada módulo: `domain` contiene entidades, value objects, eventos e interfaces; `application`, los casos de uso y DTOs; `infrastructure`, repositorios SQLAlchemy e integraciones; `api`, los routers HTTP. No se expondrán modelos ORM directamente por la API.

## Datos y seguridad

- Usar UUID como identificadores externos; claves internas pueden ser UUID desde el inicio.
- Conservar fechas en UTC (`timestamptz`) y representar dinero con `numeric`, nunca `float`.
- Aplicar restricciones de base de datos además de validaciones de aplicación.
- Bloquear la fila de unidad física al confirmar entrega/devolución para impedir doble préstamo concurrente.
- Contraseñas con Argon2id; secretos fuera del repositorio; TLS obligatorio en producción.
- Añadir registro de auditoría inmutable para las acciones críticas, sin guardar contraseñas ni tokens.
