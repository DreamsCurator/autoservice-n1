const form = document.querySelector("#lead-form");
const statusNode = document.querySelector("#form-status");
const budgetInput = document.querySelector("#budget");
const budgetValue = document.querySelector("#budget-value");
const productSelect = form.elements.product_interest;
const serviceNote = document.querySelector("#service-note");
const startedAt = performance.now();
const clicks = [];
const hotspots = [];
let services = [];
let adminSnapshot = null;

const returnCount = rememberVisit();

function rememberVisit() {
  const storageKey = "autoservice-returns";
  const sessionKey = "autoservice-seen";
  const stored = localStorage.getItem(storageKey);
  let count = Number(stored || "0");
  if (!sessionStorage.getItem(sessionKey)) {
    if (stored !== null) count += 1;
    localStorage.setItem(storageKey, String(count));
    sessionStorage.setItem(sessionKey, "1");
  }
  return Number.isFinite(count) ? count : 0;
}

function money(value) {
  return `${new Intl.NumberFormat("ru-RU").format(Number(value))} ₽`;
}

function paintBudget() {
  budgetValue.textContent = money(budgetInput.value);
}

function textOf(name) {
  return String(form.elements[name].value || "").trim();
}

function optionalText(name) {
  const value = textOf(name);
  return value || null;
}

function applyServices(nextServices) {
  services = nextServices.filter((item) => item && item.name);
  if (!services.length) {
    productSelect.replaceChildren();
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "Услуги пока не заданы";
    productSelect.append(empty);
    serviceNote.textContent = "";
    return;
  }
  const current = productSelect.value;
  productSelect.replaceChildren(
    ...services.map((service) => {
      const option = document.createElement("option");
      option.value = service.name;
      option.textContent = service.name;
      return option;
    }),
  );
  const known = services.some((service) => service.name === current);
  productSelect.value = known ? current : services[0].name;
  [...productSelect.options].forEach((option) => {
    option.defaultSelected = option.value === productSelect.value;
  });
  paintServiceNote();
}

function paintServiceNote() {
  const service = services.find((item) => item.name === productSelect.value);
  serviceNote.textContent = service?.description || "";
}

function applyAdmin(data) {
  adminSnapshot = data;
  if (Array.isArray(data.services)) applyServices(data.services);
  const min = Number(data.budget_min);
  const max = Number(data.budget_max);
  const step = Number(data.budget_step);
  if (Number.isFinite(min) && Number.isFinite(max) && max >= min && step > 0) {
    budgetInput.min = String(min);
    budgetInput.max = String(max);
    budgetInput.step = String(step);
    const middle = min + Math.round((max - min) / 2 / step) * step;
    budgetInput.value = String(Math.min(max, Math.max(min, middle)));
    paintBudget();
  }
}

function mergeAdminSets(items) {
  const byName = new Map();
  let budgetMin = Infinity;
  let budgetMax = -Infinity;
  let budgetStep = 1;

  const ordered = [...items].sort((a, b) => Number(a.id) - Number(b.id));
  for (const item of ordered) {
    for (const service of item.services || []) {
      if (service?.name && !byName.has(service.name)) {
        byName.set(service.name, service);
      }
    }
    const min = Number(item.budget_min);
    const max = Number(item.budget_max);
    const step = Number(item.budget_step);
    if (Number.isFinite(min)) budgetMin = Math.min(budgetMin, min);
    if (Number.isFinite(max)) budgetMax = Math.max(budgetMax, max);
    if (Number.isFinite(step) && step > 0) budgetStep = step;
  }

  if (!byName.size || !Number.isFinite(budgetMin) || !Number.isFinite(budgetMax)) {
    return null;
  }

  return {
    services: [...byName.values()],
    budget_min: budgetMin,
    budget_max: budgetMax,
    budget_step: budgetStep,
  };
}

async function loadAdmin() {
  try {
    const response = await fetch("/api/admin-data?limit=200");
    if (!response.ok) return;
    const page = await response.json();
    const merged = mergeAdminSets(Array.isArray(page.items) ? page.items : []);
    if (merged) applyAdmin(merged);
  } catch {
    paintBudget();
  }
}

