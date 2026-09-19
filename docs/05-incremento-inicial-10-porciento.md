# Incremento inicial: 10 % del proyecto

## Propósito

El primer 10 % no busca cubrir cada contexto del diagrama. Busca establecer una base segura y demostrar el flujo más temprano que habilita valor: un administrador autenticado registra y consulta unidades físicas de inventario, y el sistema conserva esos datos en PostgreSQL mediante migraciones.

Esto reduce el riesgo técnico antes de abordar préstamos: un préstamo no puede existir sin usuarios, roles, bienes ni unidades identificables.

## Alcance comprometido

| Área | Incluido en el 10 % | Aún no incluido |
| --- | --- | --- |
| Plataforma | Configuración, Docker, PostgreSQL, Alembic, CI básico y convenciones. | Despliegue productivo, monitoreo y copias de seguridad. |
| Identidad | Usuario local, contraseña segura, inicio de sesión y rol `ADMIN_INVENTARIO`. | Integración institucional, recuperación de contraseña y todos los perfiles. |
| Inventario | Tipos de bien, ficha de bien y unidades físicas; alta y consulta. | Préstamo, reserva, baja, mantenimiento, QR/código de barras. |
| Auditoría | Registro de creación/modificación de inventario con actor y fecha. | Historial completo de todos los contextos. |
| API | Endpoints autenticados, validación y documentación OpenAPI. | Interfaz web y aplicación móvil. |

## Resultado demostrable

Al cerrar el incremento, se podrá:

1. Crear la base de datos desde cero usando migraciones.
2. Crear un administrador inicial de desarrollo de forma controlada.
3. Iniciar sesión y recibir un token de acceso.
4. Crear un tipo de bien, su ficha y una unidad física con código único.
5. Consultar el catálogo y sus unidades solo con permisos válidos.
6. Ver quién creó o modificó un registro de inventario.

## Orden de ejecución

| Orden | Entregable | Dependencia | Criterio de cierre |
| --- | --- | --- | --- |
| 1 | Configuración y migraciones | Ninguna | `alembic upgrade head` construye un esquema vacío. |
| 2 | Módulo compartido y auditoría base | 1 | UUID, tiempo UTC, errores y actor se reutilizan sin acoplar módulos. |
| 3 | Usuarios, roles y autenticación | 1, 2 | Un usuario autenticado recibe un token; un no autorizado obtiene 401/403. |
| 4 | Modelo de inventario | 1, 2 | La base impide códigos de unidad repetidos y estados inválidos. |
| 5 | API de inventario protegida | 3, 4 | Un administrador puede crear y consultar bienes y unidades. |
| 6 | Pruebas, CI y guía operativa | 1–5 | Pruebas automatizadas pasan y la guía permite ejecutar el entorno limpio. |

## Estructura de trabajo

Cada entregable tendrá una rama corta, una revisión y una solicitud de cambio hacia `main`:

```text
main
 ├── codex/foundation-migrations
 ├── codex/authentication
 └── codex/inventory-catalog
```

Una rama no debe mezclar más de un entregable. Todo cambio debe incluir pruebas pertinentes, migración cuando altere el esquema y actualización de documentación si modifica un contrato API o una decisión arquitectónica.

## Modelo mínimo del incremento

```text
Usuario  ──< UsuarioRol >── Rol
  │
  └──< EventoAuditoria

TipoBien ──< FichaBien ──< UnidadFisica
```

`UnidadFisica.codigo_inventario` será único. La disponibilidad se representará con un estado controlado (`DISPONIBLE`, `NO_DISPONIBLE`, `MANTENIMIENTO`); todavía no se modela un préstamo activo.

## Definition of Done

Un entregable está terminado cuando:

- Las reglas de dominio relevantes tienen pruebas unitarias.
- Los endpoints tienen pruebas de integración, incluyendo autorización cuando aplique.
- Ruff y mypy no reportan errores.
- No se exponen secretos ni datos sensibles en el repositorio, logs o respuestas.
- La migración funciona tanto en una base nueva como al actualizar la base de desarrollo.
- La documentación y OpenAPI representan el comportamiento real.

## Riesgos y decisiones que deben cerrarse antes del hito siguiente

- Acordar quién crea y administra las cuentas iniciales.
- Definir el formato institucional del `codigo_inventario` y estados operativos permitidos.
- Confirmar si una ficha representa un modelo de bien o una adquisición/lote.
- Validar el conjunto real de roles de inventario con la EPCC.

## Seguimiento

El trabajo se reflejará en el hito de GitHub **Incremento inicial (10%)**. Las incidencias del hito representan entregables; los commits y solicitudes de cambio deberán referenciarlas para mantener trazabilidad.
