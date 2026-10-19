import { compareLeads, scoreLead } from "./lead-score.js";

const TOKEN_KEY = "autoservice-admin-token";

const authView = document.querySelector("#auth-view");
const panelView = document.querySelector("#panel-view");
const authForm = document.querySelector("#auth-form");
const authStatus = document.querySelector("#auth-status");
const authTitle = document.querySelector("#auth-title");
const authLede = document.querySelector("#auth-lede");
const authSubmit = document.querySelector("#auth-submit");
const authRegister = document.querySelector("#auth-register");
const panelStatus = document.querySelector("#panel-status");
const adminHello = document.querySelector("#admin-hello");
const logoutBtn = document.querySelector("#logout-btn");
const serviceForm = document.querySelector("#service-form");
const serviceSubmit = document.querySelector("#service-submit");
const serviceCancel = document.querySelector("#service-cancel");
const serviceMode = document.querySelector("#service-mode");
const servicesList = document.querySelector("#services-list");
const statsCards = document.querySelector("#stats-cards");
const leadsBody = document.querySelector("#leads-body");
const leadDetail = document.querySelector("#lead-detail");
const heatmapCanvas = document.querySelector("#heatmap-canvas");
const heatmapCount = document.querySelector("#heatmap-count");
const heatmapRefresh = document.querySelector("#heatmap-refresh");

let registrationOpen = false;
let authMode = "login";
let currentAdmin = null;
let editingService = null;

function token() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  if (value) localStorage.setItem(TOKEN_KEY, value);
  else localStorage.removeItem(TOKEN_KEY);
}

function showMessage(node, message, isError) {
  node.hidden = false;
  node.textContent = message;
  node.classList.toggle("is-error", Boolean(isError));
}

function hideMessage(node) {
  node.hidden = true;
  node.textContent = "";
}

function errorText(payload) {
  if (!payload) return "Запрос не выполнен";
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
  }
  return "Запрос не выполнен";
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const auth = token();
  if (auth) headers.Authorization = `Bearer ${auth}`;
  const response = await fetch(`/api${path}`, { ...options, headers });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorText(body));
    error.status = response.status;
    error.payload = body;
    throw error;
  }
  return body;
}

function money(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value || "—");
  return `${new Intl.NumberFormat("ru-RU").format(number)} ₽`;
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ru-RU");
}

function paintAuthMode() {
  if (authMode === "register") {
    authTitle.textContent = "Регистрация";
    authLede.textContent = "Создайте первого администратора. После этого регистрация закроется.";
    authSubmit.textContent = "Создать администратора";
    authRegister.hidden = true;
  } else {
    authTitle.textContent = "Вход";
    authLede.textContent = "Войдите, чтобы управлять услугами и смотреть заявки.";
    authSubmit.textContent = "Войти";
    authRegister.hidden = !registrationOpen;
  }
}

function showAuth() {
  authView.hidden = false;
  panelView.hidden = true;
  paintAuthMode();
}

function showPanel() {
  authView.hidden = true;
  panelView.hidden = false;
  adminHello.textContent = currentAdmin
    ? `Вы вошли как ${currentAdmin.login}.`
    : "Сессия активна.";
}

function markInvalid(field, invalid) {
  field.classList.toggle("is-invalid", invalid);
}

function validateForm(form) {
  let valid = true;
  form.querySelectorAll(".field").forEach((field) => {
    const control = field.querySelector("input, textarea, select");
    if (!control || control.type === "range") return;
    const empty = control.required && !String(control.value || "").trim();
    markInvalid(field, empty);
    if (empty) valid = false;
  });
  return valid;
}

async function loadAuthStatus() {
  const status = await api("/auth/status");
  registrationOpen = Boolean(status.registration_open);
  paintAuthMode();
  return status;
}

async function bootstrap() {
  try {
    await loadAuthStatus();
  } catch {
    registrationOpen = false;
  }

  if (!token()) {
    showAuth();
    return;
  }

  try {
    currentAdmin = await api("/auth/me");
    showPanel();
    await refreshActiveTab();
  } catch {
    setToken("");
    currentAdmin = null;
    showAuth();
  }
}

