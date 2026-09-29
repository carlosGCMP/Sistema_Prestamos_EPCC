# Sistema de gestión de préstamos de bienes de la EPCC
{{COVER_SUBTITLE}}
Informe para el primer examen
Universidad Nacional de San Agustín
Escuela Profesional de Ciencia de la Computación
{{COVER_META}}
Estudiante: completar
Docente: completar
Curso: completar
Arequipa, 29 de septiembre de 2026
{{PAGEBREAK}}

## Resumen ejecutivo

Este informe presenta la primera versión del análisis del Sistema de Gestión de Préstamos de Bienes de la EPCC. Atiende los tres productos solicitados para el primer examen: requisitos del sistema, modelo de dominio y extensión del modelo hacia una arquitectura en capas mediante diagramas UML [F1].

El diseño considera personas y cuentas, inventario físico, reservas, préstamos y renovaciones. El esquema PostgreSQL suministrado cubre parcialmente identidad y acceso, y desarrolla inventario, reservas y préstamos; todavía no incorpora políticas de préstamo, vinculación académica, garantías, incidencias, sanciones ni auditoría [F3]. La arquitectura propuesta conserva los contextos del modelo dentro de una aplicación Python modular con API FastAPI y persistencia PostgreSQL.

El repositorio contiene documentación inicial, un endpoint de salud y la configuración local de PostgreSQL. El esquema SQL y los diagramas de dominio aún no se han integrado en la aplicación; por tanto, este informe describe un diseño en elaboración y no una solución funcional completa [F4].

## Introducción y alcance

El sistema busca controlar la identificación de bienes prestables y el ciclo de reserva, entrega, renovación y devolución. Cada operación debe relacionar a las personas involucradas con una unidad física concreta, registrar sus fechas y conservar el estado del bien.

Para el examen se presenta el diseño general. El alcance examinado se basa en el modelo de dominio entregado y en el SQL adjunto. Los requisitos derivados de ese material se distinguen de las recomendaciones que todavía necesitan validación con los responsables de la EPCC.

## Fuentes y estado del proyecto

La pauta del examen pide requisitos, el modelo de dominio y una arquitectura en capas con diagramas UML de paquetes y clases [F1]. El diagrama de dominio compartido organiza el problema en contextos delimitados. El archivo SQL concreta cuatro de ellos: BC-01 Identidad y Acceso de forma parcial, BC-03 Catálogo e Inventario, BC-05 Reservas y BC-06 Préstamos [F2, F3].

La propuesta tecnológica existente selecciona Python, FastAPI, SQLAlchemy, Alembic y PostgreSQL para una primera implementación como monolito modular. El repositorio también incluye un endpoint `/health` y un servicio PostgreSQL en Docker Compose. A la fecha de este informe no hay modelos de persistencia, migraciones, autenticación, operaciones de inventario, reservas o préstamos integradas en la aplicación [F4].

## Requisitos del sistema

Los requisitos marcados como derivados se observan directamente en las tablas, restricciones o estados del SQL. Los marcados como por validar completan el flujo del producto o vienen de la documentación funcional, pero necesitan aprobación de la EPCC antes de considerarse definitivos.

### Requisitos funcionales

| ID | Requisito | Origen y estado |
| --- | --- | --- |
| RF-01 | Registrar personas con CUI, documento, nombre, correo institucional, rol base, vinculación y estado. | SQL; derivado |
| RF-02 | Asociar a una persona una cuenta con nombre de usuario, hash de contraseña, estado y último acceso. | SQL; derivado |
| RF-03 | Mantener categorías y tipos de bien, indicando si cada tipo se puede prestar. | SQL; derivado |
| RF-04 | Mantener fichas de bienes y unidades físicas con código de inventario, ubicación, condición, accesorios y estado. | SQL; derivado |
| RF-05 | Solicitar una reserva para una unidad durante un intervalo, registrando solicitante y uso previsto. | SQL; derivado |
| RF-06 | Cambiar el estado de una reserva y guardar el motivo cuando se rechace. | SQL; el flujo de aprobación requiere validar reglas |
| RF-07 | Registrar un préstamo con solicitante, administrador, unidad, plazo y reserva de origen opcional. | SQL; derivado |
| RF-08 | Registrar la entrega y la devolución, incluidos fecha, condición, accesorios, responsable y estado de destino de la unidad. | SQL; derivado |
| RF-09 | Registrar renovaciones con secuencia, vencimiento anterior y nuevo, administrador y fecha de autorización. | SQL; derivado |
| RF-10 | Consultar personas, disponibilidad, reservas y préstamos por identificador, estado y fechas. | Propuesto; validar filtros y permisos |
| RF-11 | Consultar el historial de cambios de las operaciones críticas. | Documentación del proyecto; falta definir el modelo de auditoría |

### Requisitos no funcionales

