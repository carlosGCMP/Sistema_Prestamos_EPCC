# Plan de implementación

## Hito 0 — Base técnica (completado)

- Proyecto Python, API FastAPI y prueba de salud.
- PostgreSQL local con Docker Compose.
- Convenciones de dependencias, calidad y documentación.

## Hito 1 — Fundaciones, catálogo y préstamo inicial (25 % actual)

1. Configuración por entorno, conexión de base de datos y Alembic.
2. Modelo de `Persona`, cuenta, roles y autenticación.
3. Catálogo: categorías, tipos de bien, fichas y unidades físicas.
4. Políticas versionadas y validación manual mínima de elegibilidad académica.
5. Reservas con decisión administrativa y cancelación.
6. Entrega, renovación y devolución con comprobación transaccional y auditoría.
7. Pruebas de API/autenticación y guía reproducible de desarrollo.

**Resultado verificable:** un administrador inicia sesión, gestiona catálogo y políticas, confirma reservas y registra entregas, renovaciones y devoluciones; cada acción queda auditada.

## Hito 2 — Endurecimiento operativo de políticas y préstamos

1. Vencimientos automáticos, cupos completos y reglas institucionales.
2. Ampliar concurrencia y pruebas de integración contra PostgreSQL.
3. Gestión operativa de mora, reportes y notificaciones.

**Resultado verificable:** el personal entrega y devuelve una unidad; el sistema rechaza una segunda entrega concurrente y conserva la política aplicada.

## Hito 3 — Operación ampliada

1. Vencimiento automático y reglas de prioridad de reservas.
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
