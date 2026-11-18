export function crearReportes({ request, showToast, isAdmin, makeCell, refrescar }) {
  let contenidoValidado = null;
  const formulario = document.querySelector('#reports-import-form');
  const archivo = document.querySelector('#reports-file');
  const confirmar = document.querySelector('#reports-confirm');
  const estado = document.querySelector('#reports-import-status');
  const vistaPrevia = document.querySelector('#reports-preview');

  function limpiar() {
    contenidoValidado = null;
    confirmar.disabled = true;
    vistaPrevia.hidden = true;
    document.querySelector('#reports-preview-rows').replaceChildren();
    estado.textContent = '';
  }

  async function cargar() {
    if (!isAdmin()) return;
    const datos = await request('/reports/summary');
    const totales = document.querySelector('#reports-totals');
    totales.replaceChildren();
    for (const [clave, etiqueta] of Object.entries({ personas: 'Personas registradas', tipos: 'Tipos de bien', categorias: 'Categorías', unidades: 'Unidades físicas', reservas: 'Reservas', prestamos: 'Préstamos' })) {
      const termino = document.createElement('dt');
      const valor = document.createElement('dd');
      termino.textContent = etiqueta;
      valor.textContent = String(datos[clave]);
      totales.append(termino, valor);
    }
    const cuerpo = document.querySelector('#reports-states');
    cuerpo.replaceChildren();
    for (const [clave, modulo] of Object.entries({ inventario_por_estado: 'Inventario', reservas_por_estado: 'Reservas', prestamos_por_estado: 'Préstamos' })) {
      for (const [nombre, cantidad] of Object.entries(datos[clave])) {
        const fila = document.createElement('tr');
        [modulo, nombre, cantidad].forEach((valor) => makeCell(fila, valor));
        cuerpo.append(fila);
      }
    }
    document.querySelector('#reports-date').textContent = `Actualizado: ${new Date(datos.generado_en).toLocaleString('es-PE')}`;
  }

  archivo.addEventListener('change', limpiar);
  formulario.addEventListener('submit', async (evento) => {
    evento.preventDefault();
    limpiar();
    const boton = formulario.querySelector('button[type="submit"]');
    boton.disabled = true;
    try {
      const seleccionado = archivo.files[0];
      if (!seleccionado || seleccionado.size > 100000) throw new Error('Selecciona un CSV de máximo 100 KB.');
      const contenido = new TextDecoder('utf-8', { fatal: true }).decode(await seleccionado.arrayBuffer());
      const filas = await request('/reports/catalog/preview', { method: 'POST', body: JSON.stringify({ contenido }) });
      const cuerpo = document.querySelector('#reports-preview-rows');
      filas.forEach((registro) => {
        const fila = document.createElement('tr');
        [registro.tipo, registro.categoria, registro.descripcion].forEach((valor) => makeCell(fila, valor));
        cuerpo.append(fila);
      });
      contenidoValidado = contenido;
      vistaPrevia.hidden = false;
      confirmar.disabled = false;
      estado.textContent = `${filas.length} categorías válidas. Revisa los datos y confirma para guardarlos.`;
    } catch (error) { estado.textContent = error.message; }
    finally { boton.disabled = false; }
  });

  confirmar.addEventListener('click', async () => {
    if (!contenidoValidado) return;
    confirmar.disabled = true;
    try {
      const resultado = await request('/reports/catalog/import', { method: 'POST', body: JSON.stringify({ contenido: contenidoValidado }) });
      limpiar();
      formulario.reset();
      estado.textContent = `Importación guardada: ${resultado.tipos_creados} tipos nuevos y ${resultado.categorias_creadas} categorías.`;
      try { await refrescar(); await cargar(); }
      catch { showToast('Importación guardada. Actualiza la pantalla para consultar los datos.', true); }
    } catch (error) {
      estado.textContent = error.message;
      confirmar.disabled = false;
    }
  });

  document.querySelector('#reports-refresh').addEventListener('click', () => cargar().catch((error) => showToast(error.message, true)));
  document.querySelector('#reports-template').addEventListener('click', () => {
    const enlace = document.createElement('a');
    const url = URL.createObjectURL(new Blob(['tipo,categoria,descripcion\nEquipo audiovisual,Proyectores,Equipos para exposición\n'], { type: 'text/csv;charset=utf-8' }));
    enlace.href = url;
    enlace.download = 'ejemplo_catalogo.csv';
    enlace.click();
    URL.revokeObjectURL(url);
  });
  return { cargar, limpiar() { limpiar(); formulario.reset(); } };
}
