import { crearModulos } from "./modulos.js";

const API = "";
const tokenKey = "epcc_access_token";
const roleNames = {
  ESTUDIANTE: "Estudiante",
  DOCENTE: "Docente",
  PERSONAL_ADMINISTRATIVO: "Personal administrativo",
  ADMIN_INVENTARIO: "Administrador de inventario",
};
const stateNames = {
  DISPONIBLE: "Disponible",
  PRESTADA: "Prestada",
  MANTENIMIENTO: "Mantenimiento",
  BAJA: "Baja",
  PENDIENTE: "Pendiente",
  CONFIRMADA: "Confirmada",
  RECHAZADA: "Rechazada",
  CANCELADA: "Cancelada",
  ATENDIDA: "Atendida",
  VENCIDA: "Vencida",
  ACTIVA: "Activa",
  INACTIVA: "Inactiva",
  VENCIDO: "Vencido",
  DEVUELTO: "Devuelto",
  CERRADO_POR_PERDIDA: "Cerrado por pérdida",
};
const stateClasses = {
  DISPONIBLE: "available",
  CONFIRMADA: "confirmed",
  PENDIENTE: "pending",
  ACTIVA: "active",
  INACTIVA: "inactive",
  PRESTADA: "loaned",
  BAJA: "retired",
  RECHAZADA: "rejected",
  CANCELADA: "cancelled",
  ATENDIDA: "returned",
  VENCIDA: "overdue",
  VENCIDO: "overdue",
  DEVUELTO: "returned",
  CERRADO_POR_PERDIDA: "lost",
};

const loginView = document.querySelector("#login-view");
const appView = document.querySelector("#app-view");
const toast = document.querySelector("#toast");
let currentPerson = null;
let refreshToastTimer = null;

function isAdmin() {
  return currentPerson?.is_admin === true;
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error-toast", isError);
  toast.hidden = false;
  window.clearTimeout(refreshToastTimer);
  refreshToastTimer = window.setTimeout(() => { toast.hidden = true; }, 4200);
}

function askConfirmation(title, message, acceptText = "Aceptar") {
  const modal = document.querySelector("#modal-confirmar");
  const accept = modal.querySelector('[data-action="aceptar-modal"]');
  const cancel = modal.querySelector('[data-action="cerrar-modal"]');
  modal.querySelector("#modal-confirmar-titulo").textContent = title;
  modal.querySelector("#modal-confirmar-mensaje").textContent = message;
  accept.textContent = acceptText;

  return new Promise((resolve) => {
    const finish = (confirmed) => {
      modal.hidden = true;
      accept.removeEventListener("click", onAccept);
      cancel.removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onKeyDown);
      resolve(confirmed);
    };
    const onAccept = () => finish(true);
    const onCancel = () => finish(false);
    const onKeyDown = (event) => {
      if (event.key === "Escape") finish(false);
    };
    accept.addEventListener("click", onAccept);
    cancel.addEventListener("click", onCancel);
    document.addEventListener("keydown", onKeyDown);
    modal.hidden = false;
    accept.focus();
  });
}

function askReason(title, message, acceptText) {
  const modal = document.querySelector("#modal-motivo");
  const textarea = modal.querySelector("#modal-motivo-texto");
  const accept = modal.querySelector('[data-action="aceptar-modal"]');
  const cancel = modal.querySelector('[data-action="cerrar-modal"]');
  modal.querySelector("#modal-motivo-titulo").textContent = title;
  modal.querySelector("#modal-motivo-mensaje").textContent = message;
  accept.textContent = acceptText;
  textarea.value = "";

  return new Promise((resolve) => {
    const finish = (reason) => {
      modal.hidden = true;
      accept.removeEventListener("click", onAccept);
      cancel.removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onKeyDown);
      resolve(reason);
    };
    const onAccept = () => {
      if (textarea.value.trim()) finish(textarea.value.trim());
      else textarea.reportValidity();
    };
    const onCancel = () => finish(null);
    const onKeyDown = (event) => {
      if (event.key === "Escape") finish(null);
    };
    accept.addEventListener("click", onAccept);
    cancel.addEventListener("click", onCancel);
    document.addEventListener("keydown", onKeyDown);
    modal.hidden = false;
    textarea.focus();
  });
}

