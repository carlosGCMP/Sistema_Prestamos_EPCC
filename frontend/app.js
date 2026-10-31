// Configuración y datos de la sesión.
const claveToken = "epcc_access_token";
const nombresRoles = {
    ESTUDIANTE: "Estudiante",
    DOCENTE: "Docente",
    PERSONAL_ADMINISTRATIVO: "Personal administrativo",
    ADMIN_INVENTARIO: "Administrador de inventario",
};
const nombresEstados = {
    DISPONIBLE: "Disponible",
    PRESTADA: "Prestada",
    MANTENIMIENTO: "Mantenimiento",
    BAJA: "Baja",
    PENDIENTE: "Pendiente",
    CONFIRMADA: "Confirmada",
    RECHAZADA: "Rechazada",
    CANCELADA: "Cancelada",
    ACTIVA: "Activa",
    INACTIVA: "Inactiva",
};
const clasesEstados = {
    DISPONIBLE: "available",
    CONFIRMADA: "confirmed",
    PENDIENTE: "pending",
    ACTIVA: "active",
    INACTIVA: "inactive",
    PRESTADA: "loaned",
    BAJA: "retired",
    RECHAZADA: "rejected",
    CANCELADA: "cancelled",
};

const vistaAcceso = document.querySelector("#login-view");
const vistaAplicacion = document.querySelector("#app-view");
const avisoGeneral = document.querySelector("#toast");
const formularioUsuario = document.querySelector("#person-form");
const accionesPendientes = new Set();
let personaActual = null;
let temporizadorAviso = null;
let datosInventario = { categorias: [], tipos: [], fichas: [], unidades: [] };

function esAdministrador() {
    return personaActual?.role === "ADMIN_INVENTARIO";
}

// Mensajes y peticiones a la API. Las claves del JSON conservan sus nombres originales.
function mostrarMensaje(texto, esError = false) {
    avisoGeneral.textContent = texto;
    avisoGeneral.classList.toggle("error-toast", esError);
    avisoGeneral.hidden = false;
    window.clearTimeout(temporizadorAviso);
    temporizadorAviso = window.setTimeout(() => {
        avisoGeneral.hidden = true;
    }, 6500);
}

function mostrarMensajeFormulario(formulario, texto, esError = false) {
    const mensaje = formulario.querySelector(".mensaje-formulario");
    mensaje.textContent = texto;
    mensaje.classList.toggle("error", esError);
    mensaje.setAttribute("role", esError ? "alert" : "status");
    mensaje.hidden = !texto;
}

function actualizarConexion(disponible) {
    document.querySelector("#estado-api").textContent = disponible
        ? "API disponible"
        : "Sin conexión con la API";
    document.querySelector("#indicador-api").classList.toggle("sin-conexion", !disponible);
}

async function solicitarDatos(ruta, opciones = {}) {
    const cabeceras = new Headers(opciones.headers);
    const token = sessionStorage.getItem(claveToken);
    if (token) {
        cabeceras.set("Authorization", `Bearer ${token}`);
    }
    if (typeof opciones.body === "string") {
        cabeceras.set("Content-Type", "application/json");
    }

    let respuesta;
    try {
        respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
    } catch {
        actualizarConexion(false);
        throw new Error("No se pudo conectar con el servidor. Comprueba que la API esté iniciada.");
    }
    actualizarConexion(true);
    if (respuesta.status === 204) {
        return null;
    }

    const datos = await respuesta.json().catch(() => null);
    if (!respuesta.ok) {
        let texto = "No se pudo completar la operación.";
        if (typeof datos?.detail === "string") {
            texto = datos.detail;
        } else if (Array.isArray(datos?.detail)) {
            texto = datos.detail.map((detalle) => detalle.msg).join("; ");
        } else if (respuesta.status >= 500) {
            texto = "El servidor tuvo un problema. Inténtalo de nuevo más tarde.";
        }
        if (respuesta.status === 401 && ruta !== "/auth/token") {
            texto = "Tu sesión venció. Inicia sesión nuevamente.";
            sessionStorage.removeItem(claveToken);
            mostrarAcceso(texto);
        }
        const error = new Error(texto);
        error.campos = Array.isArray(datos?.detail) ? datos.detail : [];
        throw error;
    }
    return datos;
}

