# Reportes: guía sencilla para la exposición

## Qué muestra

Solo los administradores pueden consultar esta pantalla:

- Seis tarjetas: personas, tipos de bien, categorías, unidades, reservas y préstamos.
- Tres paneles: estados de inventario, reservas y préstamos.
- La fecha y hora de la última consulta correcta.
- Un botón para volver a consultar los datos.

Los números corresponden a toda la base, no solo a una página de resultados.
Cuando un módulo no tiene registros, se muestra un mensaje. Un error de conexión
se indica en pantalla y permite intentar de nuevo; no se presenta como un total de cero.

## Cómo está organizado el código

| Archivo | Qué hace |
| --- | --- |
| `frontend/index.html` | Define los títulos, tarjetas y contenedores de los estados. |
| `frontend/reportes.css` | Da color, espaciado y columnas; adapta la pantalla al celular. |
| `frontend/reportes.js` | Consulta la API y coloca los números y los estados en la pantalla. |
| `app/api/reportes.py` | Expone una sola ruta y comprueba el permiso administrativo. |
| `app/application/reportes.py` | Cuenta los registros y los agrupa por estado. |
| `tests/test_reportes.py` | Comprueba permisos, totales, vencimientos y eliminación del CSV. |

El CSS se carga después de `styles.css` y utiliza clases que comienzan por
`reports-`. Así reutiliza los colores de la plataforma sin rediseñar otros módulos.
No necesita bibliotecas de gráficos, Node.js ni compilación.

## El recorrido de una consulta

```text
Abrir Reportes o pulsar Actualizar
    → JavaScript pide GET /reports/summary
    → FastAPI comprueba que la cuenta es administrativa
    → SQLAlchemy consulta PostgreSQL
    → La API devuelve los totales y los estados
    → JavaScript actualiza las tarjetas y las listas
```

En el servidor hay tres funciones pequeñas:

1. `contar_registros`: utiliza `COUNT` para obtener el total de una tabla.
2. `contar_por_estado`: utiliza `GROUP BY` para contar cada estado.
3. `resumen`: reúne esos resultados y clasifica los préstamos abiertos como
   activos o vencidos según su fecha de vencimiento.

El vencimiento solo se calcula para mostrarlo. **Consultar Reportes no cambia el
estado guardado de un préstamo ni libera su unidad.**

En JavaScript, `cargar` consulta y actualiza la pantalla, `mostrarEstados` crea
las filas de cada lista y `limpiar` retira los datos al cerrar sesión.
El botón se desactiva mientras carga para evitar consultas repetidas.

Por ejemplo, la tarjeta con `data-report-total="unidades"` recibe el valor
`unidades` de la respuesta. El mismo bucle actualiza las seis tarjetas, sin repetir
seis veces el código.

Para explicar el CSS, basta señalar tres partes:

- `.reports-totals`: usa **Grid** para organizar las tarjetas en columnas.
- `.reports-card`: define el fondo, borde, espacio interior y tamaño del número.
- `@media`: reduce las columnas cuando la pantalla es más pequeña.

## Qué se simplificó

Se retiró la importación de catálogo CSV: formulario, vista previa, descarga de
ejemplo, rutas HTTP y lógica de importación. El módulo es ahora de **solo lectura**.
Los tipos y categorías que ya se hubieran importado se conservan. El catálogo
todavía se puede registrar mediante los formularios normales de Inventario.

No hay exportación PDF/Excel, filtros por fechas ni actualización automática.
Los datos se consultan al abrir la sección o pulsar el botón.

## Guion breve

> Esta pantalla resume el estado actual del sistema. Las tarjetas muestran los
> totales y los paneles permiten revisar cómo se distribuyen los registros.
> HTML define la estructura, CSS organiza su presentación, JavaScript solicita
> los datos y Python los consulta en PostgreSQL. Es una consulta administrativa:
> no modifica el inventario ni los préstamos.

Para demostrarlo, entrar como administrador, abrir Reportes, señalar una tarjeta,
comparar sus estados y pulsar Actualizar. Después, entrar como estudiante para
explicar que no dispone de esta función y que el permiso también se verifica en la API.

## Cómo se refleja un nuevo préstamo

1. Un estudiante o docente solicita una reserva.
2. Un administrador la confirma antes de su inicio.
3. Dentro del horario reservado, el administrador registra la entrega en Préstamos.
4. `POST /loans` valida y guarda el préstamo, marca la unidad como prestada y la
   reserva como atendida. La transacción se confirma antes de responder con éxito.
5. Al entrar a Reportes o pulsar Actualizar se hace otra consulta a la base.
   Aumentan el total de préstamos, los préstamos activos y las unidades prestadas;
   disminuyen las unidades disponibles. El total de unidades no cambia.

**No hay actualización automática en segundo plano.** Si la pantalla conserva los
datos de una consulta anterior, hace falta pulsar el botón o volver a abrir Reportes.
La reserva `DEMO-LAP-002` de una demo recién cargada sirve para practicar la entrega
durante ocho horas. Si ese horario ya terminó, hay que preparar otra reserva válida.
