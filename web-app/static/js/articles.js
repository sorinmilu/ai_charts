const articlesState = {
  data: null,
  page: 1,
  pageSize: 20,
  filters: {
    concerns: [],
    years: [],
    types: [],
    search: "",
  },
  filtersBuilt: false,
};

const MS_FILTERS = [
  { key: "concerns", panelId: "articles-filter-concern", btnId: "articles-filter-concern-btn" },
  { key: "years", panelId: "articles-filter-year", btnId: "articles-filter-year-btn" },
  { key: "types", panelId: "articles-filter-type", btnId: "articles-filter-type-btn" },
];

const ARTICLE_COLUMNS = [
  "id",
  "dimension",
  "author",
  "date",
  "source_type",
  "level_label",
  "source_title",
  "source_url",
  "type",
  "researched_on",
];

async function loadArticles() {
  articlesState.data = await fetchJSON("/api/articles");
  if (!articlesState.filtersBuilt) {
    buildArticleFilters();
    articlesState.filtersBuilt = true;
  } else {
    refreshArticleFilterOptions();
  }
  renderArticles();
}

function concernOptionLabel(concern) {
  const lang = getLang();
  return lang === "ro" ? concern.label_ro : concern.label_en;
}

function checkedValues(panel) {
  return [...panel.querySelectorAll('input[type="checkbox"]:checked')].map((el) => el.value);
}

function closeAllMsDropdowns(exceptPanel) {
  MS_FILTERS.forEach(({ panelId, btnId }) => {
    const panel = document.getElementById(panelId);
    const btn = document.getElementById(btnId);
    if (!panel || panel === exceptPanel) return;
    panel.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  });
}

function msTriggerLabel(key, selected, options) {
  if (!selected.length) return t("filterAll");
  if (selected.length === 1) {
    const match = options.find((o) => o.value === selected[0]);
    return match ? match.label : selected[0];
  }
  return t("filterSelectedCount").replace("{n}", String(selected.length));
}

function updateMsTrigger(key) {
  const cfg = MS_FILTERS.find((f) => f.key === key);
  if (!cfg || !articlesState.data) return;
  const btn = document.getElementById(cfg.btnId);
  const labelEl = btn.querySelector(".ms-trigger-label");
  const selected = articlesState.filters[key];
  const options = msOptionsFor(key);
  labelEl.textContent = msTriggerLabel(key, selected, options);
}

function msOptionsFor(key) {
  if (!articlesState.data) return [];
  if (key === "concerns") {
    return articlesState.data.concerns.map((c) => ({
      value: c.id,
      label: concernOptionLabel(c),
    }));
  }
  if (key === "years") {
    return articlesState.data.years.map((y) => ({ value: y, label: y }));
  }
  return articlesState.data.types.map((ty) => ({ value: ty, label: ty }));
}