function cambiarEstadoBoton(boton, ocupado, texto = "Guardando…") {
    if (ocupado) {
        boton.dataset.textoAnterior = boton.textContent;
        boton.dataset.deshabilitadoAnterior = String(boton.disabled);
        boton.disabled = true;
        boton.textContent = texto;
        boton.setAttribute("aria-busy", "true");
    } else {
        boton.textContent = boton.dataset.textoAnterior;
        boton.disabled = boton.dataset.deshabilitadoAnterior === "true";
        boton.removeAttribute("aria-busy");
    }
}

// Validación y envío de los formularios que ya tienen una API disponible.
function obtenerTexto(datos, nombre) {
    return String(datos.get(nombre) || "").trim();
}

function validarFormulario(formulario) {
    if (formulario.classList.contains("formulario-dependiente")) {
        const selector = formulario.querySelector("select[required]");
        if (selector.disabled || selector.options.length < 2) {
            mostrarMensajeFormulario(
                formulario,
                "Primero completa el registro anterior o actualiza el inventario.",
                true,
            );
            return false;
        }
    }
    for (const campo of formulario.querySelectorAll("input, select, textarea")) {
        if (campo.disabled || campo.type === "password") {
            continue;
        }
        if (campo.required && !campo.value.trim()) {
            campo.setCustomValidity("Completa este campo sin usar solamente espacios.");
        }
    }
    return formulario.reportValidity();
}

function mostrarErrorFormulario(formulario, error) {
    mostrarMensajeFormulario(formulario, error.message, true);
    let primerCampo = null;
    for (const detalle of error.campos || []) {
        const campo = formulario.elements.namedItem(detalle.loc?.[1]);
        if (campo && !campo.disabled && campo.setCustomValidity) {
            campo.setCustomValidity(detalle.msg);
            campo.setAttribute("aria-invalid", "true");
            primerCampo ||= campo;
        }
    }
    primerCampo?.focus();
}

async function enviarFormulario(formulario, ruta, prepararDatos, textoExito, actualizar) {
    if (formulario.dataset.enviando === "true" || !validarFormulario(formulario)) {
        return;
    }
    const boton = formulario.querySelector('button[type="submit"]');
    formulario.dataset.enviando = "true";
    cambiarEstadoBoton(boton, true);
    mostrarMensajeFormulario(formulario, "");
    try {
        const datos = prepararDatos(new FormData(formulario));
        const registro = await solicitarDatos(ruta, {
            method: "POST",
            body: JSON.stringify(datos),
        });
        formulario.reset();
        if (formulario === formularioUsuario) {
            actualizarCamposPorRol();
        }
        // Un fallo al refrescar la tabla no significa que haya fallado el guardado.
        try {
            await actualizar(registro);
            mostrarMensajeFormulario(formulario, textoExito);
        } catch {
            mostrarMensajeFormulario(
                formulario,
                `${textoExito} No se pudo actualizar la lista. Pulsa Actualizar; no repitas el registro.`,
            );
        }
    } catch (error) {
        mostrarErrorFormulario(formulario, error);
    } finally {
        delete formulario.dataset.enviando;
        cambiarEstadoBoton(boton, false);
        actualizarBloqueos();
    }
}