function errorMessage(payload, fallback) {
  const detail = payload?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((entry) => entry.msg).join("; ");
  return fallback;
}

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = sessionStorage.getItem(tokenKey);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  let response;
  try {
    response = await fetch(`${API}${path}`, { ...options, headers });
  } catch {
    estadoConexion(false);
    throw new Error("No se pudo conectar con la API. Comprueba que Uvicorn siga funcionando y vuelve a intentar.");
  }
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) logout(false);
    if (response.status === 503) estadoConexion(false);
    throw new Error(errorMessage(payload, response.status >= 500 ? "La API no pudo completar la operación; revisa la terminal del servidor." : `La solicitud falló (${response.status})`));
  }
  return payload;
}

function setLoading(button, loading) {
  if (!button) return;
  if (loading) {
    button.dataset.previousText = button.textContent;
    button.disabled = true;
    button.textContent = "Procesando…";
  } else {
    button.disabled = false;
    if (button.dataset.previousText) button.textContent = button.dataset.previousText;
  }
}

function escapeForDisplay(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function makeCell(row, value) {
  const cell = document.createElement("td");
  cell.textContent = escapeForDisplay(value);
  row.append(cell);
  return cell;
}

function addBadge(cell, state) {
  const badge = document.createElement("span");
  badge.className = `badge ${stateClasses[state] || ""}`;
  badge.textContent = stateNames[state] || escapeForDisplay(state);
  cell.replaceChildren(badge);
}

function fillSelect(select, items, labelFor, placeholder) {
  if (!select) return;
  const previous = select.value;
  select.replaceChildren(new Option(placeholder, ""));
  for (const item of items) select.add(new Option(labelFor(item), item.id));
  if (items.some((item) => item.id === previous)) select.value = previous;
  select.disabled = items.length === 0;
}

function showDashboard(person) {
  currentPerson = person;
  loginView.hidden = true;
  appView.hidden = false;
  document.querySelector("#account-name").textContent = `${person.full_name} · ${roleNames[person.role] || person.role}`;
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.hidden = !isAdmin();
  });
  const requester = ["ESTUDIANTE", "DOCENTE"].includes(person.role);
  document.querySelectorAll(".requester-only").forEach((element) => {
    element.hidden = !requester;
  });
  document.querySelector("#reservations-heading").textContent = isAdmin() ? "Todas las reservas" : "Mis reservas";
  activateView("inventory-view", false);
  loadDashboard().catch((error) => showToast(error.message, true));
}

function showLogin(error = "") {
  currentPerson = null;
  appView.hidden = true;
  loginView.hidden = false;
  const message = document.querySelector("#login-error");
  message.textContent = error;
  message.hidden = !error;
  document.querySelectorAll(".modal").forEach((modal) => { modal.hidden = true; });
  document.querySelectorAll("tbody").forEach((body) => body.replaceChildren());
  modulos.limpiar();
}

async function logout(sendRequest = true) {
  if (sendRequest && sessionStorage.getItem(tokenKey)) {
    try { await request("/auth/logout", { method: "POST" }); } catch { /* Always clear local session. */ }
  }
  sessionStorage.removeItem(tokenKey);
  showLogin();
}

function activateView(viewId, cargar = true) {
  document.querySelectorAll(".page-view").forEach((view) => { view.hidden = view.id !== viewId; });
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });
  if (!cargar) return;
  if (viewId === "people-view") loadPeople().catch((error) => showToast(error.message, true));
  if (viewId === "reservations-view") loadReservations().catch((error) => showToast(error.message, true));
  if (viewId === "inventory-view") loadInventory().catch((error) => showToast(error.message, true));
  if (viewId === "policies-view") modulos.cargarPoliticas().catch((error) => showToast(error.message, true));
  if (viewId === "loans-view") loadReservations().then(() => modulos.cargarPrestamos()).catch((error) => showToast(error.message, true));
  if (viewId === "academic-view") modulos.cargarAcademico().catch((error) => showToast(error.message, true));
}

