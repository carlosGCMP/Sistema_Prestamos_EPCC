// Reportes solo consulta datos: no crea ni modifica registros.
export function crearReportes({ request, isAdmin }) {
  const vista = document.querySelector("#reports-view");
  const boton = document.querySelector("#reports-refresh");
  const fecha = document.querySelector("#reports-date");
  const error = document.querySelector("#reports-error");
  const totales = vista.querySelectorAll("[data-report-total]");
  const grupos = {
    inventario_por_estado: document.querySelector("#reports-inventory"),
    reservas_por_estado: document.querySelector("#reports-reservations"),
    prestamos_por_estado: document.querySelector("#reports-loans"),
  };
  const nombres = {
    DISPONIBLE: "Disponible", PRESTADA: "Prestada", MANTENIMIENTO: "Mantenimiento",
    BAJA: "De baja", PENDIENTE: "Pendiente", CONFIRMADA: "Confirmada",
    RECHAZADA: "Rechazada", CANCELADA: "Cancelada", ATENDIDA: "Atendida",
    VENCIDA: "Vencida", ACTIVO: "Activo", VENCIDO: "Vencido",
    DEVUELTO: "Devuelto", CERRADO_POR_PERDIDA: "Cerrado por pérdida",
  };

  function mostrarEstados(lista, estados) {
    lista.replaceChildren();
    for (const [estado, cantidad] of Object.entries(estados)) {
      const fila = document.createElement("li");
      const nombre = document.createElement("span");
      const numero = document.createElement("strong");
      nombre.className = "reports-state";
      nombre.dataset.estado = estado;
      nombre.textContent = nombres[estado] || estado;
      numero.textContent = cantidad;
      fila.append(nombre, numero);
      lista.append(fila);
    }
    if (!lista.children.length) {
      const mensaje = document.createElement("li");
      mensaje.className = "reports-empty";
      mensaje.textContent = "No hay registros todavía.";
      lista.append(mensaje);
    }
  }

  async function cargar() {
    if (!isAdmin() || boton.disabled) return;
    boton.disabled = true;
    boton.textContent = "Actualizando…";
    vista.setAttribute("aria-busy", "true");
    error.hidden = true;
    try {
      const datos = await request("/reports/summary");
      if (!isAdmin()) return; // La sesión pudo cerrarse durante la consulta.
      totales.forEach((elemento) => {
        elemento.textContent = datos[elemento.dataset.reportTotal];
      });
      for (const [clave, lista] of Object.entries(grupos)) {
        mostrarEstados(lista, datos[clave]);
      }
      fecha.textContent = `Actualizado: ${new Date(datos.generado_en).toLocaleString("es-PE")}`;
    } catch (problema) {
      error.textContent = `No se pudo actualizar el resumen. ${problema.message}`;
      error.hidden = false;
    } finally {
      boton.disabled = false;
      boton.textContent = "Actualizar reportes";
      vista.setAttribute("aria-busy", "false");
    }
  }

  function limpiar() {
    totales.forEach((elemento) => { elemento.textContent = "—"; });
    Object.values(grupos).forEach((lista) => lista.replaceChildren());
    fecha.textContent = "Los datos se consultan al abrir esta sección.";
    error.hidden = true;
    error.textContent = "";
  }

  boton.addEventListener("click", cargar);
  return { cargar, limpiar };
}
