# Visión y alcance

## Problema

La EPCC necesita controlar el ciclo de vida de los bienes prestables: conocer qué unidad física se entrega, a quién, bajo qué reglas, cuándo debe regresar y qué ocurrió durante el préstamo. El sistema debe evitar entregas no autorizadas o sin disponibilidad y conservar evidencia auditable de cada decisión.

## Objetivo del producto

Ofrecer una aplicación web con API para que personal autorizado administre bienes, políticas y operaciones de préstamo; y para que estudiantes y personal consulten, reserven y sigan sus solicitudes.

## Alcance del primer producto viable (MVP)

1. Autenticación y autorización por rol.
2. Catálogo de bienes y unidades físicas, con estado y ubicación.
3. Registro académico/administrativo básico del solicitante y validación de elegibilidad.
4. Políticas de préstamo configurables por perfil y tipo de bien.
5. Solicitud, reserva, entrega, devolución y renovación de préstamos.
6. Auditoría de las operaciones críticas.

## Fuera del MVP

- Integración automática con sistemas institucionales de matrícula o identidad.
- Cobros/pagos en línea y notificaciones multicanal.
- Flujos completos de garantías, incidencias, sanciones y apelaciones. Se modelarán para no bloquear su incorporación posterior.
- Aplicación móvil nativa.

## Roles iniciales

| Rol | Responsabilidades principales |
| --- | --- |
| Estudiante/docente | Consultar catálogo, solicitar/reservar y ver sus préstamos. |
| Personal administrativo | Registrar entrega y devolución, administrar reservas según permisos. |
| Encargado de inventario | Mantener fichas, unidades físicas, estado y ubicación. |
| Administrador | Gestionar usuarios, roles, políticas y configuración. |

## Criterios de éxito iniciales

- No se puede entregar una unidad que no esté disponible ni a una persona bloqueada/no elegible.
- Cada entrega y devolución identifica actor, fecha, unidad física y condición.
- Las reglas aplicadas al préstamo quedan registradas incluso si la política luego cambia.
- El personal puede reconstruir el historial de una unidad y de un préstamo.
