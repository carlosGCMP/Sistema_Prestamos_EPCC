// Pantallas de políticas, préstamos y datos académicos. Sin bibliotecas externas.
export function crearModulos({ request, showToast, submitJsonForm, fillSelect,
  makeCell, dateLabel, isAdmin, getCatalogo, refrescar }) {
  let politicas = [];
  let reservas = [];
  let registros = [];

  function boton(texto, accion) {
    const elemento = document.createElement("button");
    elemento.type = "button";
    elemento.className = "button small secondary";
    elemento.textContent = texto;
    elemento.addEventListener("click", () => Promise.resolve().then(accion).catch((error) => showToast(error.message, true)));
    return elemento;
  }

  function fila(cuerpo, valores) {
    const elemento = document.createElement("tr");
    valores.forEach((valor) => makeCell(elemento, valor));
    cuerpo.append(elemento);
    return elemento;
  }

  function fechaLocal(valor) {
    const fecha = new Date(valor);
    const parte = (numero) => String(numero).padStart(2, "0");
    return `${fecha.getFullYear()}-${parte(fecha.getMonth() + 1)}-${parte(fecha.getDate())}T${parte(fecha.getHours())}:${parte(fecha.getMinutes())}`;
  }

  function detalle(titulo, lineas) {
    const modal = document.querySelector("#modal-detalle");
    modal.querySelector("h2").textContent = titulo;
    const contenido = modal.querySelector("#modal-detalle-contenido");
    contenido.replaceChildren();
    for (const texto of lineas) {
      const parrafo = document.createElement("p");
      parrafo.textContent = texto;
      contenido.append(parrafo);
    }
    modal.hidden = false;
  }

  function actualizarReservas(filas) {
    reservas = filas;
    const momento = Date.now();
    const catalogo = getCatalogo();
    const vigentes = filas.filter((reserva) => reserva.state === "CONFIRMADA" &&
      new Date(reserva.starts_at).getTime() <= momento && momento < new Date(reserva.ends_at).getTime());
    fillSelect(document.querySelector('#loan-form [name="reservation_id"]'), vigentes,
      (reserva) => {
        const unidad = catalogo.units.find((item) => item.id === reserva.unit_id);
        const ficha = catalogo.items.find((item) => item.id === unidad?.item_card_id);
        return `Reserva ${reserva.id} · ${unidad?.inventory_code || `unidad ${reserva.unit_id}`} · ${ficha?.name || "bien"} · vence ${dateLabel(reserva.ends_at)}`;
      },
      "Selecciona una reserva confirmada en horario vigente");
  }

  const formularioPrestamo = document.querySelector("#loan-form");
  formularioPrestamo.elements.reservation_id.addEventListener("change", () => {
    const reserva = reservas.find((elemento) => elemento.id === formularioPrestamo.elements.reservation_id.value);
    if (!reserva) return;
    formularioPrestamo.elements.due_date.value = fechaLocal(reserva.ends_at);
    formularioPrestamo.elements.due_date.max = fechaLocal(reserva.ends_at);
  });
  formularioPrestamo.addEventListener("submit", (evento) => {
    evento.preventDefault();
    submitJsonForm(formularioPrestamo, "/loans", (datos) => ({
      origin_reservation_id: datos.get("reservation_id"),
      due_at: new Date(datos.get("due_date")).toISOString(),
      use_mode: datos.get("modalidad_uso"),
      delivered_condition: String(datos.get("condicion_entrega")).trim(),
      delivered_accessories: String(datos.get("accesorios_entregados")).split(",").map((valor) => valor.trim()).filter(Boolean),
      notes: String(datos.get("notes")).trim() || null,
    }), "Préstamo entregado.", refrescar);
  });

  function abrirDevolucion(prestamo) {
    const modal = document.querySelector("#modal-devolver");
    const condicion = document.querySelector("#modal-devolver-condicion");
    const accesorios = document.querySelector("#modal-devolver-accesorios");
    const destino = document.querySelector("#modal-devolver-destino");
    condicion.value = "";
    accesorios.value = "";
    destino.value = "DISPONIBLE";
    const aceptar = modal.querySelector('[data-action="aceptar-modal"]');
    aceptar.onclick = async () => {
      if (!condicion.value.trim() || !condicion.reportValidity()) {
        showToast("Indica la condición del bien recibido.", true);
        return;
      }
      aceptar.disabled = true;
      try {
        await request(`/loans/${prestamo.id}/return`, { method: "POST", body: JSON.stringify({
          condition: condicion.value.trim(), accessories: accesorios.value.split(",").map((valor) => valor.trim()).filter(Boolean),
          disposition: destino.value,
        }) });
        modal.hidden = true;
        showToast("Devolución registrada.");
        await refrescar();
      } catch (error) { showToast(error.message, true); }
      finally { aceptar.disabled = false; }
    };
    modal.hidden = false;
  }

  async function cargarPrestamos() {
    const prestamos = await request("/loans");
    const cuerpo = document.querySelector("#loans-table");
    cuerpo.replaceChildren();
    const nombres = { ACTIVO: "En préstamo", VENCIDO: "Vencido", DEVUELTO: "Devuelto", CERRADO_POR_PERDIDA: "Cerrado por pérdida" };
    for (const prestamo of prestamos) {
      const valores = [prestamo.unit_code];
      if (isAdmin()) valores.push(prestamo.applicant_name, prestamo.administrator_name, prestamo.origin_reservation_id);
      valores.push(dateLabel(prestamo.starts_at), dateLabel(prestamo.due_at), nombres[prestamo.state] || prestamo.state);
      if (isAdmin()) valores.push(`${prestamo.late_minutes} min`);
      const elemento = fila(cuerpo, valores);
      const acciones = makeCell(elemento, "");
      if (isAdmin() && ["ACTIVO", "VENCIDO"].includes(prestamo.state)) {
        acciones.append(boton("Devolver", () => abrirDevolucion(prestamo)));
      }
      acciones.append(boton("Detalle", () => detalle(`Préstamo de ${prestamo.unit_code}`, [
        `Solicitante: ${prestamo.applicant_name}.`,
        `Condición al entregar: ${prestamo.delivered_condition}.`,
        `Accesorios entregados: ${prestamo.delivered_accessories.join(", ") || "Ninguno"}.`,
        `Devolución: ${dateLabel(prestamo.returned_at)}. Condición: ${prestamo.returned_condition || "Pendiente"}.`,
        `Política conservada: ${prestamo.applied_policy.name || "Sin nombre"}, versión ${prestamo.applied_policy.version || "histórica"}.`,
        `Duración autorizada: ${prestamo.applied_policy.max_duration} días. Máximo simultáneo: ${prestamo.applied_policy.max_units}.`,
      ])));
    }
    document.querySelector("#loans-empty").hidden = prestamos.length > 0;
    actualizarReservas(reservas);
  }

  const formularioPolitica = document.querySelector("#policy-form");
  formularioPolitica.elements.role.addEventListener("change", () => {
    const maximo = formularioPolitica.elements.role.value === "ESTUDIANTE" ? 3 : 7;
    formularioPolitica.elements.max_duration.max = String(maximo);
    formularioPolitica.elements.max_duration.value = String(maximo);
  });
  formularioPolitica.addEventListener("submit", (evento) => {
    evento.preventDefault();
    submitJsonForm(formularioPolitica, "/policies", (datos) => {
      const desde = datos.get("valid_from");
      const hasta = datos.get("valid_until");
      if (desde && hasta && hasta <= desde) throw new Error("El fin de vigencia debe ser posterior al inicio.");
      return {
        name: String(datos.get("name")).trim(), role: datos.get("role"), item_type_id: datos.get("item_type_id"),
        max_units: Number(datos.get("max_units")), max_duration: Number(datos.get("max_duration")),
        permitted: datos.get("permitted") === "on", duration_unit: "DIAS",
        valid_from: desde ? new Date(desde).toISOString() : null,
        valid_until: hasta ? new Date(hasta).toISOString() : null,
      };
    }, "Nueva versión publicada.", async () => {
      formularioPolitica.elements.role.dispatchEvent(new Event("change"));
      await cargarPoliticas();
    });
  });

  async function cargarPoliticas() {
    politicas = await request("/policies");
    const tipos = getCatalogo().types;
    fillSelect(formularioPolitica.elements.item_type_id, tipos, (tipo) => tipo.name, "Selecciona tipo de bien");
    const cuerpo = document.querySelector("#policies-table");
    cuerpo.replaceChildren();
    for (const politica of politicas) {
      const elemento = fila(cuerpo, [
        tipos.find((tipo) => tipo.id === politica.item_type_id)?.name || politica.item_type_id,
        politica.role === "ESTUDIANTE" ? "Estudiante" : "Docente", politica.version,
        politica.max_units, politica.max_duration, politica.permitted ? "Permitido" : "No permitido",
        `${dateLabel(politica.valid_from)} → ${dateLabel(politica.valid_until)}`,
        politica.status === "VIGENTE" ? "Vigente" : politica.status === "PROGRAMADA" ? "Programada" : "Finalizada",
      ]);
      if (isAdmin()) {
        const acciones = makeCell(elemento, "");
        acciones.append(boton("Nueva versión", () => {
          for (const campo of ["name", "role", "item_type_id", "max_units", "max_duration"]) formularioPolitica.elements[campo].value = politica[campo];
          formularioPolitica.elements.permitted.checked = politica.permitted;
          formularioPolitica.elements.valid_from.value = "";
          formularioPolitica.elements.valid_until.value = "";
          formularioPolitica.elements.max_duration.max = politica.role === "ESTUDIANTE" ? "3" : "7";
          formularioPolitica.scrollIntoView({ behavior: "smooth" });
        }));
        acciones.append(boton("Ver versión", async () => {
          const historial = await request(`/policies/${politica.id}/history`);
          detalle(`Historial: ${politica.name}`, historial.map((texto) => {
            const version = JSON.parse(texto);
            return `Versión ${version.version}: ${version.max_duration} días, ${version.max_units} bienes simultáneos; ${version.permitted ? "reservas permitidas" : "reservas no permitidas"}. Publicada para ${version.role}.`;
          }));
        }));
      }
    }
    document.querySelector("#policies-empty").hidden = politicas.length > 0;
  }

  const formularioPeriodo = document.querySelector("#academic-period-form");
  formularioPeriodo.addEventListener("submit", (evento) => {
    evento.preventDefault();
    submitJsonForm(formularioPeriodo, "/academic/terms", (datos) => {
      if (datos.get("fecha_fin") <= datos.get("fecha_inicio")) throw new Error("El fin del período debe ser posterior al inicio.");
      return Object.fromEntries(datos.entries());
    }, "Período registrado.", cargarAcademico);
  });
  const formularioRegistro = document.querySelector("#academic-record-form");
  formularioRegistro.addEventListener("submit", (evento) => {
    evento.preventDefault();
    submitJsonForm(formularioRegistro, "/academic/records", (datos) => {
      const salida = Object.fromEntries(datos.entries());
      for (const campo of ["promedio_acumulado", "creditos_aprobados", "creditos_reprobados", "creditos_cursando"]) salida[campo] = Number(salida[campo]);
      return salida;
    }, "Información académica guardada.", cargarAcademico);
  });
  const formularioMatricula = document.querySelector("#academic-matricula-form");
  formularioMatricula.addEventListener("submit", (evento) => {
    evento.preventDefault();
    submitJsonForm(formularioMatricula, "/academic/enrollments", (datos) => Object.fromEntries(datos.entries()),
      "Matrícula registrada.", cargarAcademico);
  });

  async function cargarAcademico() {
    if (!isAdmin()) return;
    const [estudiantes, periodos, informacion, matriculas] = await Promise.all([
      request("/academic/students"), request("/academic/terms"), request("/academic/records"), request("/academic/enrollments"),
    ]);
    registros = informacion;
    for (const formulario of [formularioRegistro, formularioMatricula]) {
      fillSelect(formulario.elements.persona_id, estudiantes, (persona) => `${persona.name} · ${persona.cui || persona.id}`, "Selecciona estudiante");
    }
    fillSelect(formularioMatricula.elements.id_semestre, periodos.map((periodo) => ({ ...periodo, id: periodo.id_semestre })),
      (periodo) => periodo.nombre_semestre, "Selecciona período");
    fillSelect(formularioRegistro.elements.periodo, periodos.map((periodo) => ({
      ...periodo, id: periodo.nombre_semestre,
    })), (periodo) => `${periodo.nombre_semestre} · ${periodo.fecha_inicio} – ${periodo.fecha_fin}`,
    "Selecciona período registrado");
    const tablaPeriodos = document.querySelector("#academic-periods-table");
    const tablaRegistros = document.querySelector("#academic-records-table");
    const tablaMatriculas = document.querySelector("#academic-matriculas-table");
    [tablaPeriodos, tablaRegistros, tablaMatriculas].forEach((cuerpo) => cuerpo.replaceChildren());
    periodos.forEach((periodo) => fila(tablaPeriodos, [periodo.nombre_semestre, periodo.fecha_inicio, periodo.fecha_fin]));
    for (const registro of registros) {
      const elemento = fila(tablaRegistros, [registro.cui, registro.estudiante, registro.periodo,
        registro.situacion, registro.promedio_acumulado, registro.creditos_aprobados,
        registro.creditos_reprobados, registro.creditos_cursando]);
      makeCell(elemento, "").append(boton("Editar", () => {
        for (const campo of ["persona_id", "periodo", "situacion", "promedio_acumulado", "creditos_aprobados", "creditos_reprobados", "creditos_cursando"]) formularioRegistro.elements[campo].value = registro[campo];
        formularioRegistro.scrollIntoView({ behavior: "smooth" });
      }));
    }
    matriculas.forEach((matricula) => fila(tablaMatriculas, [matricula.cui, matricula.estudiante, matricula.nombre_semestre, dateLabel(matricula.fecha_matricula)]));
    document.querySelector("#academic-periods-empty").hidden = periodos.length > 0;
    document.querySelector("#academic-records-empty").hidden = registros.length > 0;
    document.querySelector("#academic-matriculas-empty").hidden = matriculas.length > 0;
  }

  for (const cerrar of document.querySelectorAll('[data-action="cerrar-modal"]')) {
    cerrar.addEventListener("click", () => { cerrar.closest(".modal").hidden = true; });
  }
  document.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") document.querySelectorAll(".modal").forEach((modal) => { modal.hidden = true; });
  });
  return { cargarPoliticas, cargarPrestamos, cargarAcademico, actualizarReservas,
    limpiar() { politicas = []; reservas = []; registros = []; } };
}