async function loadDashboard() {
  await loadInventory();
  await loadReservations();
  if (isAdmin()) await loadPeople();
  await modulos.cargarPoliticas();
  await modulos.cargarPrestamos();
  if (isAdmin()) await modulos.cargarAcademico();
}

let inventoryCache = { categories: [], types: [], items: [], units: [] };

async function loadInventory() {
  const [categories, types, items, units] = await Promise.all([
    request("/inventory/categories"), request("/inventory/types"),
    request("/inventory/items"), request("/inventory/units"),
  ]);
  inventoryCache = { categories, types, items, units };
  renderUnits(units, items, types);
  fillSelect(document.querySelector('#category-form [name="item_type_id"]'), types, (item) => item.name, "Selecciona tipo");
  fillSelect(document.querySelector('#item-form [name="category_id"]'), categories, (category) => {
    const type = types.find((item) => item.id === category.item_type_id);
    return `${category.name} · ${type?.name || "tipo"}`;
  }, "Selecciona categoría");
  const freeCards = items.filter((item) => !units.some((unit) => unit.item_card_id === item.id));
  fillSelect(document.querySelector('#unit-form [name="item_card_id"]'), freeCards, (item) => {
    const category = categories.find((entry) => entry.id === item.category_id);
    return `${item.name} · ${category?.name || "categoría"}`;
  }, "Selecciona ficha sin unidad");
  const availableUnits = units.filter((unit) => {
    if (unit.state !== "DISPONIBLE") return false;
    const item = items.find((entry) => entry.id === unit.item_card_id);
    if (!item || item.active === false) return false;
    const category = categories.find((entry) => entry.id === item.category_id);
    if (!category || category.active === false) return false;
    const type = types.find((entry) => entry.id === category.item_type_id);
    return Boolean(type && type.active !== false && type.lendable !== false);
  });
  fillSelect(document.querySelector('#reservation-form [name="unit_id"]'), availableUnits, (unit) => `${unit.inventory_code} · ${itemName(unit.item_card_id, items)}`, "Selecciona unidad");
}

function itemName(itemId, items = inventoryCache.items) {
  return items.find((item) => item.id === itemId)?.name || "Bien";
}

function renderUnits(units, items, types) {
  const body = document.querySelector("#units-table");
  body.replaceChildren();
  for (const unit of units) {
    const row = document.createElement("tr");
    makeCell(row, unit.inventory_code);
    const itemCell = makeCell(row, itemName(unit.item_card_id, items));
    const item = items.find((entry) => entry.id === unit.item_card_id);
    const type = types.find((entry) => entry.id === item?.item_type_id);
    itemCell.title = type?.name || "";
    makeCell(row, unit.location);
    makeCell(row, unit.condition);
    addBadge(makeCell(row, ""), unit.state);
    if (isAdmin()) {
      makeCell(row, unit.serial_number);
      makeCell(row, unit.acquisition_date);
    }
    body.append(row);
  }
  document.querySelector("#units-empty").hidden = units.length > 0;
}

