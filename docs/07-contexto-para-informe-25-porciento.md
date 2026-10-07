# Fuente de contexto para redactar el informe del 25 %

Este documento reúne datos verificables del proyecto para proporcionar a otra inteligencia artificial como fuente. No reemplaza el informe académico ni el informe del primer examen. Debe usarse junto con la lectura del código y los documentos enlazados al final.

## Instrucción para la IA redactora

Redacta un informe académico, claro y conciso, sobre el avance de implementación del Sistema de Gestión de Préstamos de Bienes de la EPCC-UNSA, presentado como un avance estimado del 25 % del proyecto. Distingue entre lo implementado y lo pendiente. No inventes requisitos aprobados, métricas, resultados de pruebas, datos institucionales ni tecnologías distintas a las indicadas. Explica que este avance es un backend funcional inicial, no un sistema listo para producción. Describe la arquitectura por capas, el modelo y las reglas de negocio, la instalación, la evidencia de verificación y las limitaciones. Evita portada si no se solicita. Usa los datos de esta fuente y verifica cualquier detalle adicional en los archivos del repositorio.

## Identificación y objetivo

- Proyecto: Sistema de Gestión de Préstamos de Bienes de la Escuela Profesional de Ciencia de la Computación (EPCC), Universidad Nacional de San Agustín.
- Propósito: administrar solicitantes, inventario, políticas, reservas y el ciclo de préstamos con control de acceso y trazabilidad.
- Forma de arquitectura: monolito modular por contextos, organizado en capas; no se implementaron microservicios.
- Estado: primer incremento backend utilizable, comunicado como 25 % de avance planificado. El porcentaje es una medida de alcance del proyecto, no una medición estadística ni una declaración de finalización.

## Tecnologías implementadas

- Python 3.13.
- FastAPI para API HTTP y documentación OpenAPI/Swagger.
- SQLAlchemy 2 para persistencia y modelos relacionales.
- PostgreSQL 16 como motor objetivo; Docker Compose para desarrollo local.
- Alembic para versionar el esquema.
- PyJWT para tokens de acceso; `pwdlib` con Argon2id para hashes de contraseña.
- Pytest para pruebas; Ruff para estilo/lint; mypy para comprobación estática.

## Arquitectura y responsabilidades

1. **Presentación/API** (`app/main.py`, `app/routes.py`, `app/schemas.py`): recibe peticiones, valida entrada/salida, documenta rutas y aplica dependencias de autenticación/autorización.
2. **Aplicación/dominio** (`app/application/use_cases.py`): coordina casos de uso y reglas para políticas, elegibilidad, cupos, reservas, préstamos, renovaciones, devoluciones y auditoría.
3. **Persistencia e infraestructura** (`app/models.py`, `app/database.py`, `migrations/`): modelos SQLAlchemy, sesiones, conexión y migración inicial de PostgreSQL.
4. **Seguridad/configuración** (`app/security.py`, `app/settings.py`): hashing, JWT, roles, invalidez de sesiones y configuración por entorno.

La dependencia normal es API → casos de uso → modelos/sesión de persistencia. El caso de uso agrupa las escrituras de cada petición en una transacción; PostgreSQL permite bloquear filas en operaciones concurrentes.

## Funcionalidad incluida

- Personas con roles de estudiante, docente y personal administrativo; perfiles académicos mínimos y cuenta local opcional.
- Autenticación por usuario/contraseña, contraseña almacenada como hash Argon2id, token Bearer JWT y permisos por rol. Cerrar sesión o desactivar una cuenta invalida tokens anteriores mediante versión de sesión.
- Categorías, tipos de bienes, ficha de bien y unidades físicas. El código patrimonial de la unidad es único.
- Políticas versionadas por rol y tipo de bien, con duración máxima, cupos, modalidades, elegibilidad académica manual y límite de renovaciones.
- Solicitud, confirmación/rechazo y cancelación de reservas.
- Entrega, renovación y devolución de unidades. El préstamo conserva la instantánea de la política aplicada.
- Eventos de auditoría consultables por personal administrativo.
- Endpoints operativos `/health` y `/health/ready`.

