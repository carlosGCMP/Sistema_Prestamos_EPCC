# Esquema de datos en español

La base sigue llamándose `epcc_prestamos`. Sus tablas y columnas están en español,
con identificadores `BIGINT`. Se incluyen las **43 tablas de los SQL originales**
y las dos entidades que faltaban para resolver sus referencias: `bien` y `prestamo`.

Los archivos `base de datos/**/*.sql` y `app/conexion_python_base_datos.py` no se
modifican. La definición ejecutable está en `app/infrastructure/models.py` y
`app/infrastructure/modelos_sql.py`. El arranque crea las tablas y los catálogos
desde esos modelos; no ejecuta Alembic ni interpreta SQL defectuoso.

## Relaciones principales

```text
persona ── cuenta ── administrador
   │          │
   └── solicitante
          ├── solicitante_estudiante ── informacion_estudiante
          │             └── matricula_realizada ── semestre_academico
          ├── solicitante_docente
          └── solicitante_personal_administrativo

tipo_de_bien ── categoria_del_bien ── bien ── ficha_de_bien ── unidad_fisica
                       │                       │                  │
                       └── caracteristica_del_bien               └── ubicacion_del_bien
                                               │
                                          solicitante

solicitante ── solicitud_de_reserva ── registro_de_reserva
                    │                       │
              unidad_fisica        prestamo_aprobado_de_reserva
                                            │
                                         prestamo
                         ┌──────────────────┼─────────────────────┐
                entrega_del_prestamo  devolucion_del_prestamo  ampliacion_devolucion_prestamo
                                            │
                            registro_bienes_fisicos_prestamo ── unidad_fisica

prestamo ── garantia / sancion
solicitante ── incidencia ── resolucion_de_incidencia
cuenta ── registro_auditoria ── historial_de_cambios
```

Cada línea corresponde a relaciones del modelo, no a una autorización de acceso.
Los tipos y estados de garantía, incidencia y sanción tienen tablas de catálogo
propias, conectadas mediante claves foráneas.

## Ajustes necesarios respecto de los originales

| Situación original | Decisión en los modelos |
| --- | --- |
| `solicitante` duplicaba cuenta y no tenía `id_solicitante`. | Crear su identificador y relaciones únicas con persona y cuenta. Las credenciales están solamente en `cuenta`. |
| Los perfiles generaban identificadores independientes con el mismo nombre. | Compartir la clave del solicitante mediante una FK; conservar también su relación con persona. |
| `bien` y `prestamo` eran referenciados pero no estaban definidos. | Añadir ambas entidades y conectar todas sus referencias. |
| Categorías dependían de tipos, a diferencia de la interfaz antigua. | Cambiar el flujo a **tipo → categoría → bien/ficha → unidad**. |
| No había vínculo entre solicitud y reserva registrada. | Añadir `registro_de_reserva.id_solicitud`, único. Confirmar una solicitud crea su registro; cancelarla actualiza ambos. |
| Las tablas de estado de reserva y préstamo no estaban conectadas. | Referenciar sus nombres únicos desde los estados operativos; precargar los valores. |
| Varias sentencias tenían errores de sintaxis. | Declarar estructuras válidas en SQLAlchemy, sin editar los SQL. |
| El préstamo actual necesitaba datos operativos adicionales. | Conservar fechas con zona horaria, condiciones, accesorios y política aplicada, con columnas en español. |
| La auditoría necesitaba asociarse a cuentas, no a personas. | Registrar `id_cuenta`, tipo de evento e historial en la misma transacción. Permitir actor nulo para procesos automáticos. |
| El historial técnico usaba tablas en inglés y UUID. | Recrear expresamente la base de desarrollo, previa autorización y respaldo; no convertir automáticamente datos antiguos. |

Se conserva la unicidad de `unidad_fisica.id_ficha`: cada ficha identifica una sola
unidad. Para registrar otro ejemplar, se crea otra ficha. Las versiones de política
y campos operativos adicionales permiten conservar el contexto del aplicativo;
no implican que todos esos módulos estén expuestos por HTTP.

## Contrato de la aplicación

- Los nombres físicos en PostgreSQL son españoles. Se conservan nombres de
  atributos Python y rutas HTTP históricos para no renombrar toda la aplicación.
- Los identificadores son enteros en Python y cadenas decimales en JSON, porque
  JavaScript no representa con exactitud todo el rango de `BIGINT`.
- Los formularios envían nombres y apellidos por separado. El nombre completo es
  una presentación calculada, no una columna duplicada.
- `administrador` es una atribución de una cuenta de docente o personal
  administrativo; no sustituye su rol personal. Los estudiantes no pueden recibirla.
- Registrar una ficha crea también su `bien` y los nombres de sus características.
- Registrar una unidad crea su primera entrada en `ubicacion_del_bien`.
- La API y sus formularios incluyen usuarios, inventario, reservas, políticas,
  préstamos y vinculación académica manual. Los módulos nuevos reutilizan las
  tablas actuales sin añadir columnas ni migraciones.
- Publicar una política guarda `politicas_del_prestamo`, `reglas_del_prestamo` y
  `version_de_la_politica` en la misma transacción. Confirmar conserva la versión
  aprobada en auditoría; entregar la copia también en el préstamo.
- Entregar registra aprobación, préstamo, acta de entrega y bienes físicos, y marca
  la reserva como atendida y la unidad como prestada. Devolver registra el acta,
  cierra el préstamo y actualiza la unidad.
- Los períodos, información académica y matrículas se registran manualmente; no
  habilitan conexión institucional ni bloqueos académicos automáticos.
- Garantías, incidencias, sanciones y prórrogas siguen fuera del alcance operativo.
  Las siete reglas se explican en [políticas y guía de uso](13-politicas-y-guia-de-uso.md).

## Verlo en pgAdmin 4

1. Cerrar las pestañas del diagrama anterior.
2. En `epcc_prestamos → Schemas → public`, pulsar **Refresh**.
3. Desplegar `Tables`: deben aparecer 45 tablas, sin `accounts`, `loans` ni `alembic_version`.
4. Clic derecho en `public` → **ERD For Schema**.
5. Utilizar **Auto align** y **Zoom to fit**.

Para comprobar las relaciones desde Query Tool:

```sql
SELECT conrelid::regclass AS tabla,
       pg_get_constraintdef(oid) AS relacion
FROM pg_constraint
WHERE contype = 'f'
  AND connamespace = 'public'::regnamespace
ORDER BY tabla, relacion;
```

## Primera cuenta en una instalación nueva

**No es necesario recrear la base para habilitar estos módulos.** Si ya tienes un
administrador, utiliza esa cuenta. Solo en una instalación nueva, crea uno con el
entorno virtual activo:

```bash
python -m app.bootstrap_admin
```

Después iniciar `uvicorn app.main:app --reload`. No existen claves predeterminadas.
Los respaldos deben conservarse fuera del repositorio: pueden contener datos
personales y hashes de contraseñas.
