# Plan de implementación

## Hito 0 — Base técnica (actual)

- Proyecto Python, API FastAPI y prueba de salud.
- PostgreSQL local con Docker Compose.
- Convenciones de dependencias, calidad y documentación.

## Hito 1 — Fundaciones y catálogo

1. Configuración por entorno, conexión de base de datos y Alembic.
2. Modelo de `Persona`, cuenta, roles y autenticación.
3. Catálogo: tipos de bien, fichas y unidades físicas.
4. Endpoints CRUD protegidos y auditoría de cambios.
5. Pruebas de repositorio, API y autorización.

**Resultado verificable:** un administrador registra un bien y una unidad; un usuario autenticado puede consultarla.

## Hito 2 — Políticas y préstamos

1. Política configurable por perfil y tipo de bien.
2. Validación de vinculación académica mínima (manual/administrada mientras no exista integración).
3. Entrega, devolución y renovaciones.
4. Control de concurrencia para disponibilidad y bitácora de operaciones.

**Resultado verificable:** el personal entrega y devuelve una unidad; el sistema rechaza una segunda entrega concurrente y conserva la política aplicada.

## Hito 3 — Reservas y operación

1. Reserva, vencimiento y reglas de prioridad.
2. Indicadores operativos: vencidos, bienes no disponibles y reservas pendientes.
3. Notificaciones básicas por correo o tarea programada, si el canal está definido.

## Hito 4 — Excepciones y madurez

1. Garantías, incidencias, sanciones y apelaciones.
2. Integración institucional de identidad/matrícula.
3. Interfaz web para usuarios y panel administrativo.
4. Observabilidad, respaldos, CI/CD y pruebas de carga.

## Primer backlog ejecutable

| Orden | Historia | Criterio de aceptación resumido |
| --- | --- | --- |
| 1 | Como desarrollador, versiono el esquema. | Una base nueva se crea mediante migraciones. |
| 2 | Como administrador, gestiono roles. | Cada endpoint restringe acciones por permiso. |
| 3 | Como inventarista, registro unidades. | No existen dos códigos patrimoniales iguales. |
| 4 | Como administrador, defino una política. | Plazo y límite de renovaciones quedan validados. |
| 5 | Como personal, entrego una unidad. | Se validan elegibilidad, política y disponibilidad atómicamente. |
| 6 | Como personal, recibo una devolución. | Se cierra el préstamo y se registra la auditoría. |

## Decisiones pendientes que requieren validación institucional

- Fuente oficial y frecuencia de actualización de matrícula/condición académica.
- Roles concretos, niveles de autorización y responsables de aprobación.
- Identificador único de cada bien y si habrá lector de código de barras/QR.
- Reglas de préstamo por categoría y tratamiento de retrasos, daños y pérdidas.
- Requisitos de conservación de datos personales y de auditoría.