authRegister.addEventListener("click", () => {
  authMode = "register";
  hideMessage(authStatus);
  paintAuthMode();
});

authForm.addEventListener("input", (event) => {
  const field = event.target.closest(".field");
  if (field) markInvalid(field, false);
});

authForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateForm(authForm)) {
    showMessage(authStatus, "Заполните логин и пароль.", true);
    return;
  }
  const login = String(authForm.login.value || "").trim();
  const password = String(authForm.password.value || "");
  authSubmit.disabled = true;
  try {
    const path = authMode === "register" ? "/auth/register" : "/auth/login";
    const result = await api(path, {
      method: "POST",
      body: JSON.stringify({ login, password }),
    });
    setToken(result.access_token);
    currentAdmin = result.admin;
    registrationOpen = false;
    authForm.reset();
    hideMessage(authStatus);
    showPanel();
    await refreshActiveTab();
  } catch (error) {
    showMessage(authStatus, error.message, true);
    if (error.status === 403) {
      registrationOpen = false;
      authMode = "login";
      paintAuthMode();
    }
  } finally {
    authSubmit.disabled = false;
  }
});

logoutBtn.addEventListener("click", () => {
  setToken("");
  currentAdmin = null;
  authMode = "login";
  hideMessage(panelStatus);
  showAuth();
  loadAuthStatus().catch(() => {});
});

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", async () => {
    document.querySelectorAll(".tab").forEach((node) => {
      node.classList.toggle("is-active", node === tab);
    });
    document.querySelectorAll(".tab-panel").forEach((panel) => {
      panel.hidden = panel.id !== `tab-${tab.dataset.tab}`;
    });
    await refreshActiveTab();
  });
});

function activeTab() {
  return document.querySelector(".tab.is-active")?.dataset.tab || "services";
}

async function refreshActiveTab() {
  const tab = activeTab();
  hideMessage(panelStatus);
  if (tab === "services") await loadServices();
  if (tab === "stats") await loadStats();
  if (tab === "heatmap") await loadHeatmap();
}

function defaultBudget() {
  serviceForm.budget_min.value = "10000";
  serviceForm.budget_max.value = "100000";
  serviceForm.budget_step.value = "2000";
}

function resetServiceForm() {
  editingService = null;
  serviceForm.reset();
  defaultBudget();
  serviceSubmit.textContent = "Добавить услугу";
  serviceCancel.hidden = true;
  serviceMode.hidden = true;
  serviceMode.textContent = "";
}

