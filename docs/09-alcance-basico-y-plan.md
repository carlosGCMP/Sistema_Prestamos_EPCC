# Restablecimiento al alcance básico

## Decisión de alcance

El repositorio vuelve a un corte pequeño para avanzar de forma verificable: usuarios, catálogo/inventario y reservas. Se conserva Python 3.13, FastAPI, SQLAlchemy, PostgreSQL 16, Alembic, Pydantic, JWT y Argon2. No se añaden frameworks.

## Qué está activo en la API

- `POST /auth/token`, `POST /auth/logout`, `GET /me`.
- Gestión administrativa de personas: alta, consulta, listado y desactivación.
- Gestión de categorías, tipos, fichas de bien y unidades físicas.
- Consulta de unidades por código, estado o tipo.
- Solicitud de reserva por una persona con cuenta activa, decisión administrativa y cancelación autorizada.
- Control de reserva por intervalo `[inicio, fin)`, revalidación transaccional al confirmar y auditoría.

La lista exacta y vigente de rutas se obtiene de `/openapi.json` o `/docs` al ejecutar la API.

## Qué no está activo

La API no expone políticas configurables, préstamos, renovaciones/devoluciones, condición académica, garantías, incidencias, sanciones, apelaciones ni resumen de operaciones. Tampoco se integra con sistemas externos ni incluye interfaz web.

## Persistencia y compatibilidad

Se preservaron `migrations/versions/0001`–`0003` y las tablas existentes. No se reescribió una migración aplicada ni se eliminaron datos/tablas localmente. La consecuencia es que el esquema PostgreSQL heredado contiene tablas que el router básico no usa. La limpieza futura exige inventariar el esquema y preparar una migración segura con respaldo, tal como se sigue en el issue [#16](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/16).

## Organización de la implementación

1. Mantener base técnica y esquema Alembic existente.
2. Reducir rutas HTTP al alcance solicitado.
3. Concentrar las reglas básicas en casos de uso pequeños y tipados.
4. Mantener seguridad por rol, restricciones de integridad y auditoría transaccional.
5. Añadir la cobertura focalizada del corte en el issue [#15](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/15).
6. Resolver CI/documentación de integración en [#6](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/6) y [#10](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/10).

## Estado y límites

El código de este alcance se publica en la rama `implementacion-basica`. El PR anterior del incremento del 25 % se mantiene intacto y no se mezcla con este corte. Los issues y el tablero GitHub organizan el backlog básico. El material anterior permanece en Git como historial; no debe confundirse con la funcionalidad actualmente expuesta.