function dateLabel(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : new Intl.DateTimeFormat("es-PE", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

async function loadReservations() {
  const reservations = await request("/reservations");
  modulos.actualizarReservas(reservations);
  const body = document.querySelector("#reservations-table");
  body.replaceChildren();
  for (const reservation of reservations) {
    const row = document.createElement("tr");
    const unit = inventoryCache.units.find((entry) => entry.id === reservation.unit_id);
    makeCell(row, unit?.inventory_code || reservation.unit_id);
    if (isAdmin()) makeCell(row, reservation.applicant_id);
    makeCell(row, dateLabel(reservation.starts_at));
    makeCell(row, dateLabel(reservation.ends_at));
    makeCell(row, reservation.intended_use);
    addBadge(makeCell(row, ""), reservation.state);
    if (isAdmin()) makeCell(row, reservation.decision_reason);
    const actions = document.createElement("td");
    if (isAdmin() && reservation.state === "PENDIENTE" && reservation.applicant_id !== currentPerson.applicant_id) {
      const accept = document.createElement("button");
      accept.className = "button small primary";
      accept.type = "button";
      accept.textContent = "Confirmar";
      accept.addEventListener("click", () => decideReservation(reservation.id, true));
      actions.append(accept, document.createTextNode(" "));
      const reject = document.createElement("button");
      reject.className = "button small danger";
      reject.type = "button";
      reject.textContent = "Rechazar";
      reject.addEventListener("click", () => decideReservation(reservation.id, false));
      actions.append(reject, document.createTextNode(" "));
    }
    if (["PENDIENTE", "CONFIRMADA"].includes(reservation.state) && (isAdmin() || new Date(reservation.starts_at) > new Date())) {
      const cancel = document.createElement("button");
      cancel.className = "button small quiet";
      cancel.type = "button";
      cancel.textContent = "Cancelar";
      cancel.addEventListener("click", () => cancelReservation(reservation.id));
      actions.append(cancel);
    }
    row.append(actions);
    body.append(row);
  }
  document.querySelector("#reservations-empty").hidden = reservations.length > 0;
}

async function loadPeople() {
  const people = await request("/people");
  const body = document.querySelector("#people-table");
  body.replaceChildren();
  for (const person of people) {
    const row = document.createElement("tr");
    makeCell(row, person.full_name);
    makeCell(row, person.institutional_email);
    makeCell(row, roleNames[person.role] || person.role);
    makeCell(row, person.cui || person.id);
    makeCell(row, person.is_admin ? "Sí" : "No");
    addBadge(makeCell(row, ""), person.state);
    const actions = document.createElement("td");
    if (person.state === "ACTIVA" && person.id !== currentPerson.id) {
      const deactivate = document.createElement("button");
      deactivate.className = "button small danger";
      deactivate.type = "button";
      deactivate.textContent = "Desactivar";
      deactivate.addEventListener("click", async () => {
        const confirmed = await askConfirmation(
          "Desactivar usuario",
          `¿Desactivar a ${person.full_name}? Ya no podrá iniciar sesión.`,
          "Desactivar",
        );
        if (!confirmed) return;
        try {
          await request(`/people/${person.id}/deactivate`, { method: "POST" });
          showToast("La persona fue desactivada.");
          await loadPeople();
        } catch (error) { showToast(error.message, true); }
      });
      actions.append(deactivate);
    }
    row.append(actions);
    body.append(row);
  }
  document.querySelector("#people-empty").hidden = people.length > 0;
}

async function submitJsonForm(form, path, convert, success, after) {
  const button = form.querySelector('button[type="submit"]');
  setLoading(button, true);
  try {
    await request(path, { method: "POST", body: JSON.stringify(convert(new FormData(form))) });
    form.reset();
    if (after) {
      try { await after(); }
      catch { showToast(`${success} No se pudo actualizar la vista; pulsa Actualizar.`, true); return; }
    }
    showToast(success);
  } catch (error) {
    showToast(error.message, true);
  } finally {
    setLoading(button, false);
  }
}

function values(formData) {
  return Object.fromEntries(formData.entries());
}

function requiredText(formData, key) {
  return String(formData.get(key) || "").trim();
}

async function decideReservation(reservationId, confirm) {
  const reason = confirm ? null : await askReason(
    "Rechazar reserva",
    "Indica el motivo que se guardará en la solicitud.",
    "Rechazar",
  );
  if (!confirm && !reason) return;
  try {
    await request(`/reservations/${reservationId}/decision`, {
      method: "POST", body: JSON.stringify({ confirm, reason: reason?.trim() || null }),
    });
    showToast(confirm ? "Reserva confirmada." : "Reserva rechazada.");
    await loadReservations();
    await loadInventory();
  } catch (error) { showToast(error.message, true); }
}

async function cancelReservation(reservationId) {
  const confirmed = await askConfirmation(
    "Cancelar reserva",
    "¿Deseas cancelar esta solicitud? Esta acción no se puede deshacer.",
    "Cancelar reserva",
  );
  if (!confirmed) return;
  const motivo = isAdmin()
    ? await askReason("Motivo de cancelación", "Indica por qué se cancela la reserva.", "Confirmar")
    : null;
  if (isAdmin() && !motivo) return;
  try {
    const consulta = motivo ? `?reason=${encodeURIComponent(motivo.trim())}` : "";
    await request(`/reservations/${reservationId}/cancel${consulta}`, { method: "POST" });
    showToast("Reserva cancelada.");
    await loadReservations();
    await loadInventory();
  } catch (error) { showToast(error.message, true); }
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const button = form.querySelector('button[type="submit"]');
  setLoading(button, true);
  try {
    const body = new URLSearchParams(new FormData(form));
    const payload = await request("/auth/token", { method: "POST", body, headers: { "Content-Type": "application/x-www-form-urlencoded" } });
    sessionStorage.setItem(tokenKey, payload.access_token);
    form.reset();
    const person = await request("/me");
    showDashboard(person);
  } catch (error) {
    sessionStorage.removeItem(tokenKey);
    showLogin(error.message);
  } finally { setLoading(button, false); }
});

document.querySelector("#logout-button").addEventListener("click", () => logout());
document.querySelectorAll(".nav-link").forEach((button) => {
  button.addEventListener("click", () => activateView(button.dataset.view));
});
document.querySelectorAll(".refresh-button").forEach((button) => {
  button.addEventListener("click", () => loadDashboard().then(() => showToast("Información actualizada.")).catch((error) => showToast(error.message, true)));
});

document.querySelector("#category-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/categories", (data) => ({ item_type_id: data.get("item_type_id"), name: requiredText(data, "name"), description: requiredText(data, "description") || null }), "Categoría creada.", loadInventory);
});
document.querySelector("#type-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/types", (data) => ({ name: requiredText(data, "name"), lendable: data.get("lendable") === "on" }), "Tipo de bien creado.", loadInventory);
});
document.querySelector("#item-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/items", (data) => {
    const attributes = {};
    for (const line of requiredText(data, "caracteristicas").split("\n").filter((value) => value.trim())) {
      const separator = line.indexOf(":");
      const name = line.slice(0, separator).trim();
      const value = line.slice(separator + 1).trim();
      if (separator < 1 || !value || Object.hasOwn(attributes, name)) {
        throw new Error("Cada característica debe tener nombre y valor separados por dos puntos, sin nombres repetidos.");
      }
      Object.defineProperty(attributes, name, { value, enumerable: true });
    }
    return { category_id: data.get("category_id"), name: requiredText(data, "name"), description: requiredText(data, "description") || null, attributes };
  }, "Ficha creada.", loadInventory);
});
document.querySelector("#unit-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/units", (data) => ({
    item_card_id: data.get("item_card_id"), inventory_code: requiredText(data, "inventory_code"),
    serial_number: requiredText(data, "serial_number"), location: requiredText(data, "location"),
    acquisition_date: data.get("acquisition_date") || null,
    custody: requiredText(data, "custody"), condition: requiredText(data, "condition"),
    accessories: requiredText(data, "accessories").split(",").map((part) => part.trim()).filter(Boolean),
  }), "Unidad registrada.", loadInventory);
});

