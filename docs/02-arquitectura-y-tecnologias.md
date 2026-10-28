# Arquitectura y tecnologías

## Enfoque

Se adopta un monolito modular: una API y una base PostgreSQL. Las rutas HTTP se limitan a validar y autorizar; casos de uso pequeños coordinan las reglas; la infraestructura persiste mediante SQLAlchemy. No se incorporan microservicios, colas ni frameworks adicionales.

```text
Cliente HTTP ── JSON ── FastAPI
                          ├── Usuarios
                          ├── Catálogo e inventario
                          └── Reservas
                               │
                         Casos de uso
                               │
                       SQLAlchemy 2.x
                               │
                         PostgreSQL
```

## Stack

| Área | Tecnología | Uso |
| --- | --- | --- |
| Lenguaje | Python 3.13 | Implementación con anotaciones de tipos. |
| API | FastAPI | Rutas HTTP y documentación OpenAPI. |
| Validación | Pydantic | Validar datos de entrada y salida en los límites de la API. |
| Persistencia | SQLAlchemy 2.x | Modelos ORM, consultas y transacciones. |
| Base de datos | PostgreSQL 16 | Persistencia relacional e integridad referencial. |
| Migraciones | Alembic | Evolución versionada del esquema. |
| Autenticación | JWT y Argon2 | Sesiones de API y almacenamiento seguro de contraseñas. |
| Calidad | Ruff y mypy | Formato, análisis estático y verificación de tipos. |
| Entorno local | Docker Compose | Servicio reproducible de PostgreSQL. |

No se incorpora frontend en este alcance. FastAPI/OpenAPI sirve para explorar y validar las operaciones mientras se estabiliza el dominio.

## Capas del código

```text
app/api             contratos HTTP, dependencias y autorización
app/application     casos de uso y coordinación transaccional
app/core            configuración y seguridad transversal
app/infrastructure  sesión, modelos ORM y persistencia
```

Las capas internas no deben depender de FastAPI. Las rutas delegan reglas a casos de uso, evitando lógica de negocio duplicada y manteniendo responsabilidades acotadas.

## Decisiones de implementación

- Fechas con zona horaria; persistencia temporal normalizada a UTC.
- Contraseñas almacenadas como hash Argon2, nunca como texto ni incluidas en respuestas.
- Secretos configurados fuera del repositorio.
- Restricciones SQL para invariantes de unicidad y relaciones, además de validaciones de aplicación.
- Al confirmar una reserva, bloquear la unidad y volver a comprobar estado y solapamientos en la misma transacción.
- La auditoría de la operación se confirma junto con el cambio principal.

El ORM y el esquema heredado aún contienen entidades de módulos futuros. No se presentan como funcionalidad activa: las rutas de esta etapa se limitan a usuarios, catálogo/inventario y reservas.
