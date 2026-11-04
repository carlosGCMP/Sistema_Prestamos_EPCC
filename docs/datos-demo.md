# Entrega con datos de demostración

Esta opción permite descargar el ZIP y probar el sistema con datos ficticios.
**No contiene una copia de la base de Javier ni datos reales de la universidad.**

## Antes de comenzar

- Extraer el ZIP completamente y abrir una terminal en la carpeta que contiene
  `pyproject.toml` y `docker-compose.demo.yml`.
- Tener Python **3.13 o superior**, Docker y Docker Compose V2.
- En Windows 11, iniciar Docker Desktop con contenedores Linux.
- Tener Internet para descargar las dependencias y PostgreSQL la primera vez.
- Tener libres los puertos **5434** (base demo) y **8001** (interfaz demo).

La demo utiliza un proyecto Docker y un volumen propios. La instalación normal
continúa usando su Compose original y el puerto 5433. No sobrescribas tu `.env`:
los comandos siguientes configuran la demo solo en la terminal donde se ejecutan.
La demo también funciona si todavía no existe un archivo `.env`.

## Primera ejecución en Linux

Ejecutar los comandos uno por uno desde la raíz del proyecto:

```bash
python3 --version
python3 -m venv .venv
./.venv/bin/python -m pip install -e .
docker compose -f docker-compose.demo.yml up -d db
export APP_ENV=development
export DATABASE_URL="postgresql+psycopg://epcc_demo:epcc_demo@localhost:5434/epcc_prestamos_demo"
./.venv/bin/python -m app.cargar_demo
./.venv/bin/python -m uvicorn app.main:app --reload --port 8001
```

Si ya tienes `.venv` con las dependencias instaladas, no necesitas volver a crearlo.

## Primera ejecución en Windows 11

Abrir PowerShell y ejecutar desde la raíz del proyecto:

```powershell
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
docker compose -f docker-compose.demo.yml up -d db
$env:APP_ENV = "development"
$env:DATABASE_URL = "postgresql+psycopg://epcc_demo:epcc_demo@localhost:5434/epcc_prestamos_demo"
.\.venv\Scripts\python.exe -m app.cargar_demo
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8001
```

No hace falta activar el entorno virtual ni cambiar la política de ejecución de
PowerShell: los comandos usan directamente su intérprete.

**No ejecutes `app.bootstrap_admin` para esta demo**: el cargador ya crea el
administrador. Tampoco ejecutes los SQL originales, migraciones, Node.js o npm.

## Entrar a la plataforma

Esperar el mensaje `Application startup complete` y abrir:

- Interfaz: <http://127.0.0.1:8001/>
- API interactiva: <http://127.0.0.1:8001/docs>
- Comprobación de conexión: <http://127.0.0.1:8001/health/ready>

Credenciales públicas de las cuentas de demostración:

| Usuario | Contraseña | Acceso |
| --- | --- | --- |
| `admin` | `contra123456` | Personal administrativo con atribución administrativa |
| `demo_estudiante1` | `SoloDemo-EPCC-2026!` | Estudiante con un préstamo y una reserva lista para entregar |
| `demo_estudiante2` | `SoloDemo-EPCC-2026!` | Estudiante con una solicitud pendiente y un préstamo devuelto |
| `demo_docente` | `SoloDemo-EPCC-2026!` | Docente con una reserva confirmada futura |

Estas cuentas y las credenciales de PostgreSQL incluidas en el Compose son
**exclusivas para evaluación local**. No las reutilices para cuentas reales ni
publiques esta instalación en Internet. Las contraseñas de las cuentas se guardan
con el mismo hash Argon2 del aplicativo, no como texto plano en la base.

## Qué se carga

- 4 personas con sus cuentas y perfiles.
- 2 tipos de bienes y sus categorías: laptops y proyectores.
- 6 bienes con sus fichas y unidades: `DEMO-LAP-001` a `004` y `DEMO-PRO-001` a `002`.
- 4 políticas iniciales: 3 días corridos para estudiantes y 7 para docentes,
  con un máximo de 2 bienes simultáneos del mismo tipo.
- 5 reservas: una pendiente, dos confirmadas y dos atendidas.
- 2 préstamos: uno activo y otro devuelto, con aprobación, entrega y trazabilidad.
- Un período académico del año de carga, información académica y matrículas de
  los dos estudiantes.