## Reglas de negocio representadas

- Los intervalos se interpretan como `[inicio, fin)`: dos intervalos solo se superponen si cada inicio es anterior al fin del otro. Por ello, fin e inicio coincidentes no producen conflicto.
- Se comprueban la disponibilidad de la unidad, elegibilidad del solicitante, modalidad permitida, duración y cupo concurrente al confirmar/entregar/renovar.
- El vencimiento no devuelve automáticamente la unidad al inventario; el compromiso sigue abierto hasta devolución o cierre por pérdida.
- Se serializan comprobaciones de unidad y solicitante con bloqueos de fila en PostgreSQL; existe además un índice único parcial para impedir más de un préstamo abierto por unidad.
- La devolución registra condición, accesorios y destino operativo de la unidad.

## Evidencia ejecutada

- Entorno local: Python 3.13.15, PostgreSQL 16-alpine en Docker.
- `alembic upgrade head`: aplicado correctamente en una base de desarrollo nueva.
- Suite del proyecto: 6 pruebas correctas; se incluyen autenticación, autorización, flujo de préstamo y regla de solapamiento.
- Ruff: “All checks passed”.
- mypy: “Success: no issues found in 12 source files”.
- Demostración HTTP contra PostgreSQL: se registraron datos ficticios, política y reserva; se entregó un préstamo, renovó y devolvió; estado final `DEVUELTO` y 12 eventos de auditoría.
- La interfaz disponible es Swagger/OpenAPI en `/docs`; no se ha implementado todavía un frontend de usuario.

## Instalación y demostración local

Requisitos: Python 3.13+, Docker y Docker Compose.

```bash
cp .env.example .env
docker compose up -d db
python3.13 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
alembic upgrade head
python -m app.bootstrap_admin
uvicorn app.main:app --reload
```

URLs locales: `http://127.0.0.1:8000/docs`, `/health` y `/health/ready`. El bootstrap solicita datos y contraseña de forma interactiva; no hay credenciales administrativas predeterminadas. Para detener la API: `Ctrl+C`. Para detener PostgreSQL preservando el volumen: `docker compose down` (no añadir `-v` si se quieren conservar los datos).

Pruebas de calidad:

```bash
pytest
ruff check .
ruff format --check app migrations tests
mypy
```

## Fuera de alcance y pendientes

- Garantías, incidencias, sanciones, apelaciones y reglas automatizadas de multas/mora.
- Integración real con matrícula, identidad o directorio institucional. La elegibilidad académica se ingresa manualmente y es temporal.
- Frontend para estudiantes y panel administrativo.
- Notificaciones, vencimiento programado, reportes operativos, despliegue, observabilidad, backups y pruebas de carga.
- Validación institucional de roles, responsabilidades, políticas, plazos, cupos y tratamiento de bienes dañados/perdidos.
- Probar concurrencia y funcionamiento operacional en PostgreSQL con una batería de integración sostenida; la comprobación actual de API con PostgreSQL fue una demostración manual.

## Fuentes del repositorio

- `README.md`: puesta en marcha y mapa documental.
- `docs/01-vision-y-alcance.md`: problema, propósito y límites del sistema.
- `docs/02-arquitectura-y-tecnologias.md`: tecnologías y estructura propuesta.
- `docs/03-dominio-y-modulos.md`: conceptos y límites de contexto.
- `docs/04-plan-de-implementacion.md`: hitos y avance.
- `docs/06-incremento-funcional-25-porciento.md`: alcance y estado de este incremento.
- `app/application/use_cases.py`, `app/models.py`, `app/routes.py`: reglas, persistencia y contrato API implementados.
- `tests/`: pruebas automatizadas.
