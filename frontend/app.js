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
  ACTIVA: "Activa",
  INACTIVA: "Inactiva",
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
};

const loginView = document.querySelector("#login-view");
const appView = document.querySelector("#app-view");
const toast = document.querySelector("#toast");
let currentPerson = null;
let refreshToastTimer = null;

function isAdmin() {
  return currentPerson?.role === "ADMIN_INVENTARIO";
}

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.toggle("error-toast", isError);
  toast.hidden = false;
  window.clearTimeout(refreshToastTimer);
  refreshToastTimer = window.setTimeout(() => { toast.hidden = true; }, 4200);
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
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && token) logout(false);
    throw new Error(errorMessage(payload, `La solicitud falló (${response.status})`));
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
  loadDashboard().catch((error) => showToast(error.message, true));
}

function showLogin(error = "") {
  currentPerson = null;
  appView.hidden = true;
  loginView.hidden = false;
  const message = document.querySelector("#login-error");
  message.textContent = error;
  message.hidden = !error;
}

async function logout(sendRequest = true) {
  if (sendRequest && sessionStorage.getItem(tokenKey)) {
    try { await request("/auth/logout", { method: "POST" }); } catch { /* Always clear local session. */ }
  }
  sessionStorage.removeItem(tokenKey);
  showLogin();
}

function activateView(viewId) {
  document.querySelectorAll(".page-view").forEach((view) => { view.hidden = view.id !== viewId; });
  document.querySelectorAll(".nav-link").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === viewId);
  });
  if (viewId === "people-view") loadPeople().catch((error) => showToast(error.message, true));
  if (viewId === "reservations-view") loadReservations().catch((error) => showToast(error.message, true));
  if (viewId === "inventory-view") loadInventory().catch((error) => showToast(error.message, true));
}

async function loadDashboard() {
  await loadInventory();
  await loadReservations();
  if (isAdmin()) await loadPeople();
}

let inventoryCache = { categories: [], types: [], items: [], units: [] };

async function loadInventory() {
  const [categories, types, items, units] = await Promise.all([
    request("/inventory/categories"), request("/inventory/types"),
    request("/inventory/items"), request("/inventory/units"),
  ]);
  inventoryCache = { categories, types, items, units };
  renderUnits(units, items, types);
  fillSelect(document.querySelector('#type-form [name="category_id"]'), categories, (item) => item.name, "Selecciona categoría");
  fillSelect(document.querySelector('#item-form [name="item_type_id"]'), types, (item) => item.name, "Selecciona tipo");
  fillSelect(document.querySelector('#unit-form [name="item_card_id"]'), items, (item) => item.name, "Selecciona ficha");
  const availableUnits = units.filter((unit) => unit.state === "DISPONIBLE");
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
  const body = document.querySelector("#reservations-table");
  body.replaceChildren();
  for (const reservation of reservations) {
    const row = document.createElement("tr");
    const unit = inventoryCache.units.find((entry) => entry.id === reservation.unit_id);
    makeCell(row, unit?.inventory_code || reservation.unit_id.slice(0, 8));
    makeCell(row, dateLabel(reservation.starts_at));
    makeCell(row, dateLabel(reservation.ends_at));
    makeCell(row, reservation.intended_use);
    addBadge(makeCell(row, ""), reservation.state);
    const actions = document.createElement("td");
    if (isAdmin() && reservation.state === "PENDIENTE") {
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
    if (["PENDIENTE", "CONFIRMADA"].includes(reservation.state)) {
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
    addBadge(makeCell(row, ""), person.state);
    const actions = document.createElement("td");
    if (person.state === "ACTIVA" && person.id !== currentPerson.id) {
      const deactivate = document.createElement("button");
      deactivate.className = "button small danger";
      deactivate.type = "button";
      deactivate.textContent = "Desactivar";
      deactivate.addEventListener("click", async () => {
        if (!window.confirm(`¿Desactivar a ${person.full_name}?`)) return;
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
    if (after) await after();
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
  const reason = confirm ? null : window.prompt("Indica el motivo del rechazo:");
  if (!confirm && !reason?.trim()) return;
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
  if (!window.confirm("¿Cancelar esta reserva?")) return;
  try {
    await request(`/reservations/${reservationId}/cancel`, { method: "POST" });
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
    const response = await fetch("/auth/token", { method: "POST", body });
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(errorMessage(payload, "No fue posible iniciar sesión."));
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
  submitJsonForm(form, "/inventory/categories", (data) => ({ name: requiredText(data, "name"), description: requiredText(data, "description") || null }), "Categoría creada.", loadInventory);
});
document.querySelector("#type-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/types", (data) => ({ name: requiredText(data, "name"), category_id: data.get("category_id"), lendable: data.get("lendable") === "on" }), "Tipo de bien creado.", loadInventory);
});
document.querySelector("#item-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/items", (data) => ({ item_type_id: data.get("item_type_id"), name: requiredText(data, "name"), description: requiredText(data, "description") || null, attributes: {} }), "Ficha creada.", loadInventory);
});
document.querySelector("#unit-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/inventory/units", (data) => ({
    item_card_id: data.get("item_card_id"), inventory_code: requiredText(data, "inventory_code"),
    serial_number: requiredText(data, "serial_number") || null, location: requiredText(data, "location"),
    custody: requiredText(data, "custody"), condition: requiredText(data, "condition"),
    accessories: requiredText(data, "accessories").split(",").map((part) => part.trim()).filter(Boolean),
  }), "Unidad registrada.", loadInventory);
});

document.querySelector('#person-form [name="role"]').addEventListener("change", (event) => {
  document.querySelectorAll(".student-field").forEach((field) => { field.hidden = event.target.value !== "ESTUDIANTE"; });
  document.querySelectorAll(".teacher-field").forEach((field) => { field.hidden = event.target.value !== "DOCENTE"; });
});
document.querySelector('#person-form [name="role"]').dispatchEvent(new Event("change"));
document.querySelector("#person-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const selectedRole = form.elements.role.value;
  submitJsonForm(form, "/people", (data) => {
    const person = values(data);
    person.cui = person.cui.trim();
    person.full_name = person.full_name.trim();
    person.start_date = person.start_date || new Date().toISOString().slice(0, 10);
    person.semester = person.semester ? Number(person.semester) : null;
    for (const field of ["student_code", "program", "teacher_code", "specialty"]) person[field] ||= null;
    if (selectedRole !== "ESTUDIANTE") { person.student_code = null; person.program = null; person.semester = null; }
    if (selectedRole !== "DOCENTE") { person.teacher_code = null; person.specialty = null; }
    return person;
  }, "Usuario creado.", loadPeople);
});
document.querySelector("#reservation-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  submitJsonForm(form, "/reservations", (data) => ({
    unit_id: data.get("unit_id"),
    starts_at: new Date(data.get("starts_at")).toISOString(),
    ends_at: new Date(data.get("ends_at")).toISOString(),
    intended_use: requiredText(data, "intended_use"),
  }), "Solicitud de reserva enviada.", async () => {
    await loadInventory();
    await loadReservations();
  });
});

const savedToken = sessionStorage.getItem(tokenKey);
if (savedToken) {
  request("/me").then(showDashboard).catch(() => logout(false));
}