Las fechas se calculan al cargar, no están fijadas a una entrega anterior.
La reserva de `DEMO-LAP-002` y el préstamo activo duran hasta ocho horas después
de la carga. La solicitud pendiente comienza dos horas después; la reserva docente
comienza al día siguiente y dura cinco días.

## Recorrido sugerido para evaluar

1. Entrar como `admin`, con contraseña `contra123456`, y revisar inventario y políticas.
2. Abrir Reservas: confirmar la solicitud de `demo_estudiante2` antes de su inicio.
3. Abrir Préstamos: entregar `DEMO-LAP-002`, cuya reserva ya está en horario vigente.
4. Registrar su devolución y comprobar que la unidad vuelve a estar disponible.
5. Revisar períodos, información académica y matrículas.
6. Cerrar sesión y entrar como estudiante: solo verá sus reservas y préstamos,
   sin acceso a las pantallas administrativas.
7. Entrar como docente y comprobar el límite de siete días.

La confirmación ficticia de las reservas ya iniciadas se prepara únicamente
dentro del cargador. La API normal sigue prohibiendo solicitar o confirmar una
reserva en el pasado. No se cambia el reloj del sistema.

## Protecciones y repetición

- La carga es **opcional**: arrancar Uvicorn nunca crea cuentas demo automáticamente.
- Solo se permite con `APP_ENV=development`.
- Antes de crear tablas, catálogos o políticas se comprueba el destino. Una base
  vacía, o que solo tiene los catálogos iniciales, puede recibir la demo.
- Si existen usuarios, inventario u otros datos previos, se rechaza la carga,
  incluso si un usuario se llama `admin`. No se mezclan datos ni se cambian claves.
- Una marca en auditoría identifica una carga completa. Si se repite sin cambiar
  sus datos, informa que ya está cargada y no escribe nada. Iniciar/cerrar sesión
  no invalida esa marca.
- Si se añadieron o editaron datos después de cargar, puede rechazar una repetición:
  es una protección, no una orden de borrado. **La demo ya existente se puede seguir
  usando normalmente sin volver a ejecutar el cargador.**
- No se actualizan fechas al repetir, no se restablecen contraseñas ni se borran
  préstamos. Para una demostración desde cero, usar otra base vacía y separada.
- Las credenciales `admin` / `contra123456` corresponden a cargas nuevas. Una demo
  de la versión anterior (`demo_admin`) no se renombra ni se actualiza al ejecutar
  el cargador: se rechaza para conservar sus datos. No borres tu base actual.
- En PostgreSQL, los datos y las tablas nuevas se confirman juntos; un fallo revierte
  la carga. No se añaden tablas ni columnas al modelo actual de 45 tablas.

El cargador toma bloqueos para evitar dos cargas simultáneas. Ejecútalo con la API
de la demo detenida. No hay una opción para forzar la carga sobre datos existentes.

## Próximos arranques y cierre

No vuelvas a instalar dependencias ni a cargar los datos. En una terminal nueva:

1. Ejecutar `docker compose -f docker-compose.demo.yml up -d db`.
2. Repetir las dos variables de entorno de tu sistema operativo.
3. Ejecutar el comando de Uvicorn con el Python de `.venv` y `--port 8001`.

Los registros y las fechas se conservan: un préstamo puede aparecer vencido si
se abre la demo otro día. Eso es el comportamiento normal del sistema.

Para detenerla, usar **Ctrl+C** y después:

```bash
docker compose -f docker-compose.demo.yml down
```

No añadir `-v`: eliminaría los datos del volumen demo. Cierra esa terminal al
terminar para no reutilizar por accidente las variables de la demo en la instalación real.

## Crear el ZIP para Classroom

Primero revisar los cambios y guardarlos en un commit, incluyendo estos archivos
nuevos. **`git archive` solo incluye lo guardado en el commit**, no cambios pendientes.

Desde la raíz del repositorio:

```bash
git archive --format=zip --prefix=Sistema_Prestamos_EPCC/ --output=../Sistema_Prestamos_EPCC_entrega.zip HEAD
```

Antes de subirlo, comprobar que incluye `app/cargar_demo.py`,
`app/application/datos_demo.py`, `app/infrastructure/seguridad_demo.py`,
`docker-compose.demo.yml` y esta guía. No debe incluir tu `.env`, `.venv`,
respaldos reales ni datos de los volúmenes Docker. Probar el ZIP extraído en una
instalación independiente siguiendo los pasos de arriba y luego adjuntarlo a la tarea.