function actualizarCamposPorRol() {
    const rol = formularioUsuario.elements.role.value;
    const grupos = [
        [".student-field", rol === "ESTUDIANTE"],
        [".teacher-field", rol === "DOCENTE"],
        [".staff-field", rol === "PERSONAL_ADMINISTRATIVO"],
        [".admin-attribution-field", ["DOCENTE", "PERSONAL_ADMINISTRATIVO"].includes(rol)],
    ];
    for (const [selector, visible] of grupos) {
        for (const etiqueta of formularioUsuario.querySelectorAll(selector)) {
            etiqueta.hidden = !visible;
            const campo = etiqueta.querySelector("input, select");
            const pendiente = campo.hasAttribute("data-no-disponible");
            campo.disabled = !visible || pendiente;
            campo.required = visible && !pendiente;
            campo.setCustomValidity("");
            campo.removeAttribute("aria-invalid");
        }
    }
    if (!formularioUsuario.elements.start_date.value) {
        const hoy = new Date();
        hoy.setMinutes(hoy.getMinutes() - hoy.getTimezoneOffset());
        formularioUsuario.elements.start_date.value = hoy.toISOString().slice(0, 10);
    }
}

function actualizarBloqueos() {
    for (const formulario of document.querySelectorAll(".formulario-dependiente")) {
        const selector = formulario.querySelector("select[required]");
        const sinOpciones = selector.disabled || selector.options.length < 2;
        formulario.querySelector('button[type="submit"]').disabled =
            sinOpciones || formulario.dataset.enviando === "true";
        formulario.querySelector(".ayuda-dependencia").hidden = !sinOpciones;
    }
}

function obtenerCaracteristicas(datos) {
    const caracteristicas = Object.create(null);
    const campo = document.querySelector('#item-form [name="caracteristicas"]');
    for (const linea of obtenerTexto(datos, "caracteristicas").split("\n")) {
        if (!linea.trim()) {
            continue;
        }
        const separador = linea.indexOf(":");
        const nombre = linea.slice(0, separador).trim();
        const valor = linea.slice(separador + 1).trim();
        if (separador < 1 || !nombre || !valor || Object.hasOwn(caracteristicas, nombre)) {
            campo.setCustomValidity(
                "Usa una característica por línea: nombre: valor, sin nombres repetidos.",
            );
            campo.reportValidity();
            throw new Error("Revisa las características. Ejemplo: RAM: 8GB.");
        }
        caracteristicas[nombre] = valor;
    }
    return caracteristicas;
}

function prepararReserva(datos) {
    const inicio = new Date(datos.get("starts_at"));
    const fin = new Date(datos.get("ends_at"));
    const formulario = document.querySelector("#reservation-form");
    if (!Number.isFinite(inicio.getTime()) || inicio <= new Date()) {
        formulario.elements.starts_at.setCustomValidity("Selecciona una fecha futura.");
        formulario.elements.starts_at.reportValidity();
        throw new Error("La fecha de inicio debe ser futura.");
    }
    if (!Number.isFinite(fin.getTime()) || fin <= inicio) {
        formulario.elements.ends_at.setCustomValidity(
            "La fecha final debe ser posterior al inicio.",
        );
        formulario.elements.ends_at.reportValidity();
        throw new Error("Revisa el intervalo de la reserva.");
    }
    return {
        unit_id: datos.get("unit_id"),
        starts_at: inicio.toISOString(),
        ends_at: fin.toISOString(),
        intended_use: obtenerTexto(datos, "intended_use"),
    };
}

// Sesión y navegación.
function mostrarAcceso(error = "") {
    personaActual = null;
    vistaAplicacion.hidden = true;
    vistaAcceso.hidden = false;
    mostrarMensajeFormulario(document.querySelector("#login-form"), error, Boolean(error));
}

function mostrarPanel(persona) {
    personaActual = persona;
    vistaAcceso.hidden = true;
    vistaAplicacion.hidden = false;
    document.querySelector("#account-name").textContent =
        `${persona.full_name} · ${nombresRoles[persona.role] || persona.role}`;
    for (const elemento of document.querySelectorAll(".admin-only")) {
        elemento.hidden = !esAdministrador();
    }
    for (const elemento of document.querySelectorAll(".requester-only")) {
        elemento.hidden = !["ESTUDIANTE", "DOCENTE"].includes(persona.role);
    }
    document.querySelector("#reservations-heading").textContent = esAdministrador()
        ? "Todas las reservas"
        : "Mis reservas";
    activarVista("inventory-view");
}