| ID | Requisito | Base de diseño |
| --- | --- | --- |
| RNF-01 | La base de datos debe conservar identificadores únicos y relaciones válidas entre persona, cuenta, bien, reserva, préstamo y renovación. | UUID, claves únicas y claves foráneas en SQL |
| RNF-02 | El sistema debe rechazar intervalos de reserva y plazos de préstamo inválidos. | Restricciones `CHECK` del esquema |
| RNF-03 | Las operaciones de entrega y devolución deben mantener la disponibilidad correcta cuando varias solicitudes coincidan. | Recomendación pendiente de implementar con transacciones y control de concurrencia |
| RNF-04 | Las contraseñas deben almacenarse como hashes; la API debe limitar cada operación a usuarios autorizados. | El SQL guarda un hash; algoritmo y autorización están pendientes |
| RNF-05 | Las fechas de operación deben incluir zona horaria y conservar una referencia temporal coherente. | Uso de `TIMESTAMPTZ` en el esquema |
| RNF-06 | El dominio debe poder probarse sin depender de FastAPI ni de SQLAlchemy. | Decisión de arquitectura propuesta |
| RNF-07 | Las modificaciones del esquema deben ser reproducibles mediante migraciones versionadas. | Propuesta de Alembic |
| RNF-08 | La API debe publicar sus operaciones y estructuras de datos mediante OpenAPI. | FastAPI propuesto |

Los materiales no fijan metas medibles de rendimiento, disponibilidad, retención de datos o accesibilidad. Esos valores deben levantarse con los usuarios y responsables institucionales antes de aprobar requisitos no funcionales definitivos.

## Modelo de dominio

El modelo conserva los conceptos y asociaciones representados por el SQL. `Persona` identifica al solicitante o al personal que opera el sistema. `Cuenta` contiene las credenciales de acceso. El inventario se organiza como categoría, tipo, ficha y unidad física. Una reserva se solicita para una unidad durante un intervalo. Un préstamo registra la entrega y devolución de esa unidad, y puede provenir de una reserva. Las renovaciones forman un historial ordenado del préstamo [F2, F3].

{{FIGURE:domain}}

La notación de multiplicidad expresa las relaciones definidas por las claves foráneas del esquema. Una persona puede tener cero o una cuenta; cada cuenta corresponde a una persona. Una reserva referencia a una persona y a una unidad. Un préstamo registra por separado solicitante, administrador y unidad, además de una reserva de origen opcional. Cada renovación pertenece a un préstamo y la secuencia no se repite dentro de ese préstamo [F3].

### Reglas e invariantes del negocio

- El código de inventario identifica una sola unidad física.
- El inicio de una reserva debe preceder a su fin. El inicio del plazo de un préstamo debe preceder a su vencimiento.
- La secuencia de renovaciones empieza en uno, no se repite por préstamo y el nuevo vencimiento es posterior al anterior.
- La entrega y la devolución deben registrar quién fue responsable y la condición reportada del bien.
- Una unidad no debe tener más de un préstamo activo o vencido a la vez. El índice parcial actual facilita la consulta, pero no impone unicidad; la base necesita una restricción o índice único parcial si se confirma esta regla.

Las tres primeras reglas aparecen directamente en restricciones o claves del SQL. Las dos últimas se desprenden del flujo operativo propuesto y requieren modelarse y probarse en la aplicación. El modelo conceptual completo también incluye políticas, vinculación académica, garantías, incidencias, sanciones y auditoría; esos contextos no forman parte del SQL recibido [F2, F3].

## Arquitectura en capas

Se propone un monolito modular desplegado como una aplicación. Los contextos delimitados se mantienen como paquetes internos con responsabilidades claras. La arquitectura separa el acceso HTTP, los casos de uso, las reglas del dominio y los adaptadores técnicos. Las dependencias del código apuntan hacia el dominio; la infraestructura implementa las interfaces que necesita la aplicación.

{{FIGURE:architecture}}

La capa de presentación traduce solicitudes HTTP a comandos o consultas y convierte respuestas en esquemas de API. La capa de aplicación coordina casos de uso como registrar una unidad, crear una reserva, entregar un préstamo o recibir una devolución. El dominio contiene entidades, reglas y contratos de repositorio. La infraestructura implementa persistencia PostgreSQL, seguridad, configuración y migraciones.

### Flujo de registro de préstamo

El personal inicia el caso de uso de entrega desde la API. La aplicación valida al solicitante, comprueba que la unidad se pueda prestar y confirma que no exista otra operación incompatible. Después crea el préstamo y registra la evidencia de entrega dentro de una transacción. El repositorio guarda los cambios en PostgreSQL y el sistema devuelve el préstamo creado. La validación de políticas y condición académica se añadirá cuando esos contextos estén disponibles.

La arquitectura no propone llamadas HTTP entre módulos internos ni microservicios separados en esta etapa. Las transacciones de inventario y préstamo necesitan mantener consistencia, y el equipo aún está construyendo la primera versión del producto.

## Tecnologías propuestas

| Componente | Tecnología | Uso en el sistema |
| --- | --- | --- |
| Lenguaje | Python 3.13 o superior | Reglas, casos de uso y API |
| API | FastAPI y Pydantic | Rutas HTTP, validación y OpenAPI |
| Base de datos | PostgreSQL | Persistencia relacional y restricciones |
| Acceso a datos | SQLAlchemy 2 y Psycopg 3 | Mapeo y transacciones |
| Migraciones | Alembic | Evolución versionada del esquema |
| Autenticación | Hash Argon2id y tokens de acceso | Credenciales y sesiones de API; diseño por concretar |
| Pruebas y calidad | pytest, Ruff y mypy | Pruebas, estilo y tipado |
| Entorno local | Docker Compose | Ejecución reproducible de PostgreSQL |

