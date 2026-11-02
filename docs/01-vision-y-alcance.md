# Visión y alcance

## Problema

La EPCC requiere controlar la consulta del catálogo institucional, la disponibilidad de bienes y las solicitudes de reserva. El sistema debe identificar a las personas usuarias y conservar evidencia de las decisiones administrativas.

## Objetivo

Construir incrementalmente una API sencilla para administrar usuarios, catálogo e inventario, y reservas de unidades físicas.

## Alcance activo

1. Registro de personas y cuentas, autenticación y autorización por rol.
2. Catálogo jerárquico: categorías, tipos de bien, fichas y unidades físicas.
3. Consulta de inventario por código, estado y tipo.
4. Solicitud, decisión administrativa y cancelación de reservas.
5. Auditoría de operaciones principales.

## Fuera del alcance actual

Políticas configurables, validación académica institucional, préstamos/entregas/devoluciones, renovaciones, garantías, incidencias, sanciones, apelaciones, integraciones externas y aplicación móvil nativa. La interfaz web presente es básica y no sustituye una experiencia institucional completa.

## Roles iniciales

| Rol | Responsabilidades |
| --- | --- |
| Estudiante/docente | Consultar catálogo y unidades, solicitar reservas y consultar sus solicitudes. |
| `PERSONAL_ADMINISTRATIVO` | Consultar catálogo y perfil; este perfil no otorga permisos de inventario. |
| `ADMIN_INVENTARIO` | Gestionar personas y catálogo/inventario, además de decidir reservas. |

Los permisos son deliberadamente básicos y podrán desglosarse cuando se definan las atribuciones institucionales.

## Criterios de aceptación

- Las credenciales incorrectas o las cuentas inactivas no permiten autenticarse.
- Las rutas requieren el rol correspondiente.
- Los identificadores de personas, cuentas y unidades tienen restricciones de unicidad.
- Solo unidades activas y prestables pueden ser reservadas.
- Una confirmación revalida la disponibilidad y evita reservas confirmadas solapadas.
- Los intervalos se interpretan como semiabiertos `[inicio, fin)`, por lo que dos reservas contiguas son compatibles.
- Las decisiones críticas y su auditoría se guardan dentro de una transacción.