async function iniciarSesion(evento) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    if (formulario.dataset.enviando === "true" || !validarFormulario(formulario)) {
        return;
    }
    const boton = formulario.querySelector('button[type="submit"]');
    formulario.dataset.enviando = "true";
    cambiarEstadoBoton(boton, true, "Ingresando…");
    mostrarMensajeFormulario(formulario, "");
    try {
        const datos = new URLSearchParams(new FormData(formulario));
        datos.set("username", datos.get("username").trim());
        const sesion = await solicitarDatos("/auth/token", { method: "POST", body: datos });
        sessionStorage.setItem(claveToken, sesion.access_token);
        const persona = await solicitarDatos("/me");
        formulario.reset();
        mostrarPanel(persona);
    } catch (error) {
        sessionStorage.removeItem(claveToken);
        mostrarAcceso(error.message);
    } finally {
        delete formulario.dataset.enviando;
        cambiarEstadoBoton(boton, false);
    }
}

async function cerrarSesion(evento) {
    const boton = evento.currentTarget;
    if (boton.disabled) {
        return;
    }
    cambiarEstadoBoton(boton, true, "Cerrando…");
    try {
        await solicitarDatos("/auth/logout", { method: "POST" });
    } catch {
        mostrarMensaje(
            "Sesión cerrada en este equipo. No se pudo confirmar el cierre en el servidor.",
            true,
        );
    } finally {
        sessionStorage.removeItem(claveToken);
        for (const formulario of vistaAplicacion.querySelectorAll("form")) {
            formulario.reset();
            const mensaje = formulario.querySelector(".mensaje-formulario");
            if (mensaje) {
                mostrarMensajeFormulario(formulario, "");
            }
        }
        datosInventario = { categorias: [], tipos: [], fichas: [], unidades: [] };
        actualizarCamposPorRol();
        mostrarAcceso();
        cambiarEstadoBoton(boton, false);
    }
}

function activarVista(identificador) {
    for (const vista of document.querySelectorAll(".page-view")) {
        vista.hidden = vista.id !== identificador;
    }
    for (const boton of document.querySelectorAll(".nav-link")) {
        const activo = boton.dataset.view === identificador;
        boton.classList.toggle("active", activo);
        if (activo) {
            boton.setAttribute("aria-current", "page");
        } else {
            boton.removeAttribute("aria-current");
        }
    }
    actualizarVista(identificador);
}

async function actualizarVista(identificador, mostrarAviso = false) {
    const vista = document.getElementById(identificador);
    if (vista.hasAttribute("data-pendiente") || vista.dataset.cargando === "true") {
        return;
    }
    const boton = vista.querySelector(".refresh-button");
    vista.dataset.cargando = "true";
    cambiarEstadoBoton(boton, true, "Actualizando…");
    try {
        if (identificador === "inventory-view") {
            await cargarInventario();
        } else if (identificador === "reservations-view") {
            await cargarReservas();
        } else if (identificador === "people-view") {
            await cargarPersonas();
        }
        if (mostrarAviso) {
            mostrarMensaje("Información actualizada.");
        }
    } catch (error) {
        mostrarMensaje(error.message, true);
    } finally {
        delete vista.dataset.cargando;
        cambiarEstadoBoton(boton, false);
    }
}

// Carga y presentación de los datos disponibles.
function agregarCelda(fila, valor) {
    const celda = document.createElement("td");
    celda.textContent = valor === null || valor === undefined || valor === "" ? "—" : String(valor);
    fila.append(celda);
    return celda;
}

function agregarEstado(fila, estado) {
    const celda = agregarCelda(fila, "");
    const etiqueta = document.createElement("span");
    etiqueta.className = `badge ${clasesEstados[estado] || ""}`;
    etiqueta.textContent = nombresEstados[estado] || estado;
    celda.replaceChildren(etiqueta);
}

