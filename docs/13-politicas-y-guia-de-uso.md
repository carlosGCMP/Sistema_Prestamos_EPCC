# Políticas y guía de uso

Este documento explica las reglas que aplica la plataforma. Son las reglas acordadas
para este proyecto; no se presentan como un reglamento oficial de la UNSA.

## Las siete políticas

### 1. Quién puede solicitar

Pueden solicitar reservas los **estudiantes y docentes con persona y cuenta activas**.
El personal administrativo administra el sistema cuando tiene esa atribución, pero
no solicita bienes con ese rol. Ser administrador no reemplaza el rol personal.

### 2. Qué bienes se pueden reservar

La unidad debe estar disponible. Su ficha, categoría y tipo deben estar activos y
el tipo debe permitir préstamos. No se puede entregar una unidad en mantenimiento,
dada de baja o que todavía esté prestada.

### 3. Cuántos bienes puede tener una persona

El límite inicial es **2 bienes simultáneos por persona y por tipo de bien**.
Se suman las reservas confirmadas que coinciden en horario y los préstamos que
todavía no se han devuelto. Una reserva pendiente no ocupa un cupo por sí misma.

Ejemplo: si ya tienes dos laptops comprometidas para el mismo horario, no puedes
confirmar una tercera. Una reserva que termina a las 10:00 no se cruza con otra
que empieza a las 10:00. Un préstamo vencido sigue ocupando cupo hasta la devolución.

### 4. Cuánto tiempo dura

| Solicitante | Máximo inicial |
| --- | --- |
| Estudiante | **3 días corridos: 72 horas** |
| Docente o profesor | **7 días corridos: 168 horas** |

Se cuentan sábados, domingos y feriados. Una reserva de estudiante que empieza el
miércoles a las 10:00 puede terminar como máximo el sábado a las 10:00.

El administrador puede publicar un límite menor para un tipo de bien, pero no
puede superar los topes de 3 y 7 días ni el máximo de 2 bienes. La reserva debe
empezar en el futuro y su final debe ser posterior al inicio.

Entregar el bien más tarde **no reinicia el plazo**: el préstamo debe terminar como
máximo al finalizar la reserva confirmada. No se admiten entregas antes de su inicio.

### 5. No puede haber dos reservas para la misma unidad y horario

Antes de confirmar se vuelve a comprobar el horario y el estado de la unidad.
Las solicitudes pendientes no bloquean el inventario; una vez confirmada una,
otra que se cruce no puede confirmarse. La comprobación y el cambio se guardan juntos.

### 6. Quién aprueba

Solo un administrador puede confirmar o rechazar. **No puede confirmar una reserva
propia**, aunque su rol personal sea docente. El rechazo requiere un motivo.
La confirmación debe hacerse antes de que empiece la reserva.

### 7. Quién cancela

El solicitante cancela sus reservas pendientes o confirmadas **antes del inicio**.
Un administrador puede cancelarlas indicando siempre un motivo, incluso si el
horario ya comenzó. Una reserva atendida no se cancela: el bien se devuelve desde
el módulo de préstamos.

## Cómo se configuran y conservan las políticas

- Al crear un tipo de bien se preparan políticas iniciales para estudiante y docente.
- Al iniciar una instalación existente se añaden solo las que nunca se publicaron.
  No se reemplazan las decisiones del administrador ni se reactivan políticas vencidas.
- En **Políticas** se eligen tipo de bien, rol, permiso, cantidad, días y vigencia.
- Cada cambio se publica como **una versión nueva**, conservando el historial.
- Se utiliza la versión vigente para la fecha de inicio solicitada. Programar una
  versión futura no desactiva la anterior antes de tiempo.
- Las reservas se validan al solicitar y otra vez al confirmar. Si una solicitud
  pendiente deja de cumplir las reglas, el administrador recibe una explicación.
- Una reserva ya confirmada conserva en su auditoría la versión aprobada. El préstamo
  conserva esa misma información; un cambio posterior no modifica sus condiciones.
- Las reservas antiguas sin versión registrada se validan al entregar el bien.

No se borra el historial. Si no hay una política vigente, se muestra un mensaje
para que el administrador publique una; no se inventa una regla en silencio.

## Uso de cada módulo

### Usuarios e inventario

Un administrador registra personas y cuentas. Nombres, apellidos, documento y correo
son obligatorios. La fecha de fin de una persona es opcional; si se completa, debe
ser posterior a la fecha de inicio. El inventario se registra en este orden:

**Tipo → categoría → bien con su ficha → unidad física.**

### Reservas

1. El solicitante elige unidad, inicio, final y uso previsto.
2. El sistema comprueba las reglas y crea una solicitud pendiente.
3. Un administrador confirma o rechaza.
4. Al confirmar se crea también el registro de reserva y se guarda la política usada.

### Préstamos

1. Un administrador elige una reserva confirmada cuyo horario esté vigente.
2. Registra vencimiento, modalidad, condición y accesorios entregados.
3. El sistema registra la hora real de entrega, marca la unidad como prestada y
   la reserva como atendida. También guarda la aprobación y el acta de entrega.
4. Al devolver, el administrador registra condición, accesorios recibidos y destino:
   disponible, mantenimiento o baja.
5. El sistema cierra el préstamo, registra la devolución y actualiza la unidad.

Cada solicitante ve solamente sus préstamos; el administrador ve todos. Un préstamo
fuera de plazo aparece como **vencido**, pero no genera multas automáticas. La hora
de devolución no puede ser futura ni anterior a la entrega. No se permite devolver dos veces.

### Vinculación académica

Solo los administradores registran y consultan estos datos:

- **Períodos:** nombre del semestre y fechas de inicio y final.
- **Información académica:** estudiante, situación, período, promedio y créditos.
- **Matrículas:** estudiante y período. No se duplica la misma matrícula.

Se registran manualmente; no hay conexión automática con sistemas de la universidad.
La matrícula y la información académica son registros separados. No se supone una
cuarta matrícula ni se aplican bloqueos académicos que no hayan sido acordados.
Estas siete políticas no exigen un promedio o matrícula determinados para reservar.

## Qué no está incluido

No se aplican multas, garantías, sanciones, renovaciones ni prórrogas en esta versión.
Que existan sus tablas en PostgreSQL no significa que se hayan habilitado sus procesos.

## Si algo falla

- **Datos inválidos:** se señala el campo o la regla que debe corregirse.
- **Sin conexión:** comprobar que Uvicorn esté funcionando y abrir la interfaz desde
  `http://127.0.0.1:8000/`, no desde un archivo o servidor de frontend independiente.
- El indicador de conexión consulta el estado real de la API.
- Un error no autoriza a recrear la base. No es necesario borrar tablas para usar estos módulos.

## Para quien mantiene el código

Los módulos de negocio están en `app/application/politicas.py`, `prestamos.py` y
`academico.py`. Comparten errores, fechas UTC y auditoría en `comun.py`.
Las rutas nuevas están en `app/api/modulos.py`; el frontend utiliza JavaScript nativo.

Se reutilizan las 45 tablas existentes, sin migraciones ni cambios en los SQL originales
o en `app/conexion_python_base_datos.py`. Las políticas y reglas se escriben juntas;
la versión aplicada queda registrada en la auditoría y en el préstamo.

La tabla de aprobación resume fechas por días con final exclusivo para cumplir su
restricción de fechas. Las horas exactas y los límites efectivos siempre se guardan
y comprueban en la reserva y en el préstamo, sin ampliar el plazo concedido.