document.querySelector('#person-form [name="role"]').addEventListener("change", (event) => {
  const rol = event.target.value;
  const configurar = (selector, visible, requeridos = []) => {
    document.querySelectorAll(selector).forEach((field) => {
      field.hidden = !visible;
      const control = field.querySelector("input, select");
      if (!control) return;
      control.disabled = !visible;
      control.required = visible && requeridos.includes(control.name);
    });
  };
  configurar(".student-field", rol === "ESTUDIANTE", ["cui", "student_code", "program", "semester"]);
  configurar(".teacher-field", rol === "DOCENTE", ["teacher_code", "specialty"]);
  configurar(".staff-field", rol === "PERSONAL_ADMINISTRATIVO");
  configurar(".employee-field", rol !== "ESTUDIANTE", ["department", "position"]);
  const posicion = document.querySelector('#person-form [name="position"]');
  const cargoActual = posicion.value.trim();
  if (rol === "DOCENTE" && (!cargoActual || cargoActual === "Personal EPCC")) posicion.value = "Docente";
  if (rol === "PERSONAL_ADMINISTRATIVO" && (!cargoActual || cargoActual === "Docente")) posicion.value = "Personal EPCC";
  const departamento = document.querySelector('#person-form [name="department"]');
  if (!departamento.value.trim()) departamento.value = "EPCC";
  document.querySelectorAll(".admin-attribution-field").forEach((field) => {
    field.hidden = rol === "ESTUDIANTE";
    field.querySelector("input").disabled = rol === "ESTUDIANTE";
  });
  if (event.target.value === "ESTUDIANTE") document.querySelector('[name="is_admin"]').checked = false;
});
document.querySelector('#person-form [name="role"]').dispatchEvent(new Event("change"));
document.querySelector("#person-form").addEventListener("reset", () => {
  queueMicrotask(() => document.querySelector('#person-form [name="role"]').dispatchEvent(new Event("change")));
});
document.querySelector("#person-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const selectedRole = form.elements.role.value;
  submitJsonForm(form, "/people", (data) => {
    const person = values(data);
    // Los campos de perfil deshabilitados no viajan en FormData.
    person.cui = (person.cui ?? "").trim() || null;
    person.first_names = person.first_names.trim();
    person.last_names = person.last_names.trim();
    person.end_date = person.end_date || null;
    if (person.end_date && person.end_date <= person.start_date) throw new Error("La fecha de fin debe ser posterior a la fecha de inicio, o quedar vacía.");
    person.is_admin = selectedRole !== "ESTUDIANTE" && data.get("is_admin") === "on";
    person.start_date = person.start_date || new Date().toLocaleDateString("sv-SE");
    person.semester = person.semester ? Number(person.semester) : null;
    for (const field of ["student_code", "program", "teacher_code", "specialty"]) person[field] ||= null;
    return person;
  }, "Usuario creado.", loadPeople);
});
document.querySelector("#reservation-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/reservations", (data) => ({
    unit_id: data.get("unit_id"),
    starts_at: new Date(data.get("starts_at")).toISOString(),
    ends_at: validarIntervalo(data.get("starts_at"), data.get("ends_at")),
    intended_use: requiredText(data, "intended_use"),
  }), "Solicitud de reserva enviada.", async () => {
    await loadInventory();
    await loadReservations();
  });
});

