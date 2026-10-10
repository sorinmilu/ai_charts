const state = {
  years: {},
  buckets: {},
  data: null,
  definitions: null,
  filtersReady: false,
};

async function fetchJSON(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url} → ${res.status}`);
  return res.json();
}

async function loadPoints() {
  const data = await fetchJSON("/api/points");
  state.data = data;

  const years = [...new Set(data.points.map((p) => p.year).filter(Boolean))].sort();
  const buckets = data.buckets && data.buckets.length
    ? data.buckets
    : [...new Set(data.points.map((p) => p.source_bucket))];

  if (!state.filtersReady) {
    years.forEach((y) => {
      state.years[y] = true;
    });
    buckets.forEach((b) => {
      state.buckets[b] = true;
    });
    buildFilters(years, buckets, state, () => renderChart(state.data, state));
    state.filtersReady = true;
  } else {
    years.forEach((y) => {
      if (state.years[y] === undefined) state.years[y] = true;
    });
    buckets.forEach((b) => {
      if (state.buckets[b] === undefined) state.buckets[b] = true;
    });
    refreshBucketFilterLabels(buckets);
  }

  await renderChart(data, state);
}

async function loadDefinitions() {
  state.definitions = await fetchJSON("/api/definitions");
  renderDefinitions();
}

function renderDefinitions() {
  if (!state.definitions) return;
  const lang = getLang();
  const pack = state.definitions[lang] || state.definitions.en;

  const grid = document.getElementById("defs-grid");
  if (!grid) return;
  grid.innerHTML = "";
  (pack.issues || []).forEach((issue) => {
    const card = document.createElement("article");
    card.className = "defs-card";

    const h2 = document.createElement("h2");
    h2.textContent = `${issue.number}. ${issue.title}`;
    card.appendChild(h2);

    const q = document.createElement("p");
    q.className = "question";
    q.textContent = issue.question || "";
    card.appendChild(q);

    const table = document.createElement("table");
    table.className = "level-table";
    table.innerHTML = `<thead><tr>
      <th>${t("level")}</th>
      <th>${t("category")}</th>
      <th>${t("meaning")}</th>
    </tr></thead>`;
    const tbody = document.createElement("tbody");
    (issue.levels || []).forEach((row) => {
      const tr = document.createElement("tr");
      const lvl = row.level > 0 ? `+${row.level}` : String(row.level);
      tr.innerHTML = `<td class="lvl">${lvl}</td>
        <td class="cat">${escapeHtml(row.category)}</td>
        <td>${escapeHtml(row.meaning)}</td>`;
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    card.appendChild(table);

    grid.appendChild(card);
  });
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const tab = btn.dataset.tab;
      document.querySelectorAll(".tab").forEach((b) => {
        b.classList.toggle("active", b === btn);
        b.setAttribute("aria-selected", b === btn ? "true" : "false");
      });
      document.querySelectorAll(".panel").forEach((panel) => {
        const active = panel.id === `panel-${tab}`;
        panel.classList.toggle("active", active);
        panel.hidden = !active;
      });
      hideChartPopups();
      if (tab === "chart") {
        await loadPoints();
        resizeChart();
      } else if (tab === "defs") {
        await loadDefinitions();
      } else if (tab === "articles") {
        await loadArticles();
      }
    });
  });
}

function setupLang() {
  const sync = () => {
    const lang = getLang();
    document.querySelectorAll(".lang-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.lang === lang);
    });
    applyStaticI18n();
    if (state.data) {
      refreshBucketFilterLabels(state.data.buckets || []);
      renderChart(state.data, state);
    }
    if (state.definitions) renderDefinitions();
    refreshArticlesI18n();
  };

  document.querySelectorAll(".lang-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      setLang(btn.dataset.lang);
      sync();
    });
  });
  sync();
}

function setupHoverCard() {
  const card = document.getElementById("hover-card");
  const stack = document.getElementById("marker-stack");

  card.addEventListener("mouseleave", () => {
    window.setTimeout(() => {
      if (!card.matches(":hover") && !stack.matches(":hover")) hideHoverCard();
    }, 120);
  });

  document.addEventListener("pointerdown", (e) => {
    if (stack.classList.contains("hidden") && card.classList.contains("hidden")) {
      return;
    }
    if (stack.contains(e.target) || card.contains(e.target)) return;
    // Let Plotly finish the marker click first; dismiss only true outside clicks.
    const onChart = document.getElementById("chart").contains(e.target);
    if (onChart) return;
    hideChartPopups();
  });
}

async function refreshAll() {
  if (document.getElementById("panel-chart").classList.contains("active")) {
    await loadPoints();
  } else if (document.getElementById("panel-defs").classList.contains("active")) {
    await loadDefinitions();
  } else if (document.getElementById("panel-articles").classList.contains("active")) {
    await loadArticles();
  }
}

async function init() {
  setupTabs();
  setupLang();
  setupHoverCard();
  setupArticlesPagination();
  setupArticleDetails();
  window.addEventListener("resize", resizeChart);
  window.addEventListener("focus", refreshAll);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") refreshAll();
  });
  const results = await Promise.allSettled([loadPoints(), loadDefinitions()]);
  const failed = results.find((r) => r.status === "rejected");
  if (failed) {
    console.error(failed.reason);
    if (results[0].status === "rejected") {
      const chart = document.getElementById("chart");
      if (chart) chart.textContent = String(failed.reason);
    }
  }
}

init().catch((err) => {
  console.error(err);
  const chart = document.getElementById("chart");
  if (chart) chart.textContent = String(err);
});
