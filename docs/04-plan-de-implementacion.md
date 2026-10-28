# Plan de implementación

## Prioridad del corte básico

| Prioridad | Tarea | Criterio de aceptación |
| --- | --- | --- |
| P0 | Configuración y persistencia | La aplicación se configura por entorno y conecta a PostgreSQL sin secretos versionados. |
| P0 | Usuarios y autorización | Se registra y desactiva una persona; autenticación y permisos respetan roles. |
| P0 | Catálogo e inventario | Se administran categorías, tipos, fichas y unidades con códigos únicos. |
| P0 | Reservas | Se solicita, decide y cancela; no se confirman intervalos solapados para una misma unidad. |
| P1 | Calidad y documentación | Las verificaciones estáticas y las instrucciones de ejecución son reproducibles. |
| P2 | Capacidades futuras | Préstamos, políticas e incidencias se planifican en incrementos posteriores. |

## Principios de trabajo

- Mantener cambios pequeños y vinculados a issues concretos.
- Una responsabilidad por función/clase; dependencias explícitas y casos de uso simples.
- Validar entradas en la API, aplicar reglas en la capa de aplicación y reforzar invariantes en PostgreSQL.
- Crear una rama descriptiva por tarea y commits con propósito explícito.
- Revisar el diff y actualizar documentación cuando cambie el comportamiento.
- No reescribir ni eliminar migraciones aplicadas. Cambios de esquema deben ser aditivos y contar con respaldo/plan de reversión.
- No subir secretos, bases locales ni informes privados.

## Organización de seguimiento

El trabajo se sigue en el milestone [Implementación básica: usuarios, catálogo e inventario, reservas](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/milestone/3) y en el [tablero Kanban](https://github.com/users/carlosGCMP/projects/2). Los issues abiertos definen la siguiente unidad de trabajo; se cierran al completar y verificar su criterio de aceptación.

| Issue | Propósito |
| --- | --- |
| [#6](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/6) | Integración continua y guía de desarrollo básico. |
| [#8](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/8) | Flujo básico de reservas. |
| [#10](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/10) | Documentación del alcance activo. |
| [#14](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/14) | API básica de usuarios, inventario y reservas. |
| [#15](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/15) | Alinear la suite de pruebas con el alcance reducido. |
| [#16](https://github.com/carlosGCMP/Sistema_Prestamos_EPCC/issues/16) | Revisar el esquema heredado y planear su evolución segura. |

Los módulos no activos se conservan fuera del router y no se presentan como implementados. La rama de trabajo para este alcance es `implementacion-basica`.
