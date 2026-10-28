# Modelo de dominio del alcance básico

El diagrama general conserva la visión completa del sistema. La implementación de esta etapa se limita a las entidades y responsabilidades siguientes:

| Módulo | Entidades | Responsabilidad |
| --- | --- | --- |
| Usuarios | `Persona`, `Account`, perfiles y `Role` | Registrar personas/cuentas, autenticar, autorizar y desactivar cuentas. |
| Catálogo e inventario | `Category`, `ItemType`, `ItemCard`, `PhysicalUnit` | Clasificar bienes y administrar ejemplares identificados individualmente. |
| Reservas | `Reservation` | Solicitar, confirmar, rechazar y cancelar reservas por unidad e intervalo. |
| Transversal | `AuditEvent` | Registrar operaciones relevantes con su actor y fecha. |

## Relaciones

- Una persona puede asociarse a una cuenta para autenticarse; el acceso se determina mediante roles.
- Una categoría agrupa tipos de bien y cada tipo pertenece a una categoría.
- Un tipo agrupa fichas de catálogo; una ficha puede tener varias unidades físicas.
- Cada unidad física se identifica por su código de inventario.
- Una reserva relaciona a una persona solicitante con una unidad concreta.
- Un evento de auditoría identifica al actor y la entidad afectada.

## Reglas principales

1. Los códigos de cuenta y de inventario deben ser únicos.
2. `ADMIN_INVENTARIO` administra personas, catálogo, unidades y decisiones de reserva.
3. Solo solicitantes con cuenta activa pueden crear reservas.
4. Las fechas deben incluir zona horaria, el inicio debe ser futuro y el fin posterior al inicio.
5. Solo unidades activas y prestables admiten confirmación.
6. Una reserva confirmada ocupa la unidad en `[inicio, fin)`. Dos intervalos se solapan si `inicio1 < fin2` y `inicio2 < fin1`.
7. Al confirmar, el sistema bloquea la unidad y revalida su estado y conflictos en la misma transacción.
8. El titular o un usuario autorizado puede cancelar una reserva según su estado.

## Fuera del corte activo

Las políticas de préstamo, elegibilidad académica, préstamos, renovaciones, devoluciones, garantías, incidencias, sanciones y apelaciones no se exponen como funcionalidades operativas de esta etapa. Permanecen como conceptos de diseño futuro o histórico.