function completarSelector(selector, registros, obtenerNombre, textoInicial) {
    const valorAnterior = selector.value;
    selector.replaceChildren(new Option(textoInicial, ""));
    for (const registro of registros) {
        selector.add(new Option(obtenerNombre(registro), registro.id));
    }
    if (registros.some((registro) => registro.id === valorAnterior)) {
        selector.value = valorAnterior;
    }
    selector.disabled = registros.length === 0;
}

function nombreFicha(identificador) {
    return datosInventario.fichas.find((ficha) => ficha.id === identificador)?.name || "Bien";
}

async function cargarInventario() {
    const [categorias, tipos, fichas, unidades] = await Promise.all([
        solicitarDatos("/inventory/categories"),
        solicitarDatos("/inventory/types"),
        solicitarDatos("/inventory/items"),
        solicitarDatos("/inventory/units"),
    ]);
    datosInventario = { categorias, tipos, fichas, unidades };
    const tabla = document.querySelector("#units-table");
    tabla.replaceChildren();
    for (const unidad of unidades) {
        const fila = document.createElement("tr");
        agregarCelda(fila, unidad.inventory_code);
        agregarCelda(fila, nombreFicha(unidad.item_card_id));
        agregarCelda(fila, unidad.location);
        agregarCelda(fila, unidad.condition);
        agregarEstado(fila, unidad.state);
        tabla.append(fila);
    }
    document.querySelector("#units-empty").hidden = unidades.length > 0;
    completarSelector(
        document.querySelector('#type-form [name="category_id"]'),
        categorias.filter((categoria) => categoria.active),
        (categoria) => categoria.name,
        "Selecciona una categoría",
    );
    completarSelector(
        document.querySelector('#item-form [name="item_type_id"]'),
        tipos.filter((tipo) => tipo.active),
        (tipo) => tipo.name,
        "Selecciona un tipo",
    );
    completarSelector(
        document.querySelector('#unit-form [name="item_card_id"]'),
        fichas.filter((ficha) => ficha.active),
        (ficha) => ficha.name,
        "Selecciona una ficha",
    );
    const disponibles = unidades.filter((unidad) => {
        const ficha = fichas.find((registro) => registro.id === unidad.item_card_id);
        const tipo = tipos.find((registro) => registro.id === ficha?.item_type_id);
        return unidad.state === "DISPONIBLE" && ficha?.active && tipo?.active && tipo.lendable;
    });
    completarSelector(
        document.querySelector('#reservation-form [name="unit_id"]'),
        disponibles,
        (unidad) => `${unidad.inventory_code} · ${nombreFicha(unidad.item_card_id)}`,
        "Selecciona una unidad",
    );
    actualizarBloqueos();
}