function markInvalid(field, invalid) {
  field.classList.toggle("is-invalid", invalid);
}

function validate() {
  let valid = true;
  form.querySelectorAll(".field").forEach((field) => {
    const control = field.querySelector("input, textarea, select");
    if (!control || control.type === "range") return;
    if (control.type === "radio") {
      const picked = field.querySelector("input[type='radio']:checked");
      markInvalid(field, !picked);
      if (!picked) valid = false;
      return;
    }
    const empty = control.required && !String(control.value || "").trim();
    markInvalid(field, empty);
    if (empty) valid = false;
  });
  return valid;
}

function showStatus(message, isError) {
  statusNode.hidden = false;
  statusNode.textContent = message;
  statusNode.classList.toggle("is-error", isError);
}

function errorText(payload) {
  if (!payload) return "Не удалось отправить заявку";
  if (typeof payload.detail === "string") return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg).filter(Boolean).join(" ");
  }
  return "Не удалось отправить заявку";
}

function technicalInfo() {
  return {
    user_agent: navigator.userAgent,
    language: navigator.language,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || null,
    screen_width: window.screen.width,
    screen_height: window.screen.height,
    viewport_width: window.innerWidth,
    viewport_height: window.innerHeight,
    referrer: document.referrer || null,
    page_url: window.location.href,
  };
}

function payload() {
  return {
    first_name: textOf("first_name"),
    last_name: textOf("last_name"),
    middle_name: optionalText("middle_name"),
    business_info: textOf("business_info"),
    business_niche: textOf("business_niche"),
    company_size: textOf("company_size"),
    business_size: textOf("business_size"),
    task_volume: textOf("task_volume"),
    need_volume: textOf("need_volume"),
    role: textOf("role"),
    task_type: textOf("task_type"),
    deadline: textOf("deadline"),
    product_interest: productSelect.value,
    budget: String(budgetInput.value),
    contact_method: textOf("contact_method"),
    convenient_time: textOf("convenient_time"),
    comment: optionalText("comment"),
    metrics: {
      time_on_page_seconds: Math.round((performance.now() - startedAt) / 100) / 10,
      buttons_clicked: clicks.slice(-40),
      cursor_hotspots: hotspots.slice(-40),
      return_count: returnCount,
      technical_info: technicalInfo(),
    },
  };
}

let lastPoint = null;
let stillTimer = 0;

document.addEventListener("pointermove", (event) => {
  const zone = event.target.closest("[data-zone]")?.dataset.zone || "страница";
  lastPoint = {
    x: Math.round(event.clientX),
    y: Math.round(event.clientY),
    zone,
  };
  window.clearTimeout(stillTimer);
  stillTimer = window.setTimeout(() => {
    if (!lastPoint || hotspots.length >= 40) return;
    hotspots.push(lastPoint);
  }, 450);
});

document.addEventListener("click", (event) => {
  const control = event.target.closest("button, .choice-item");
  if (!control || clicks.length >= 40) return;
  const name = control.dataset.track || control.textContent.trim().replace(/\s+/g, " ");
  clicks.push({
    name: name.slice(0, 120),
    at_second: Math.round((performance.now() - startedAt) / 100) / 10,
  });
});

budgetInput.addEventListener("input", paintBudget);
productSelect.addEventListener("change", paintServiceNote);
form.addEventListener("input", (event) => {
  const field = event.target.closest(".field");
  if (field) markInvalid(field, false);
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!validate()) {
    showStatus("Заполните отмеченные поля.", true);
    return;
  }
  const button = form.querySelector("button[type='submit']");
  button.disabled = true;
  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload()),
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      showStatus(errorText(body), true);
      return;
    }
    showStatus("Заявка принята. Мы свяжемся с вами в удобное время.", false);
    form.reset();
    if (adminSnapshot) applyAdmin(adminSnapshot);
    else {
      paintBudget();
      paintServiceNote();
    }
  } catch {
    showStatus("Сеть недоступна. Попробуйте ещё раз.", true);
  } finally {
    button.disabled = false;
  }
});

paintBudget();
loadAdmin();