function fillMsPanel(key) {
  const cfg = MS_FILTERS.find((f) => f.key === key);
  const panel = document.getElementById(cfg.panelId);
  const selected = new Set(articlesState.filters[key]);
  panel.innerHTML = "";
  msOptionsFor(key).forEach((opt) => {
    const id = `ms-${key}-${opt.value.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
    const label = document.createElement("label");
    label.className = "ms-option";
    label.setAttribute("role", "option");
    label.htmlFor = id;
    const input = document.createElement("input");
    input.type = "checkbox";
    input.id = id;
    input.value = opt.value;
    input.checked = selected.has(opt.value);
    const span = document.createElement("span");
    span.textContent = opt.label;
    label.append(input, span);
    panel.appendChild(label);
  });
  updateMsTrigger(key);
}

function syncFiltersFromPanels() {
  MS_FILTERS.forEach(({ key, panelId }) => {
    articlesState.filters[key] = checkedValues(document.getElementById(panelId));
    updateMsTrigger(key);
  });
  const searchInput = document.getElementById("articles-filter-search");
  articlesState.filters.search = searchInput.value.trim();
  articlesState.page = 1;
  renderArticles();
}

function buildArticleFilters() {
  const searchInput = document.getElementById("articles-filter-search");

  MS_FILTERS.forEach(({ panelId, btnId }) => {
    const panel = document.getElementById(panelId);
    const btn = document.getElementById(btnId);
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const opening = panel.hidden;
      closeAllMsDropdowns(opening ? panel : null);
      panel.hidden = !opening;
      btn.setAttribute("aria-expanded", opening ? "true" : "false");
    });
    panel.addEventListener("change", (e) => {
      if (e.target.matches('input[type="checkbox"]')) syncFiltersFromPanels();
    });
    panel.addEventListener("click", (e) => e.stopPropagation());
  });

  document.addEventListener("click", () => closeAllMsDropdowns(null));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllMsDropdowns(null);
  });

  let searchTimer = null;
  searchInput.addEventListener("input", () => {
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(syncFiltersFromPanels, 180);
  });

  refreshArticleFilterOptions();
}

function refreshArticleFilterOptions() {
  if (!articlesState.data) return;
  MS_FILTERS.forEach(({ key }) => fillMsPanel(key));
}

function filteredArticles() {
  if (!articlesState.data) return [];
  const { concerns, years, types, search } = articlesState.filters;
  const q = search.toLowerCase();
  return articlesState.data.articles.filter((a) => {
    if (concerns.length && !concerns.includes(a.concern)) return false;
    if (years.length && !years.includes(a.year)) return false;
    if (types.length && !types.includes(a.type || a.source_type)) return false;
    if (q) {
      const author = (a.author || "").toLowerCase();
      const title = (a.source_title || "").toLowerCase();
      if (!author.includes(q) && !title.includes(q)) return false;
    }
    return true;
  });
}

function renderArticles() {
  const all = filteredArticles();
  const total = all.length;
  const pageCount = Math.max(1, Math.ceil(total / articlesState.pageSize));
  if (articlesState.page > pageCount) articlesState.page = pageCount;
  const start = (articlesState.page - 1) * articlesState.pageSize;
  const pageRows = all.slice(start, start + articlesState.pageSize);

  const thead = document.getElementById("articles-thead");
  const tbody = document.getElementById("articles-tbody");
  thead.innerHTML = "";
  const hr = document.createElement("tr");
  ARTICLE_COLUMNS.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = t(`col_${col}`) || col;
    hr.appendChild(th);
  });
  const thAct = document.createElement("th");
  thAct.textContent = t("col_actions");
  hr.appendChild(thAct);
  thead.appendChild(hr);

  tbody.innerHTML = "";
  if (!pageRows.length) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = ARTICLE_COLUMNS.length + 1;
    td.className = "articles-empty";
    td.textContent = t("articlesEmpty");
    tr.appendChild(td);
    tbody.appendChild(tr);
  } else {
    pageRows.forEach((row) => {
      const tr = document.createElement("tr");
      ARTICLE_COLUMNS.forEach((col) => {
        const td = document.createElement("td");
        const val = row[col] || "";
        if (col === "source_url" && val) {
          const a = document.createElement("a");
          a.href = val;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.className = "articles-url";
          a.textContent = val;
          td.appendChild(a);
        } else {
          td.textContent = val;
          if (col === "source_title" || col === "author") td.className = "articles-clip";
        }
        tr.appendChild(td);
      });
      const tdAct = document.createElement("td");
      tdAct.className = "articles-actions";
      const viewBtn = document.createElement("button");
      viewBtn.type = "button";
      viewBtn.className = "articles-btn";
      viewBtn.textContent = t("viewOnline");
      viewBtn.disabled = !row.source_url;
      viewBtn.addEventListener("click", () => {
        if (row.source_url) window.open(row.source_url, "_blank", "noopener,noreferrer");
      });
      const detailBtn = document.createElement("button");
      detailBtn.type = "button";
      detailBtn.className = "articles-btn articles-btn-secondary";
      detailBtn.textContent = t("details");
      detailBtn.addEventListener("click", () => openArticleDetails(row));
      tdAct.append(viewBtn, detailBtn);
      tr.appendChild(tdAct);
      tbody.appendChild(tr);
    });
  }

  const meta = document.getElementById("articles-page-meta");
  const from = total ? start + 1 : 0;
  const to = Math.min(start + articlesState.pageSize, total);
  meta.textContent = t("articlesPageMeta")
    .replace("{from}", String(from))
    .replace("{to}", String(to))
    .replace("{total}", String(total));

  const prev = document.getElementById("articles-prev");
  const next = document.getElementById("articles-next");
  prev.disabled = articlesState.page <= 1;
  next.disabled = articlesState.page >= pageCount || total === 0;
  renderPageNumbers(pageCount);
}

function pageNumberItems(pageCount, current) {
  if (pageCount <= 1) return pageCount === 1 ? [1] : [];
  if (pageCount <= 9) {
    return Array.from({ length: pageCount }, (_, i) => i + 1);
  }
  const items = new Set([1, pageCount, current]);
  for (let p = current - 1; p <= current + 1; p += 1) {
    if (p >= 1 && p <= pageCount) items.add(p);
  }
  if (current <= 3) {
    [2, 3, 4, 5].forEach((p) => {
      if (p < pageCount) items.add(p);
    });
  }
  if (current >= pageCount - 2) {
    [pageCount - 4, pageCount - 3, pageCount - 2, pageCount - 1].forEach((p) => {
      if (p > 1) items.add(p);
    });
  }
  const sorted = [...items].sort((a, b) => a - b);
  const out = [];
  let prev = 0;
  sorted.forEach((p) => {
    if (prev && p - prev > 1) out.push("…");
    out.push(p);
    prev = p;
  });
  return out;
}

function renderPageNumbers(pageCount) {
  const wrap = document.getElementById("articles-page-numbers");
  wrap.innerHTML = "";
  const current = articlesState.page;
  pageNumberItems(pageCount, current).forEach((item) => {
    if (item === "…") {
      const span = document.createElement("span");
      span.className = "articles-page-ellipsis";
      span.textContent = "…";
      span.setAttribute("aria-hidden", "true");
      wrap.appendChild(span);
      return;
    }
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "articles-page-num";
    btn.textContent = String(item);
    btn.setAttribute("aria-label", `${t("page")} ${item}`);
    if (item === current) {
      btn.classList.add("active");
      btn.setAttribute("aria-current", "page");
    }
    btn.addEventListener("click", () => {
      if (articlesState.page === item) return;
      articlesState.page = item;
      renderArticles();
    });
    wrap.appendChild(btn);
  });
}

function setupArticlesPagination() {
  document.getElementById("articles-prev").addEventListener("click", () => {
    if (articlesState.page > 1) {
      articlesState.page -= 1;
      renderArticles();
    }
  });
  document.getElementById("articles-next").addEventListener("click", () => {
    articlesState.page += 1;
    renderArticles();
  });
}

function openArticleDetails(row) {
  const dialog = document.getElementById("article-details");
  const body = document.getElementById("article-details-body");
  const title = document.getElementById("article-details-title");
  title.textContent = row.source_title || row.id || t("details");
  body.innerHTML = "";
  const skip = new Set(["concern", "year"]);
  const keys = Object.keys(row).filter((k) => !skip.has(k));
  keys.forEach((key) => {
    const val = row[key];
    if (val === undefined || val === null || val === "") return;
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    if (key === "source_url") {
      const a = document.createElement("a");
      a.href = val;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      a.textContent = val;
      dd.appendChild(a);
    } else {
      dd.textContent = String(val);
    }
    body.append(dt, dd);
  });
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function closeArticleDetails() {
  const dialog = document.getElementById("article-details");
  if (typeof dialog.close === "function") dialog.close();
  else dialog.removeAttribute("open");
}

function setupArticleDetails() {
  document.getElementById("article-details-close").addEventListener("click", closeArticleDetails);
  document.getElementById("article-details").addEventListener("click", (e) => {
    if (e.target === e.currentTarget) closeArticleDetails();
  });
}

function refreshArticlesI18n() {
  if (!articlesState.filtersBuilt) return;
  refreshArticleFilterOptions();
  renderArticles();
}