function mostrarFecha(valor) {
    const fecha = new Date(valor);
    if (!valor || !Number.isFinite(fecha.getTime())) {
        return "—";
    }
    return new Intl.DateTimeFormat("es-PE", {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(fecha);
}

function agregarBoton(acciones, texto, estilo, ejecutar) {
    const boton = document.createElement("button");
    boton.type = "button";
    boton.className = `button small ${estilo}`;
    boton.textContent = texto;
    boton.disabled = accionesPendientes.has(acciones.closest("tr").dataset.registro);
    boton.addEventListener("click", () => ejecutar(boton));
    acciones.append(boton);
}

async function cargarReservas() {
    const reservas = await solicitarDatos("/reservations");
    const tabla = document.querySelector("#reservations-table");
    tabla.replaceChildren();
    for (const reserva of reservas) {
        const fila = document.createElement("tr");
        fila.dataset.registro = `reserva-${reserva.id}`;
        const unidad = datosInventario.unidades.find((registro) => registro.id === reserva.unit_id);
        agregarCelda(fila, unidad?.inventory_code || reserva.unit_id.slice(0, 8));
        const solicitante = agregarCelda(fila, reserva.applicant_id.slice(0, 8));
        solicitante.className = "admin-only";
        solicitante.hidden = !esAdministrador();
        solicitante.title = reserva.applicant_id;
        agregarCelda(fila, mostrarFecha(reserva.starts_at));
        agregarCelda(fila, mostrarFecha(reserva.ends_at));
        agregarCelda(fila, reserva.intended_use);
        agregarEstado(fila, reserva.state);
        agregarCelda(fila, reserva.decision_reason);
        const acciones = agregarCelda(fila, "");
        acciones.replaceChildren();
        acciones.className = "acciones-tabla";
        if (esAdministrador() && reserva.state === "PENDIENTE") {
            agregarBoton(acciones, "Confirmar", "primary", (boton) =>
                decidirReserva(boton, reserva.id, true),
            );
            agregarBoton(acciones, "Rechazar", "danger", (boton) =>
                decidirReserva(boton, reserva.id, false),
            );
        }
        if (["PENDIENTE", "CONFIRMADA"].includes(reserva.state)) {
            agregarBoton(acciones, "Cancelar", "quiet", (boton) =>
                cancelarReserva(boton, reserva.id),
            );
        }
        tabla.append(fila);
    }
    document.querySelector("#reservations-empty").hidden = reservas.length > 0;
}

async function cargarPersonas() {
    const personas = await solicitarDatos("/people");
    const tabla = document.querySelector("#people-table");
    tabla.replaceChildren();
    for (const persona of personas) {
        const fila = document.createElement("tr");
        fila.dataset.registro = `persona-${persona.id}`;
        agregarCelda(fila, persona.full_name);
        agregarCelda(fila, persona.institutional_email);
        agregarCelda(fila, nombresRoles[persona.role] || persona.role);
        agregarCelda(fila, persona.cui);
        agregarEstado(fila, persona.state);
        const acciones = agregarCelda(fila, "");
        acciones.replaceChildren();
        acciones.className = "acciones-tabla";
        if (persona.state === "ACTIVA" && persona.id !== personaActual.id) {
            agregarBoton(acciones, "Desactivar", "danger", (boton) =>
                desactivarPersona(boton, persona),
            );
        }
        tabla.append(fila);
    }
    document.querySelector("#people-empty").hidden = personas.length > 0;
}

// Se reutilizan los dos diálogos existentes. El navegador maneja Escape y el foco.
function pedirConfirmacion(titulo, mensaje, requiereMotivo = false) {
    if (document.querySelector("dialog[open]")) {
        return Promise.resolve(null);
    }
    const identificador = requiereMotivo ? "modal-motivo" : "modal-confirmar";
    const dialogo = document.getElementById(identificador);
    document.getElementById(`${identificador}-titulo`).textContent = titulo;
    document.getElementById(`${identificador}-mensaje`).textContent = mensaje;
    const campoMotivo = document.querySelector("#modal-motivo-texto");
    campoMotivo.value = "";
    campoMotivo.setCustomValidity("");
    dialogo.returnValue = "cancelar";
    return new Promise((resolver) => {
        dialogo.addEventListener(
            "close",
            () => {
                const resultado = requiereMotivo ? campoMotivo.value.trim() : true;
                resolver(dialogo.returnValue === "aceptar" ? resultado : null);
            },
            { once: true },
        );
        dialogo.showModal();
    });
}

async function ejecutarAccion(boton, ruta, datos, textoExito, actualizar) {
    const fila = boton.closest("tr");
    const registro = fila.dataset.registro;
    if (fila.dataset.enviando === "true" || accionesPendientes.has(registro)) {
        return;
    }
    accionesPendientes.add(registro);
    fila.dataset.enviando = "true";
    const botones = fila.querySelectorAll("button");
    cambiarEstadoBoton(boton, true, "Procesando…");
    for (const otroBoton of botones) {
        otroBoton.disabled = true;
    }
    try {
        await solicitarDatos(ruta, { method: "POST", body: JSON.stringify(datos) });
        accionesPendientes.delete(registro);
        cambiarEstadoBoton(boton, false);
        for (const otroBoton of botones) {
            otroBoton.disabled = true;
        }
        try {
            await actualizar();
            mostrarMensaje(textoExito);
        } catch {
            mostrarMensaje(
                `${textoExito} No se pudo refrescar la lista. Pulsa Actualizar; no repitas la acción.`,
            );
            return;
        }
    } catch (error) {
        accionesPendientes.delete(registro);
        mostrarMensaje(error.message, true);
        const filaActual = [...document.querySelectorAll("tr[data-registro]")].find(
            (elemento) => elemento.dataset.registro === registro,
        );
        for (const otroBoton of filaActual?.querySelectorAll("button") || []) {
            otroBoton.disabled = false;
        }
        cambiarEstadoBoton(boton, false);
        delete fila.dataset.enviando;
    }
    // Tras un éxito, la fila anterior queda bloqueada hasta reemplazarla por datos actuales.
}

async function decidirReserva(boton, identificador, confirmar) {
    const resultado = await pedirConfirmacion(
        confirmar ? "Confirmar reserva" : "Rechazar reserva",
        confirmar ? "¿Deseas confirmar esta reserva?" : "Indica por qué rechazas esta reserva.",
        !confirmar,
    );
    if (!resultado) {
        return;
    }
    await ejecutarAccion(
        boton,
        `/reservations/${identificador}/decision`,
        { confirm: confirmar, reason: confirmar ? null : resultado },
        confirmar ? "Reserva confirmada." : "Reserva rechazada.",
        cargarReservas,
    );
}

async function cancelarReserva(boton, identificador) {
    const confirmado = await pedirConfirmacion(
        "Cancelar reserva",
        "¿Deseas cancelar esta reserva?",
    );
    if (confirmado) {
        await ejecutarAccion(
            boton,
            `/reservations/${identificador}/cancel`,
            {},
            "Reserva cancelada.",
            cargarReservas,
        );
    }
}

async function desactivarPersona(boton, persona) {
    const confirmado = await pedirConfirmacion(
        "Desactivar usuario",
        `¿Deseas desactivar a ${persona.full_name}?`,
    );
    if (confirmado) {
        await ejecutarAccion(
            boton,
            `/people/${persona.id}/deactivate`,
            {},
            "Usuario desactivado.",
            cargarPersonas,
        );
    }
}

// Eventos: cada formulario prepara únicamente los campos que acepta el backend.
document.querySelector("#login-form").addEventListener("submit", iniciarSesion);
document.querySelector("#logout-button").addEventListener("click", cerrarSesion);
formularioUsuario.elements.role.addEventListener("change", actualizarCamposPorRol);

for (const boton of document.querySelectorAll(".nav-link")) {
    boton.addEventListener("click", () => activarVista(boton.dataset.view));
}
for (const boton of document.querySelectorAll(".refresh-button")) {
    boton.addEventListener("click", () => actualizarVista(boton.closest(".page-view").id, true));
}
for (const formulario of document.querySelectorAll("form")) {
    formulario.addEventListener("input", (evento) => {
        const campo = evento.target;
        if (campo.setCustomValidity) {
            campo.setCustomValidity("");
            campo.removeAttribute("aria-invalid");
        }
        if (campo.name === "starts_at") {
            formulario.elements.ends_at.setCustomValidity("");
        }
    });
    formulario.addEventListener("reset", () => {
        for (const campo of formulario.querySelectorAll("input, select, textarea")) {
            campo.setCustomValidity("");
            campo.removeAttribute("aria-invalid");
        }
    });
}
document.querySelector("#modal-motivo form").addEventListener("submit", (evento) => {
    if (evento.submitter?.value !== "aceptar") {
        return;
    }
    const campo = document.querySelector("#modal-motivo-texto");
    if (!campo.value.trim()) {
        evento.preventDefault();
        campo.setCustomValidity("Escribe un motivo, no solamente espacios.");
        campo.reportValidity();
    }
});

document.querySelector("#category-form").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/inventory/categories",
        (datos) => ({
            name: obtenerTexto(datos, "name"),
            description: obtenerTexto(datos, "description") || null,
        }),
        "Categoría creada. Continúa con el tipo de bien.",
        async (categoria) => {
            await cargarInventario();
            document.querySelector('#type-form [name="category_id"]').value = categoria.id;
        },
    );
});
document.querySelector("#type-form").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/inventory/types",
        (datos) => ({
            name: obtenerTexto(datos, "name"),
            category_id: datos.get("category_id"),
            lendable: datos.get("lendable") === "on",
        }),
        "Tipo creado. Continúa con la ficha.",
        async (tipo) => {
            await cargarInventario();
            document.querySelector('#item-form [name="item_type_id"]').value = tipo.id;
        },
    );
});
document.querySelector("#item-form").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/inventory/items",
        (datos) => ({
            item_type_id: datos.get("item_type_id"),
            name: obtenerTexto(datos, "name"),
            description: obtenerTexto(datos, "description") || null,
            attributes: obtenerCaracteristicas(datos),
        }),
        "Ficha creada. Continúa con la unidad física.",
        async (ficha) => {
            await cargarInventario();
            document.querySelector('#unit-form [name="item_card_id"]').value = ficha.id;
        },
    );
});
document.querySelector("#unit-form").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/inventory/units",
        (datos) => ({
            item_card_id: datos.get("item_card_id"),
            inventory_code: obtenerTexto(datos, "inventory_code"),
            serial_number: obtenerTexto(datos, "serial_number") || null,
            location: obtenerTexto(datos, "location"),
            custody: obtenerTexto(datos, "custody"),
            condition: obtenerTexto(datos, "condition"),
            accessories: obtenerTexto(datos, "accessories")
                .split(",")
                .map((accesorio) => accesorio.trim())
                .filter(Boolean),
        }),
        "Unidad registrada.",
        cargarInventario,
    );
});
formularioUsuario.addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/people",
        (datos) => ({
            cui: obtenerTexto(datos, "cui"),
            document_type: datos.get("document_type"),
            document_number: obtenerTexto(datos, "document_number"),
            full_name: obtenerTexto(datos, "full_name"),
            institutional_email: obtenerTexto(datos, "institutional_email"),
            role: datos.get("role"),
            school_affiliation: obtenerTexto(datos, "school_affiliation"),
            start_date: datos.get("start_date"),
            username: obtenerTexto(datos, "username"),
            password: datos.get("password"),
            student_code: obtenerTexto(datos, "student_code") || null,
            program: obtenerTexto(datos, "program") || null,
            semester: datos.get("semester") ? Number(datos.get("semester")) : null,
            teacher_code: obtenerTexto(datos, "teacher_code") || null,
            specialty: obtenerTexto(datos, "specialty") || null,
        }),
        "Usuario creado.",
        cargarPersonas,
    );
});
document.querySelector("#reservation-form").addEventListener("submit", (evento) => {
    evento.preventDefault();
    enviarFormulario(
        evento.currentTarget,
        "/reservations",
        prepararReserva,
        "Solicitud de reserva enviada.",
        cargarReservas,
    );
});

// Los módulos pendientes conservan su diseño, pero nunca envían formularios sin API.
for (const vista of document.querySelectorAll("[data-pendiente]")) {
    vista.querySelector(".refresh-button").disabled = true;
    for (const formulario of vista.querySelectorAll("form")) {
        formulario.addEventListener("submit", (evento) => evento.preventDefault());
    }
}
actualizarCamposPorRol();
actualizarBloqueos();
if (sessionStorage.getItem(claveToken)) {
    solicitarDatos("/me")
        .then(mostrarPanel)
        .catch((error) => {
            mostrarAcceso(error.message);
        });
}