function validarIntervalo(desde, hasta) {
  if (new Date(desde) <= new Date() || new Date(hasta) <= new Date(desde)) {
    throw new Error("La reserva debe comenzar en el futuro y terminar después de su inicio.");
  }
  const maximo = currentPerson?.role === "DOCENTE" ? 7 : 3;
  if (new Date(hasta) - new Date(desde) > maximo * 86400000) throw new Error(`La duración máxima es ${maximo} días corridos.`);
  return new Date(hasta).toISOString();
}

function estadoConexion(disponible) {
  document.querySelector("#api-status").textContent = disponible ? "API disponible" : "API sin conexión";
  document.querySelector("#api-status-dot").classList.toggle("offline", !disponible);
}

async function verificarConexion() {
  try {
    const respuesta = await fetch("/health/ready", { signal: AbortSignal.timeout(5000) });
    const datos = await respuesta.json();
    estadoConexion(respuesta.ok && datos.status === "ready");
  } catch { estadoConexion(false); }
}

const modulos = crearModulos({ request, showToast, submitJsonForm, fillSelect, makeCell,
  dateLabel, isAdmin, getCatalogo: () => inventoryCache, refrescar: loadDashboard });
verificarConexion();
window.setInterval(verificarConexion, 15000);
window.addEventListener("offline", () => estadoConexion(false));
window.addEventListener("online", verificarConexion);

const savedToken = sessionStorage.getItem(tokenKey);
if (savedToken) {
  request("/me").then(showDashboard).catch(() => logout(false));
}