Estas tecnologías siguen la propuesta documentada en el repositorio [F4]. La interfaz web no está definida en este informe; debe elegirse cuando los flujos de API e inventario estén estabilizados.

## Revisión del esquema SQL

El esquema es una base concreta para BC-01, BC-03, BC-05 y BC-06. Incluye claves UUID, unicidad de CUI, correo, usuario y código de inventario; restricciones para intervalos; estados de reserva, unidad y préstamo; y datos de entrega, devolución y renovación [F3]. Antes de migrarlo al proyecto conviene cerrar las siguientes decisiones.

{{PAGEBREAK}}

| Hallazgo | Consecuencia | Acción recomendada |
| --- | --- | --- |
| `idx_prestamo_unidad` es un índice parcial no único. | La base permite más de un préstamo activo o vencido sobre la misma unidad. | Si la regla se confirma, reemplazarlo por un índice único parcial o una restricción equivalente. |
| El préstamo inicia como `ACTIVO`, aunque los datos de entrega pueden ser nulos. | Puede existir un préstamo aparentemente activo antes de entregar físicamente el bien. | Definir un estado previo a la entrega o activar el préstamo al confirmar la entrega. |
| Reserva y préstamo se enlazan en ambos sentidos. | Se crean dos referencias para representar el préstamo generado por una reserva. | Elegir una relación autoritativa y conservar la otra solo si hay una necesidad de consulta clara. |
| `unidad_tiempo` está declarado, pero no se usa; no hay tablas de políticas. | El esquema no permite calcular el plazo permitido según perfil o tipo de bien. | Incorporar BC-04 y guardar en el préstamo una copia de las condiciones aplicadas. |
| La persona tiene un `rol_base`; no hay roles administrativos ni permisos separados. | Los permisos operativos no se pueden asignar de forma granular. | Definir autorización por rol y atribuciones administrativas dentro de BC-01. |
| No aparece el contexto de auditoría ni vínculo académico. | No se reconstruyen cambios ni se valida elegibilidad académica con el esquema actual. | Diseñar esos contextos y definir fuente institucional de datos antes de producción. |

## Avance y siguiente etapa

El trabajo existente es una base de documentación y entorno. El repositorio contiene una API mínima de salud, el servicio local de PostgreSQL y la propuesta de tecnologías. El SQL adjunto es un insumo de diseño externo al repositorio; todavía no existe una migración ni una implementación funcional de las tablas [F4].

La siguiente etapa debe integrar la configuración de base de datos y Alembic, después modelar identidad y catálogo, proteger las operaciones de inventario y añadir pruebas. Reservas y préstamos se implementarán cuando la autenticación y la disponibilidad de unidades ya tengan un flujo consistente. Este orden sigue el incremento inicial planificado en el proyecto [F4].

## Conclusiones

El examen presenta un diseño que conecta requisitos, dominio y arquitectura. El esquema ya precisa las entidades principales para registrar personas, bienes, unidades, reservas, préstamos y renovaciones. La arquitectura en capas propuesta permite trasladar esos conceptos a Python manteniendo las reglas separadas de la API y de PostgreSQL.

El siguiente paso técnico es integrar el SQL mediante migraciones y revisar las invariantes de préstamo activo, ciclo de entrega y política aplicada. Las reglas de roles, elegibilidad académica, auditoría y operación deben validarse con la EPCC antes de considerarlas cerradas.

{{PAGEBREAK}}

## Guion breve para la exposición

1. Presentar el problema: controlar qué unidad se presta, a quién, por cuánto tiempo y en qué condición se devuelve.
2. Explicar los requisitos funcionales y las cualidades esperadas de consistencia, seguridad y trazabilidad.
3. Recorrer el modelo: Persona y Cuenta; jerarquía del inventario; Reserva; Préstamo y Renovación.
4. Mostrar cómo la arquitectura separa API, casos de uso, dominio e infraestructura.
5. Cerrar con el avance real y las decisiones pendientes antes de implementar préstamos.

## Fuentes

- [F1] Pauta del primer examen compartida por el usuario. Solicita requisitos, modelo de dominio y arquitectura en capas con diagramas UML de paquetes y clases.
- [F2] Diagrama de clases del modelo de dominio del Sistema de Gestión de Préstamos de Bienes EPCC UNSA compartido previamente en el proyecto.
- [F3] `sistema_gestion_prestamos_bienes_epcc_unsa.sql`, esquema PostgreSQL derivado del modelo de dominio v6/v7; el encabezado declara cobertura parcial de BC-01 y cobertura de BC-03, BC-05 y BC-06.
- [F4] Repositorio Sistema_Prestamos_EPCC, documentación de visión, arquitectura, dominio y plan de implementación; estado revisado al 29 de septiembre de 2026.