function beginEdit(item, index) {
  const service = item.services[index];
  editingService = {
    id: item.id,
    index,
    services: (item.services || []).map((entry) => ({
      name: entry.name,
      description: entry.description || null,
    })),
  };
  serviceForm.name.value = service.name || "";
  serviceForm.description.value = service.description || "";
  serviceForm.budget_min.value = String(item.budget_min);
  serviceForm.budget_max.value = String(item.budget_max);
  serviceForm.budget_step.value = String(item.budget_step);
  serviceSubmit.textContent = "Сохранить";
  serviceCancel.hidden = false;
  serviceMode.hidden = false;
  serviceMode.textContent = `Редактирование: ${service.name || "без названия"}`;
  serviceForm.querySelectorAll(".field").forEach((field) => markInvalid(field, false));
  hideMessage(panelStatus);
  serviceForm.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadServices() {
  const page = await api("/admin-data?limit=200");
  const items = Array.isArray(page.items) ? page.items : [];
  servicesList.replaceChildren();
  if (!items.length) {
    const empty = document.createElement("li");
    empty.textContent = "Услуг пока нет.";
    servicesList.append(empty);
    return;
  }
  for (const item of items) {
    (item.services || []).forEach((service, index) => {
      const li = document.createElement("li");
      if (editingService?.id === item.id && editingService.index === index) {
        li.classList.add("is-editing");
      }
      const text = document.createElement("div");
      const title = document.createElement("h3");
      title.textContent = service.name || "Без названия";
      const meta = document.createElement("p");
      meta.textContent = [
        service.description || "Без описания",
        `бюджет ${money(item.budget_min)} — ${money(item.budget_max)}`,
        `шаг ${money(item.budget_step)}`,
        `набор #${item.id}`,
      ].join(" · ");
      text.append(title, meta);
      const actions = document.createElement("div");
      actions.className = "row-actions";
      const edit = document.createElement("button");
      edit.type = "button";
      edit.className = "ghost";
      edit.textContent = "Изменить";
      edit.addEventListener("click", () => {
        beginEdit(item, index);
        loadServices().catch((error) => showMessage(panelStatus, error.message, true));
      });
      const remove = document.createElement("button");
      remove.type = "button";
      remove.className = "ghost";
      remove.textContent = "Удалить набор";
      remove.addEventListener("click", async () => {
        try {
          await api(`/admin-data/${item.id}`, { method: "DELETE" });
          if (editingService?.id === item.id) resetServiceForm();
          await loadServices();
        } catch (error) {
          showMessage(panelStatus, error.message, true);
        }
      });
      actions.append(edit, remove);
      li.append(text, actions);
      servicesList.append(li);
    });
  }
}

serviceForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validateForm(serviceForm)) {
    showMessage(panelStatus, "Заполните обязательные поля услуги.", true);
    return;
  }
  const name = String(serviceForm.name.value || "").trim();
  const description = String(serviceForm.description.value || "").trim() || null;
  const budgetMin = Number(serviceForm.budget_min.value);
  const budgetMax = Number(serviceForm.budget_max.value);
  const budgetStep = Number(serviceForm.budget_step.value);
  if (!(budgetMax >= budgetMin) || !(budgetStep > 0)) {
    showMessage(panelStatus, "Проверьте диапазон и шаг бюджета.", true);
    return;
  }
  const payload = {
    budget_min: budgetMin,
    budget_max: budgetMax,
    budget_step: budgetStep,
  };
  serviceSubmit.disabled = true;
  try {
    if (editingService) {
      payload.services = editingService.services.map((service, index) =>
        index === editingService.index ? { name, description } : service,
      );
      await api(`/admin-data/${editingService.id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });
      resetServiceForm();
      showMessage(panelStatus, "Услуга сохранена.", false);
    } else {
      payload.services = [{ name, description }];
      await api("/admin-data", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      resetServiceForm();
      showMessage(panelStatus, "Услуга добавлена.", false);
    }
    await loadServices();
  } catch (error) {
    showMessage(panelStatus, error.message, true);
  } finally {
    serviceSubmit.disabled = false;
  }
});

serviceCancel.addEventListener("click", () => {
  resetServiceForm();
  hideMessage(panelStatus);
  loadServices().catch((error) => showMessage(panelStatus, error.message, true));
});

function contactHref(lead) {
  const source = String(lead.contact_method || "");
  const email = source.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
  if (email) return `mailto:${email[0]}`;
  const digits = source.replace(/\D/g, "");
  if (digits.length >= 10) {
    const normalized = source.trim().startsWith("+") ? `+${digits}` : digits;
    return `tel:${normalized}`;
  }
  const telegram = source.trim();
  if (telegram.startsWith("@")) return `https://t.me/${telegram.slice(1)}`;
  return "";
}

function personName(lead) {
  return [lead.last_name, lead.first_name, lead.middle_name].filter(Boolean).join(" ") || "—";
}

function renderLeadDetail(lead) {
  const priority = lead.priority;
  leadDetail.hidden = false;
  leadDetail.replaceChildren();
  const header = document.createElement("header");
  const title = document.createElement("h3");
  title.textContent = personName(lead);
  const close = document.createElement("button");
  close.type = "button";
  close.className = "ghost";
  close.textContent = "Закрыть";
  close.addEventListener("click", () => {
    leadDetail.hidden = true;
    leadDetail.replaceChildren();
  });
  header.append(title, close);

  const summary = document.createElement("p");
  summary.className = "lede";
  summary.textContent = `${priority.explanation} ${priority.worth}.`;

  const grid = document.createElement("div");
  grid.className = "detail-grid";
  const fields = [
    ["Отдел", priority.department],
    ["Персональный менеджер", priority.manager ? "Нужен" : "Не обязателен"],
    ["Стоит ли тратить время", priority.worth],
    ["Роль", lead.role || "—"],
    ["Ниша", lead.business_niche || "—"],
    ["О бизнесе", lead.business_info || "—"],
    ["Размер компании", lead.company_size || "—"],
    ["Размер бизнеса", lead.business_size || "—"],
    ["Услуга", lead.product_interest || "—"],
    ["Тип задачи", lead.task_type || "—"],
    ["Объём задачи", lead.task_volume || "—"],
    ["Объём потребности", lead.need_volume || "—"],
    ["Бюджет", money(lead.budget)],
    ["Срок", lead.deadline || "—"],
    ["Способ связи", lead.contact_method || "—"],
    ["Удобное время", lead.convenient_time || "—"],
    ["Комментарий", lead.comment || "—"],
    ["Создана", formatDate(lead.created_at)],
  ];
  for (const [label, value] of fields) {
    const block = document.createElement("div");
    const span = document.createElement("span");
    span.textContent = label;
    const strong = document.createElement("strong");
    strong.textContent = value;
    block.append(span, strong);
    grid.append(block);
  }

  const actions = document.createElement("div");
  actions.className = "submit-row";
  const href = contactHref(lead);
  if (href) {
    const link = document.createElement("a");
    link.className = "lead-open";
    link.href = href;
    link.textContent = "Связаться";
    if (href.startsWith("http")) {
      link.target = "_blank";
      link.rel = "noreferrer";
    }
    actions.append(link);
  }

  leadDetail.append(header, summary, grid, actions);
  leadDetail.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

async function loadStats() {
  const page = await api("/leads?limit=200");
  const items = (Array.isArray(page.items) ? page.items : []).map((lead) => ({
    ...lead,
    priority: scoreLead(lead),
  }));
  items.sort(compareLeads);
  const total = Number(page.total) || items.length;
  const hot = items.filter((lead) => lead.priority.band === "hot").length;
  const warm = items.filter((lead) => lead.priority.band === "warm").length;
  const cold = items.filter((lead) => lead.priority.band === "cold").length;
  const budgets = items.map((lead) => Number(String(lead.budget).replace(/[^\d]/g, ""))).filter(Boolean);
  const average = budgets.length
    ? money(Math.round(budgets.reduce((sum, value) => sum + value, 0) / budgets.length))
    : "—";
  statsCards.replaceChildren(
    statCard("Заявок", String(total)),
    statCard("Срочные", String(hot)),
    statCard("Средние", String(warm)),
    statCard("Холодные", String(cold)),
    statCard("Средний бюджет", average),
  );

  leadsBody.replaceChildren();
  if (!items.length) {
    leadDetail.hidden = true;
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 9;
    cell.textContent = "Заявок пока нет.";
    row.append(cell);
    leadsBody.append(row);
    return;
  }
  items.forEach((lead) => {
    const row = document.createElement("tr");
    const badgeCell = document.createElement("td");
    badgeCell.append(temperatureMark(lead.priority));
    const whyCell = document.createElement("td");
    whyCell.className = "why-cell";
    whyCell.textContent = lead.priority.explanation;
    const values = [
      personName(lead),
      lead.product_interest || "—",
      money(lead.budget),
      lead.deadline || "—",
      lead.priority.department,
      lead.priority.manager ? "Нужен" : "Нет",
    ];
    row.append(badgeCell, whyCell);
    for (const value of values) {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      row.append(cell);
    }
    const actionCell = document.createElement("td");
    const open = document.createElement("button");
    open.type = "button";
    open.className = "ghost lead-open";
    open.textContent = "Открыть";
    open.addEventListener("click", () => renderLeadDetail(lead));
    actionCell.append(open);
    row.append(actionCell);
    leadsBody.append(row);
  });
}

function flameIcon(on) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 16 20");
  svg.setAttribute("aria-hidden", "true");
  svg.classList.add("flame", on ? "is-on" : "is-off");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute(
    "d",
    "M8.2 0.8c.3 2.2-.6 3.6-1.6 4.8C5.2 7.2 4 8.8 4 11.2 4 14.2 6.2 16.6 9 16.6s5-2.4 5-5.4c0-2.2-1-3.8-2.2-5.2-.4 1.3-1.1 2.1-1.9 2.1-.2-1.8-.8-3.6-1.7-7.3z",
  );
  svg.append(path);
  return svg;
}

function temperatureMark(priority) {
  const wrap = document.createElement("span");
  wrap.className = `temp temp-${priority.band}`;
  const marks = document.createElement("span");
  marks.className = "temp-marks";
  for (let index = 1; index <= 3; index += 1) {
    marks.append(flameIcon(index <= priority.marks));
  }
  const label = document.createElement("span");
  label.textContent = priority.label;
  wrap.append(marks, label);
  wrap.title = `${priority.label}, ${priority.score} из 100`;
  return wrap;
}

function statCard(label, value) {
  const card = document.createElement("div");
  card.className = "stat-card";
  const span = document.createElement("span");
  span.textContent = label;
  const strong = document.createElement("strong");
  strong.textContent = value;
  if (String(value).length > 12) strong.style.fontSize = "22px";
  card.append(span, strong);
  return card;
}

function pushPoint(points, x, y) {
  if (!Number.isFinite(x) || !Number.isFinite(y)) return;
  points.push({ x, y });
}

async function loadHeatmap() {
  const [page, visits] = await Promise.all([
    api("/lead-metrics?limit=200"),
    api("/lead-metrics/visits?limit=500"),
  ]);
  const items = Array.isArray(page.items) ? page.items : [];
  const points = [];
  for (const item of items) {
    for (const point of item.cursor_hotspots || []) {
      pushPoint(points, Number(point?.x), Number(point?.y));
    }
  }
  for (const visit of visits.items || []) {
    for (const pair of String(visit.cursor_positions || "").split(";")) {
      const [x, y] = pair.split(",").map((part) => Number(part.trim()));
      pushPoint(points, x, y);
    }
  }
  heatmapCount.textContent = `Точек: ${points.length}`;
  drawHeatmap(points);
}

function drawHeatmap(points) {
  const ctx = heatmapCanvas.getContext("2d");
  const width = heatmapCanvas.width;
  const height = heatmapCanvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "rgba(18, 16, 14, 0.92)";
  ctx.fillRect(0, 0, width, height);

  if (!points.length) {
    ctx.fillStyle = "rgba(182, 170, 152, 0.9)";
    ctx.font = "16px Manrope, sans-serif";
    ctx.fillText("Пока нет данных курсора.", 28, 40);
    return;
  }

  const maxX = Math.max(...points.map((point) => point.x), width);
  const maxY = Math.max(...points.map((point) => point.y), height);
  for (const point of points) {
    const x = (point.x / maxX) * width;
    const y = (point.y / maxY) * height;
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, 28);
    gradient.addColorStop(0, "rgba(246, 210, 120, 0.55)");
    gradient.addColorStop(0.45, "rgba(198, 161, 91, 0.22)");
    gradient.addColorStop(1, "rgba(198, 161, 91, 0)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, 28, 0, Math.PI * 2);
    ctx.fill();
  }
}

heatmapRefresh.addEventListener("click", () => {
  loadHeatmap().catch((error) => showMessage(panelStatus, error.message, true));
});

bootstrap().catch((error) => {
  showAuth();
  showMessage(authStatus, error.message || "Не удалось открыть панель", true);
});
