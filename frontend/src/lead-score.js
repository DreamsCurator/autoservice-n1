const HOT = 48;
const WARM = 32;

function text(value) {
  return String(value || "").toLowerCase();
}

function has(value, words) {
  const source = text(value);
  return words.some((word) => source.includes(word));
}

function moneyNumber(value) {
  const digits = String(value || "").replace(/[^\d]/g, "");
  const number = Number(digits);
  return Number.isFinite(number) ? number : 0;
}

function deadlinePoints(value) {
  if (has(value, ["не сроч", "не спеш", "когда будет", "следующем году", "полгода", "квартал"])) {
    return 2;
  }
  if (has(value, ["сегодня", "завтра", "сроч", "немедлен", "горит"])) return 40;
  if (has(value, ["недел", "ближайш", "3 дня", "три дня", "пару дней"])) {
    return 16;
  }
  if (has(value, ["месяц"])) return 10;
  return 2;
}

function budgetPoints(value) {
  const amount = moneyNumber(value);
  if (amount >= 180000) return 42;
  if (amount >= 80000) return 16;
  if (amount >= 40000) return 8;
  return 2;
}

function rolePoints(value) {
  return has(value, ["руковод"]) ? 16 : 3;
}

function scalePoints(company, business) {
  const source = `${company || ""} ${business || ""}`;
  if (has(source, ["крупн", "холдинг", "корпорац", "сеть", "филиал"])) return 24;
  if (has(source, ["средн", "50"])) return 10;
  return 2;
}

function volumePoints(task, need) {
  const source = `${task || ""} ${need || ""}`;
  if (has(source, ["парк", "постоянн", "ежеднев", "абонент", "десят"])) return 38;
  if (has(source, ["несколько", "регуляр"])) return 10;
  return 2;
}

function department(lead, scale, volume) {
  if (scale >= 20) return "Корпоративный отдел";
  const source = text(`${lead.product_interest} ${lead.task_type} ${lead.business_niche}`);
  if (/полир|керамик|кузов|лкп/.test(source)) return "Кузовной цех";
  if (/химчист|детейл|салон/.test(source)) return "Детейлинг";
  if (volume >= 30) return "Корпоративный отдел";
  return "Приёмка";
}

function bandOf(score) {
  if (score >= HOT) return "hot";
  if (score >= WARM) return "warm";
  return "cold";
}

const BAND_LABEL = {
  hot: "Срочный",
  warm: "Средний",
  cold: "Холодный",
};

const WORTH = {
  hot: "Да, связаться сегодня",
  warm: "Да, в общей очереди",
  cold: "Низкий приоритет, можно отложить",
};

export function scoreLead(lead) {
  const axes = [
    { name: "Срок", points: deadlinePoints(lead.deadline) },
    { name: "Бюджет", points: budgetPoints(lead.budget) },
    { name: "Роль", points: rolePoints(lead.role) },
    { name: "Масштаб", points: scalePoints(lead.company_size, lead.business_size) },
    { name: "Объём", points: volumePoints(lead.task_volume, lead.need_volume) },
  ];
  const score = Math.min(100, axes.reduce((sum, axis) => sum + axis.points, 0));
  const band = bandOf(score);
  const scale = axes.find((axis) => axis.name === "Масштаб").points;
  const volume = axes.find((axis) => axis.name === "Объём").points;
  const budget = axes.find((axis) => axis.name === "Бюджет").points;
  const role = axes.find((axis) => axis.name === "Роль").points;
  const manager = role >= 14 || scale >= 20 || budget >= 30 || volume >= 30;
  const reasons = axes
    .filter((axis) => axis.points >= 16)
    .sort((a, b) => b.points - a.points)
    .map((axis) => axis.name);

  return {
    score,
    band,
    label: BAND_LABEL[band],
    worth: WORTH[band],
    manager,
    department: department(lead, scale, volume),
    reasons,
    explanation: explainTemperature(lead, axes, band),
    marks: band === "hot" ? 3 : band === "warm" ? 2 : 1,
    axes,
  };
}

function clip(value) {
  const source = String(value || "").trim().replace(/\s+/g, " ");
  if (source.length <= 80) return source;
  return `${source.slice(0, 77)}…`;
}

function explainTemperature(lead, axes, band) {
  const deadline = axes.find((axis) => axis.name === "Срок").points;
  const budget = axes.find((axis) => axis.name === "Бюджет").points;
  const role = axes.find((axis) => axis.name === "Роль").points;
  const scale = axes.find((axis) => axis.name === "Масштаб").points;
  const volume = axes.find((axis) => axis.name === "Объём").points;
  const phrases = [];
  if (deadline >= 30) phrases.push(`результат нужен срочно («${clip(lead.deadline)}»)`);
  else if (deadline >= 16) phrases.push("срок в пределах недели");
  else if (deadline >= 10) phrases.push("срок около месяца");
  if (budget >= 30) phrases.push("высокий бюджет");
  else if (budget >= 16) phrases.push("заметный бюджет");
  if (role >= 14) phrases.push("заявку оставил руководитель");
  if (scale >= 20) phrases.push("крупная компания");
  else if (scale >= 10) phrases.push("компания среднего размера");
  if (volume >= 30) phrases.push("большой объём: парк или постоянный контракт");
  else if (volume >= 10) phrases.push("несколько машин или регулярные визиты");

  if (band === "hot") {
    return `Горячий, потому что ${phrases.join(", ")}.`;
  }
  if (band === "warm") {
    const why = phrases.length ? phrases.join(", ") : "сигналы средние";
    return `Тёплый: ${why}. До срочного не хватает более сильного срока, бюджета или объёма.`;
  }
  if (!phrases.length) {
    return "Холодный: нет срочного срока, крупного бюджета, руководителя, большой компании или парка.";
  }
  return `Холодный: есть только ${phrases.join(", ")}, этого мало, чтобы поднимать заявку.`;
}

export function compareLeads(a, b) {
  return b.priority.score - a.priority.score || b.id - a.id;
}
