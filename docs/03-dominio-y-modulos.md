# Modelo de dominio y módulos

Esta es la traducción de los contextos delimitados entregados a módulos de implementación. No implica crear diez servicios independientes.

| Código | Módulo | Responsabilidad | Prioridad |
| --- | --- | --- | --- |
| BC01 | Identidad y acceso | Personas, cuentas, perfiles, roles y atribuciones. | MVP |
| BC02 | Vinculación académica | Matrícula, período y condición académica. | MVP (mínimo) |
| BC03 | Catálogo e inventario | Ficha de bien, tipo, unidad física, estado y ubicación. | MVP |
| BC04 | Políticas de préstamo | Reglas por perfil/tipo: plazo, renovaciones, cupos. | MVP |
| BC05 | Reservas | Cola, vigencia, disponibilidad y cupo. | MVP básico |
| BC06 | Préstamos | Entrega, devolución, renovación y cálculo de retraso. | MVP |
| BC07 | Garantías | Tipos, garantía asociada y su liberación. | Posterior |
| BC08 | Incidencias | Daño, pérdida, reporte y resolución. | Posterior |
| BC09 | Sanciones | Sanción, apelación, cumplimiento y bloqueo. | Posterior |
| BC10 | Auditoría | Evento histórico, actor y trazabilidad. | MVP |

## Agregados iniciales

- **Persona**: identidad, cuenta y roles. No contiene datos de préstamos.
- **Unidad física**: representa el ejemplar prestable; guarda disponibilidad, ubicación y estado operativo.
- **Política de préstamo**: determina las condiciones permitidas. Al crear un préstamo se persiste una `PolíticaAplicada` inmutable.
- **Reserva**: solicitud por ficha/tipo o unidad según la política, con prioridad y vencimiento.
- **Préstamo**: agregado transaccional de entrega, vencimiento, devolución y renovaciones.

## Reglas que deben ser invariantes

1. Una unidad física solo puede tener un préstamo activo a la vez.
2. Solo una persona elegible y sin bloqueo puede recibir un préstamo.
3. La entrega necesita una política vigente y una unidad disponible.
4. Una renovación no puede superar el límite de la política ni ignorar una reserva prioritaria.
5. Una devolución cierra el préstamo, actualiza el estado de la unidad y genera evento de auditoría.

## Integración entre módulos

El caso de uso de entrega consulta puertos de elegibilidad, bloqueo, política y disponibilidad; luego crea el préstamo en una única transacción. Tras confirmarse, publica eventos como `PrestamoEntregado` o `PrestamoDevuelto` para que auditoría y, después, notificaciones reaccionen. Evitar transacciones distribuidas y llamadas HTTP internas.
