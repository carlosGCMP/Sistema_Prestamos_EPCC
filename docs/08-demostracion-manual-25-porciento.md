# Paso a paso para realizar la muestra manual del 25 %

Esta guía es para que el estudiante ejecute y explique personalmente el sistema. No hay datos de demostración ni credenciales precargadas. Los registros que se creen quedarán en la base local de desarrollo.

## 1. Iniciar el entorno

Desde la raíz del repositorio:

```bash
docker compose up -d db
source .venv/bin/activate
alembic upgrade head
python -m app.bootstrap_admin
uvicorn app.main:app --reload
```

El bootstrap solicita los datos del administrador institucional autorizado y una contraseña; no hay usuario predeterminado. Abre `http://127.0.0.1:8000/docs` y comprueba `GET /health/ready`, que debe responder `{"status":"ready"}`.

## 2. Preparar la autorización

En Swagger pulsa **Authorize**, introduce el usuario y contraseña del administrador creado y autoriza. Las rutas de escritura administrativa requieren el permiso explícito `ADMIN_INVENTARIO`; pertenecer a `PERSONAL_ADMINISTRATIVO` no lo concede automáticamente.

Registra al solicitante de prueba con `POST /people`. Usa datos ficticios, correo bajo `example.test`, `role: ESTUDIANTE`, `username` y `password`, además de `student_code`, `program` y `semester`. Conserva el `id` devuelto. Cierra la autorización administrativa y vuelve a autorizarte con la cuenta de estudiante cuando corresponda; para retornar a las operaciones administrativas, vuelve a autorizar como administrador.

## 3. Crear inventario

Como administrador, ejecuta las rutas en este orden y copia los identificadores de las respuestas:

1. `POST /inventory/categories`: crea una categoría de prueba.
2. `POST /inventory/types`: crea un tipo prestable y usa el `category_id` anterior.
3. `POST /inventory/items`: crea la ficha del bien con el `item_type_id`.
4. `POST /inventory/units`: crea una unidad con el `item_card_id`, ubicación, custodia, condición y un `inventory_code` único y claramente temporal.
5. `GET /inventory/units`: verifica que la unidad figure como `DISPONIBLE`.

No uses códigos patrimoniales ni datos personales reales para la exposición.

## 4. Crear una política de prueba

Como administrador, ejecuta `POST /policies` con valores explícitos. Para probar sin reglas institucionales inventadas, puedes usar este conjunto temporal:

- `role`: `ESTUDIANTE`.
- `max_units`: `1`.
- `max_duration`: `1` y `duration_unit`: `DIAS`.
- `allowed_modes`: `[` `"RETIRO"` `]`.
- `allows_renewal`: `true`, `max_renewals`: `1`.
- `requires_academic_eligibility`: `false`.
- `valid_from`: timestamp ISO 8601 actual o anterior, siempre con zona horaria.
- `item_type_id`: omítelo para política general por rol o usa el tipo creado para hacerla específica.

Aclara que estos valores permiten probar el mecanismo y no son reglas aprobadas por la institución.

## 5. Mostrar el flujo de reserva

Autoriza Swagger con la cuenta del estudiante y ejecuta `POST /reservations` con el `unit_id`, un intervalo futuro ISO 8601 con zona horaria (`starts_at`, `ends_at`) y un propósito ficticio. Guarda el `id` de reserva.

Vuelve a autorizarte como administrador y ejecuta `POST /reservations/{reservation_id}/decision` con `{"confirm": true}`. Después vuelve a la cuenta de estudiante y cancela con `POST /reservations/{reservation_id}/cancel`. Esta cancelación libera la unidad para demostrar la entrega inmediatamente, sin esperar al inicio del intervalo futuro.

Explica la regla `[inicio, fin)`: si una reserva termina justo cuando comienza otra, no se superponen. La confirmación vuelve a comprobar disponibilidad y cupo.

## 6. Mostrar entrega, renovación y devolución

Como administrador:

1. `POST /loans`: usa los `applicant_id` y `unit_id` copiados, la modalidad permitida, condición y accesorios entregados; define `due_at` aproximadamente dos horas después del momento actual.
2. Guarda el `id` del préstamo y el `due_at` de la respuesta.
3. `POST /loans/{loan_id}/renewals`: establece `new_due_at` posterior al vencimiento previo y dentro del límite de política. Debe autorizarse antes de que venza el plazo original.
4. `POST /loans/{loan_id}/return`: registra condición y accesorios recibidos. Para una devolución apta, usa `disposition: DISPONIBLE`; si hay daños o faltantes, no declares apto el bien.
5. `GET /loans`: verifica `state: DEVUELTO`.
6. `GET /audit`: muestra eventos de entrega, renovación y devolución.
7. `GET /inventory/units`: verifica que la unidad retornó a `DISPONIBLE`.

## 7. Qué explicar durante la exposición

- La política se valida en el servidor y sus condiciones se guardan como instantánea en el préstamo.
- La transacción vuelve a comprobar disponibilidad y cupo bloqueando la unidad y al solicitante; además, el esquema impide dos préstamos abiertos simultáneos para una unidad.
- El vencimiento no libera el bien: queda comprometido hasta la devolución o el cierre por pérdida.
- La auditoría conserva quién realizó cada operación y sobre qué entidad.
- Swagger/OpenAPI permite ejecutar y consultar operaciones; todavía no hay una interfaz web propia.

## 8. Cierre de la muestra

Detén Uvicorn con `Ctrl+C`. Para detener PostgreSQL preservando lo registrado, usa `docker compose down`; no añadas `-v`. Para repetir la muestra, usa otros correos, documentos y códigos únicos, pues los registros anteriores permanecen en la base local.
