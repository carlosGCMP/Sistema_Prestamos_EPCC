# Análisis y diseño inicial del sistema de préstamos de bienes EPCC

## Propósito y alcance

Este documento presenta los productos solicitados para el primer examen: requisitos, modelo de dominio y arquitectura en capas. Se elaboró a partir del diagrama conceptual, el esquema PostgreSQL y la documentación del repositorio. Se distingue el dominio completo del subconjunto que actualmente concreta el SQL.

El sistema busca administrar el catálogo de bienes y controlar las reservas, entregas, renovaciones y devoluciones realizadas por la comunidad de la Escuela Profesional de Ciencia de la Computación. El diseño se encuentra en etapa inicial: el repositorio dispone de una API de salud y PostgreSQL local, pero aún no integra persistencia de negocio ni los flujos funcionales.

## 1. Requisitos del sistema

Los requisitos derivados del esquema se identifican como **D**; los que requieren confirmar reglas operativas con la EPCC, como **V**. Esta distinción evita presentar decisiones pendientes como políticas institucionales aprobadas.

### Requisitos funcionales

| ID | Requisito | Estado |
| --- | --- | --- |
| RF-01 | Registrar personas y sus cuentas de acceso, identificadores, estado y rol base. | D |
| RF-02 | Organizar el catálogo en categorías, tipos, fichas y unidades físicas identificables. | D |
| RF-03 | Solicitar y gestionar reservas de bienes para un intervalo, registrando solicitante y uso previsto. | D/V |
| RF-04 | Registrar préstamos, responsables, unidad, plazo y reserva de origen cuando corresponda. | D |
| RF-05 | Registrar evidencia de entrega, devolución y condición del bien. | D |
| RF-06 | Registrar renovaciones autorizadas y su secuencia de vencimientos. | D |
| RF-07 | Consultar disponibilidad, historial y operaciones por persona, bien, estado y fechas. | V |
| RF-08 | Conservar trazabilidad de las operaciones críticas y de sus responsables. | V |

### Requisitos de calidad

- **Integridad:** identificadores únicos, relaciones válidas e intervalos de tiempo consistentes; el SQL ya define varias claves y restricciones.
- **Consistencia concurrente:** impedir la asignación simultánea de una misma unidad; falta implementar transacciones y confirmar una restricción de unicidad para préstamos activos.
- **Seguridad:** almacenar contraseñas como hash y autorizar operaciones por rol; el esquema solo contempla un rol base, por lo que permisos y autenticación están pendientes.
- **Mantenibilidad:** versionar el esquema con migraciones y mantener reglas de negocio independientes de la API y del ORM.
- **Trazabilidad:** registrar actor, fecha y cambios relevantes; el contexto de auditoría del modelo conceptual no está incluido en el SQL actual.

Los materiales disponibles no especifican objetivos medibles de disponibilidad, rendimiento, retención o accesibilidad. Deben acordarse con los usuarios antes de fijar criterios de aceptación.

## 2. Modelo de dominio

El diagrama conceptual recibido organiza el problema en contextos delimitados: identidad y acceso, vinculación académica, catálogo e inventario, políticas, reservas, préstamos, garantías, incidencias, sanciones y auditoría. Estos contextos describen el dominio objetivo; no equivalen a tablas ya implementadas.

La vista de clases presentada a continuación se limita a los conceptos que aparecen en el SQL recibido. `Persona` se relaciona con `Cuenta`; el inventario se estructura como `CategoriaBien`, `TipoBien`, `FichaBien` y `UnidadFisica`. `Reserva` identifica solicitante y unidad. `Prestamo` registra solicitante, administrador, unidad y una reserva de origen opcional. `Renovacion` conserva los cambios de vencimiento asociados al préstamo.

{{FIGURE:domain}}

Las multiplicidades reflejan las claves foráneas del esquema. El diseño conceptual añade reglas aún por validar: elegibilidad académica, política aplicada al préstamo, prioridad de reservas, límite de renovaciones, garantías, sanciones e historial de auditoría. El diagrama debe leerse como un modelo parcial de análisis, no como el modelo completo aprobado.

### Observaciones del análisis del SQL

| Hallazgo | Implicación para el diseño |
| --- | --- |
| El índice de préstamos por unidad no es único. | No evita dos préstamos activos o vencidos para la misma unidad; definir y hacer cumplir la regla en base de datos. |
| Un préstamo se crea como activo aunque la entrega puede estar vacía. | Separar solicitud/autorización de entrega, o activar el préstamo al registrar la entrega. |
| Reserva y préstamo guardan referencias mutuas. | Definir una relación autoritativa y evitar mantener enlaces redundantes sin necesidad. |
| No hay tablas de políticas ni vínculo académico. | No se pueden aplicar límites de préstamo ni comprobar elegibilidad desde el esquema actual. |
| Roles administrativos y auditoría no están desarrollados. | Definir permisos, responsables y eventos antes de operar con datos reales. |

## 3. Arquitectura en capas

Se propone un **monolito modular** en Python. Los contextos se implementan como módulos dentro de una aplicación, sin llamadas HTTP internas ni separación prematura en microservicios. Esta opción mantiene las operaciones de inventario y préstamo dentro de transacciones consistentes y permite evolucionar los módulos con contratos explícitos.

{{FIGURE:architecture}}

La presentación recibe solicitudes HTTP y valida sus esquemas. La aplicación coordina casos de uso —por ejemplo, registrar una unidad, reservar, entregar o devolver—. El dominio contiene entidades, invariantes y contratos. La infraestructura implementa esos contratos mediante PostgreSQL, SQLAlchemy, seguridad y migraciones. Las dependencias de los casos de uso apuntan al dominio; la infraestructura se conecta a través de interfaces.

| Componente | Tecnología propuesta | Responsabilidad |
| --- | --- | --- |
| API y validación | Python, FastAPI, Pydantic | Endpoints, esquemas y OpenAPI |
| Dominio y aplicación | Python tipado | Entidades, reglas y casos de uso |
| Persistencia | PostgreSQL, SQLAlchemy 2, Psycopg 3 | Restricciones, consultas y transacciones |
| Evolución del esquema | Alembic | Migraciones versionadas |
| Calidad | pytest, Ruff, mypy | Pruebas, estilo y tipos |
| Desarrollo local | Docker Compose | Entorno reproducible de PostgreSQL |

La interfaz web queda fuera de este primer alcance; conviene elegirla después de estabilizar los flujos de API. Las tecnologías son una propuesta documentada en el repositorio, no componentes ya implementados.

## Conclusión

El dominio y el SQL ofrecen una base para iniciar identidad, catálogo e inventario, reservas y préstamos. Antes de convertir el esquema en migraciones, deben cerrarse las reglas de préstamo activo, el momento de entrega, las políticas y la relación reserva-préstamo. La siguiente entrega técnica debería integrar SQLAlchemy y Alembic, implementar primero identidad e inventario y probar la disponibilidad transaccional.

**Estado actual:** documentación inicial, API mínima de salud y PostgreSQL local. No están implementados los modelos de persistencia, autenticación ni los casos de uso del negocio.

## Fuentes

1. Pauta del primer examen compartida por el usuario: requisitos, modelo de dominio y arquitectura en capas con diagramas UML.
2. Diagrama conceptual `modelo-de-dominio_blan2 (1).png`, proporcionado para esta revisión.
3. `sistema_gestion_prestamos_bienes_epcc_unsa.sql`, esquema PostgreSQL derivado del modelo de dominio v6/v7.
4. Documentación del repositorio: visión, arquitectura, modelo de dominio y plan de implementación; estado revisado el 29 de septiembre de 2026.
