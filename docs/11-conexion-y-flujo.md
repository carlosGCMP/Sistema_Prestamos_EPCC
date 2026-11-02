# Conexión y flujo del aplicativo

## Dónde empezar a leer

| Archivo | Responsabilidad |
| --- | --- |
| `app/main.py` | Arranque, cierre, comprobaciones de salud y publicación del frontend. |
| `app/infrastructure/database.py` | Espera de PostgreSQL, inicialización y sesiones. |
| `app/infrastructure/schema.py` | Comprobación de tablas existentes, sin modificarlas. |
| `app/conexion_python_base_datos.py` | Motor y fábrica de sesiones originales; no se modifica. |
| `app/infrastructure/models.py` | Definición de las tablas que utiliza actualmente la API. |
| `app/infrastructure/modelos_sql.py` | Resto de las tablas del diseño SQL en español. |
| `app/infrastructure/catalogos.py` | Inicialización idempotente de los estados y el tipo de evento. |
| `app/api/routes.py` | Entradas HTTP y respuestas. |
| `app/core/security.py` | Autenticación y permisos. |
| `app/application/basic_use_cases.py` | Reglas de usuarios, inventario y reservas. |
| `frontend/app.js` | Formularios, botones y peticiones desde el navegador. |

## Al iniciar

```text
uvicorn app.main:app --reload
    → FastAPI inicia su ciclo de vida
    → esperar_base_datos() comprueba que PostgreSQL acepta conexiones
    → obtener_motor() carga el motor del archivo protegido
    → inicializar_base_datos() registra los modelos y valida el esquema
    → create_all() crea únicamente las tablas faltantes
    → cargar_catalogos() prepara los estados y tipos de evento necesarios
    → la aplicación comienza a atender peticiones
```

La espera dura aproximadamente `DATABASE_WAIT_SECONDS` (30 segundos por defecto),
con intentos de conexión breves. Si no se consigue conectar, el arranque termina
con un mensaje que indica revisar `.env` y ejecutar `docker compose up -d db`.
No se imprimen contraseñas desde el adaptador.

La conexión protegida ejecuta `SELECT version()` al importarse. Por eso solo se
carga **después de esperar a PostgreSQL**. Importar modelos o la aplicación por sí
solo no abre conexiones. `Base` es el registro de modelos ORM, no otro motor ni
otra fábrica de conexiones.

No se ejecuta Alembic ni se leen o corrigen automáticamente los archivos SQL.
Los SQL originales y el historial de migraciones se conservan intactos.

### Qué significa «crear tablas automáticamente»

- Una base vacía recibe las tablas de **los modelos actuales de la API**.
- Una tabla existente no se borra, recrea ni actualiza.
- Antes de crear tablas se comprueban columnas, tipos, nulabilidad, claves
  primarias y valores requeridos por los enums de las tablas existentes.
- Si esa comprobación falla, el arranque se detiene indicando las diferencias.
- En PostgreSQL se usa una transacción y un bloqueo de inicialización para evitar
  que dos procesos creen simultáneamente las mismas tablas.

Esta comprobación no sustituye una auditoría completa de índices, claves foráneas
o reglas del negocio. Los modelos representan el diseño español corregido de
`base de datos/`; los ajustes se explican en [esquema en español](12-esquema-espanol.md).
El arranque no convierte UUID a BIGINT ni renombra tablas antiguas: rechaza el
esquema anterior para no mezclar versiones.

Si necesitas otra estructura, configura una base nueva y vacía o revisa la
existente con su respaldo. **No ejecutes `docker compose down -v` para resolver
una incompatibilidad:** ese comando elimina los datos del volumen.

## Cuando se pulsa un botón

```text
Formulario HTML + JavaScript
    → fetch() envía una petición HTTP
    → FastAPI valida los datos y comprueba los permisos
    → obtener_sesion() abre una sesión compartida por la petición
    → el caso de uso consulta o modifica modelos
    → SQLAlchemy ejecuta las operaciones en PostgreSQL
    → abrir_sesion() confirma los cambios o los revierte si ocurre un error
    → la sesión se cierra antes de enviar la respuesta
    → JavaScript muestra el resultado y actualiza la pantalla
```

El navegador nunca se conecta directamente a PostgreSQL ni recibe `DATABASE_URL`.
Los permisos y las validaciones del servidor son obligatorios aunque el formulario
ya haya validado los datos.

### Cómo usar una sesión

Las rutas usan `Depends(obtener_sesion, scope="function")`. Las dependencias de
seguridad utilizan exactamente la misma función y alcance: así comparten la
transacción y los errores del `commit` se detectan antes de devolver éxito.

Para procesos fuera de HTTP:

```python
from app.infrastructure.database import abrir_sesion, inicializar_base_datos
from app.infrastructure.models import ItemType

inicializar_base_datos()
with abrir_sesion() as sesion:
    sesion.add(ItemType(name="Equipos de laboratorio"))
```

No hace falta llamar a `commit()` o `close()` dentro del bloque. Si una operación
necesita un identificador generado o consultar cambios aún pendientes, debe usar
`sesion.flush()`: la fábrica original tiene `autoflush=False`.

## Configuración local y Docker

| Lugar donde se ejecuta Python | Dirección en `DATABASE_URL` |
| --- | --- |
| Equipo local, Linux o Windows | `localhost:5433` |
| Contenedor de la API en la misma red de Compose | `db:5432` |

`docker compose up -d db` inicia solamente PostgreSQL. La API se inicia con
Uvicorn en el equipo local. No hacen falta Node.js, npm ni compilación del frontend.

`/health` comprueba el proceso HTTP. `/health/ready` comprueba la inicialización y
la conectividad con PostgreSQL; devuelve 503 si la base no está disponible.
Al cerrar FastAPI se liberan las conexiones del motor, sin eliminar tablas ni datos.

## Pruebas

```bash
pytest tests/test_database.py tests/test_health.py
ruff check app
ruff format --check app
mypy app
```

Las pruebas automatizadas de este módulo utilizan SQLite aislado y conexiones
simuladas; no acceden a la base local. El archivo protegido está excluido de los
formateadores y conserva sus anotaciones originales. El código del adaptador sí
se comprueba con Ruff y mypy.
