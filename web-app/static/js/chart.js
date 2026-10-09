const YEAR_COLORS = {
  "2020": "#e10600",
  "2022": "#3d6b8a",
  "2023": "#0f6b5c",
  "2024": "#b06a2b",
  "2025": "#6b3d8a",
  "2026": "#ffe600",
};

const BUCKET_SYMBOLS = {
  Podcast: "circle",
  Interview: "square",
  Research: "diamond",
  Industry: "triangle-up",
  Institutional: "x",
  "Blog / essay": "star",
};

function hashJitter(id) {
  let h = 0;
  const s = String(id || "");
  for (let i = 0; i < s.length; i += 1) {
    h = (h * 31 + s.charCodeAt(i)) >>> 0;
  }
  return ((h % 1000) / 1000 - 0.5) * 0.28;
}

function concernLabel(concern, lang) {
  return lang === "ro" ? concern.label_ro : concern.label_en;
}

function buildFilters(years, buckets, state, onChange) {
  const yearBox = document.getElementById("year-filters");
  const bucketBox = document.getElementById("bucket-filters");
  yearBox.innerHTML = "";
  bucketBox.innerHTML = "";

  years.forEach((year) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "toggle year-toggle active";
    btn.textContent = year;
    const color = YEAR_COLORS[year] || "#888";
    btn.style.setProperty("--year-color", color);
    btn.style.backgroundColor = color;
    btn.style.borderColor = color;
    // Bright yellow needs dark label text for contrast.
    if (year === "2026") btn.style.color = "#1c2430";
    btn.dataset.year = year;
    btn.addEventListener("click", () => {
      state.years[year] = !state.years[year];
      btn.classList.toggle("active", state.years[year]);
      onChange();
    });
    yearBox.appendChild(btn);
  });

  buckets.forEach((bucket) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "toggle bucket-toggle active";
    btn.dataset.bucket = bucket;

    const glyph = document.createElement("span");
    glyph.className = `marker-glyph ${symbolClass(bucket)}`;
    glyph.setAttribute("aria-hidden", "true");

    const label = document.createElement("span");
    label.className = "bucket-toggle-label";
    label.textContent = bucketLabel(bucket);

    btn.appendChild(glyph);
    btn.appendChild(label);
    btn.addEventListener("click", () => {
      state.buckets[bucket] = !state.buckets[bucket];
      btn.classList.toggle("active", state.buckets[bucket]);
      onChange();
    });
    bucketBox.appendChild(btn);
  });
}

function refreshBucketFilterLabels(buckets) {
  document.querySelectorAll("#bucket-filters .toggle").forEach((btn) => {
    const bucket = btn.dataset.bucket;
    const label = btn.querySelector(".bucket-toggle-label");
    if (bucket && label) label.textContent = bucketLabel(bucket);
  });
}

function filteredPoints(points, state) {
  return points.filter(
    (p) =>
      p.year &&
      state.years[p.year] !== false &&
      state.buckets[p.source_bucket] !== false
  );
}

function renderChart(data, state) {
  const lang = getLang();
  const concerns = data.concerns || [];
  const labels = concerns.map((c) => concernLabel(c, lang));
  const labelById = Object.fromEntries(
    concerns.map((c) => [c.id, concernLabel(c, lang)])
  );
  const points = filteredPoints(data.points || [], state);

  const xs = [];
  const ys = [];
  const colors = [];
  const symbols = [];
  const customdata = [];
  points.forEach((p) => {
    const base = labels.indexOf(labelById[p.concern]);
    if (base < 0) return;
    xs.push(p.level);
    ys.push(base + hashJitter(p.id));
    colors.push(YEAR_COLORS[p.year] || "#555");
    symbols.push(BUCKET_SYMBOLS[p.source_bucket] || "circle");
    customdata.push(p);
  });

  const trace = {
    type: "scatter",
    mode: "markers",
    x: xs,
    y: ys,
    customdata,
    hoverinfo: "none",
    hovertemplate: null,
    marker: {
      size: 11,
      color: colors,
      symbol: symbols,
      opacity: 0.9,
      line: { width: 1, color: "rgba(28,36,48,0.35)" },
    },
  };

  const layout = {
    margin: { l: 24, r: 170, t: 28, b: 48 },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(255,252,246,0.35)",
    font: { family: "DM Sans, sans-serif", color: "#1c2430", size: 12 },
    xaxis: {
      title: { text: t("xAxis"), font: { size: 12 } },
      range: [-3.4, 3.4],
      tickmode: "array",
      tickvals: [-3, -2, -1, 0, 1, 2, 3],
      zeroline: true,
      zerolinewidth: 2,
      zerolinecolor: "rgba(15,107,92,0.55)",
      gridcolor: "rgba(201,192,176,0.7)",
      fixedrange: true,
    },
    yaxis: {
      // High→low so concern 1 (capability) sits at the top.
      range: [labels.length - 0.4, -0.6],
      tickmode: "array",
      tickvals: labels.map((_, i) => i),
      ticktext: labels,
      side: "right",
      zeroline: false,
      showgrid: true,
      gridcolor: "rgba(201,192,176,0.55)",
      fixedrange: true,
    },
    shapes: labels.map((_, i) => ({
      type: "line",
      x0: -3,
      x1: 3,
      y0: i,
      y1: i,
      line: { color: "rgba(28,36,48,0.28)", width: 1.5 },
    })),
    showlegend: false,
    // Must stay "closest": hovermode:false disables Plotly point picking, so
    // plotly_click never receives marker data. Tooltips stay off via hoverinfo.
    hovermode: "closest",
  };

  const config = {
    displayModeBar: false,
    responsive: true,
  };

  const el = document.getElementById("chart");
  el._visiblePoints = points;
  hideMarkerStack();
  hideHoverCard();
  return Plotly.react(el, [trace], layout, config).then(() => {
    // Plotly injects SVG <title> nodes that become native browser tooltips.
    el.querySelectorAll("svg title").forEach((node) => node.remove());
    if (!el._chartEventsBound) {
      el.on("plotly_click", (ev) => onChartClick(ev, el));
      el._chartEventsBound = true;
    }
  });
}

function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function symbolClass(bucket) {
  const sym = BUCKET_SYMBOLS[bucket] || "circle";
  return `sym-${sym}`;
}

function groupKey(p) {
  return `${p.concern}::${p.level}`;
}

function pointsInGroup(points, p) {
  return (points || []).filter(
    (q) => q.concern === p.concern && Number(q.level) === Number(p.level)
  );
}

function clampToPanel(el, left, top) {
  const panel = document.getElementById("panel-chart");
  const bounds = panel.getBoundingClientRect();
  const cw = el.offsetWidth;
  const ch = el.offsetHeight;
  let l = left;
  let t = top;
  if (l + cw > bounds.width - 8) l = bounds.width - cw - 8;
  if (t + ch > bounds.height - 8) t = bounds.height - ch - 8;
  if (l < 8) l = 8;
  if (t < 8) t = 8;
  el.style.left = `${l}px`;
  el.style.top = `${t}px`;
}

function onChartClick(ev, chartEl) {
  const pt = ev.points && ev.points[0];
  if (!pt || !pt.customdata) return;
  const p = pt.customdata;
  const group = pointsInGroup(chartEl._visiblePoints, p);
  const clientX = (ev.event && ev.event.clientX) || 0;
  const clientY = (ev.event && ev.event.clientY) || 0;
  if (group.length <= 1) {
    hideMarkerStack();
    const panel = document.getElementById("panel-chart");
    const bounds = panel.getBoundingClientRect();
    fillHoverCard(group[0] || p);
    const card = document.getElementById("hover-card");
    card.classList.remove("hidden");
    clampToPanel(card, clientX - bounds.left + 14, clientY - bounds.top + 14);
    return;
  }
  showMarkerStack(group, clientX, clientY);
}

function showMarkerStack(group, clientX, clientY) {
  const stack = document.getElementById("marker-stack");
  const panel = document.getElementById("panel-chart");
  const bounds = panel.getBoundingClientRect();
  hideHoverCard();
  stack.innerHTML = "";

  const ordered = [...group].sort((a, b) => {
    const ya = String(a.year || "");
    const yb = String(b.year || "");
    if (ya !== yb) return ya.localeCompare(yb);
    return String(a.author || "").localeCompare(String(b.author || ""));
  });

  ordered.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "marker-stack-item";
    btn.setAttribute("role", "listitem");
    btn.setAttribute(
      "aria-label",
      [p.author, p.source_title].filter(Boolean).join(" — ")
    );
    const glyph = document.createElement("span");
    glyph.className = `marker-glyph ${symbolClass(p.source_bucket)}`;
    glyph.style.color = YEAR_COLORS[p.year] || "#555";
    btn.appendChild(glyph);
    btn.addEventListener("mouseenter", () => {
      window.clearTimeout(stack._hideCardTimer);
      showHoverCardBesideStack(p);
    });
    btn.addEventListener("mouseleave", () => {
      window.clearTimeout(stack._hideCardTimer);
      stack._hideCardTimer = window.setTimeout(() => {
        const card = document.getElementById("hover-card");
        if (!card.matches(":hover") && !stack.matches(":hover")) {
          hideHoverCard();
        }
      }, 160);
    });
    btn.addEventListener("focus", () => showHoverCardBesideStack(p));
    stack.appendChild(btn);
  });

  stack.dataset.groupKey = ordered[0] ? groupKey(ordered[0]) : "";
  stack.classList.remove("hidden");
  clampToPanel(
    stack,
    clientX - bounds.left + 16,
    clientY - bounds.top - stack.offsetHeight / 2
  );
}

function showHoverCardBesideStack(p) {
  const stack = document.getElementById("marker-stack");
  const panel = document.getElementById("panel-chart");
  const bounds = panel.getBoundingClientRect();
  const sr = stack.getBoundingClientRect();
  // Prefer right of the stack so glyphs stay uncovered; flip if needed.
  let left = sr.right - bounds.left + 12;
  let top = sr.top - bounds.top;
  fillHoverCard(p);
  const card = document.getElementById("hover-card");
  card.classList.remove("hidden");
  if (left + card.offsetWidth > bounds.width - 8) {
    left = sr.left - bounds.left - card.offsetWidth - 12;
  }
  clampToPanel(card, left, top);
}

function hideMarkerStack() {
  const stack = document.getElementById("marker-stack");
  if (!stack) return;
  window.clearTimeout(stack._hideCardTimer);
  stack.classList.add("hidden");
  stack.innerHTML = "";
  delete stack.dataset.groupKey;
}

function fillHoverCard(p) {
  document.getElementById("hover-author").textContent = p.author || "—";
  document.getElementById("hover-title").textContent = p.source_title || "—";
  document.getElementById("hover-point").textContent = p.talking_point || "—";
  const link = document.getElementById("hover-link");
  if (p.source_url) {
    link.href = p.source_url;
    link.style.display = "inline-block";
    link.textContent = t("openSource");
  } else {
    link.removeAttribute("href");
    link.style.display = "none";
  }
}

function hideHoverCard() {
  document.getElementById("hover-card").classList.add("hidden");
}

function hideChartPopups() {
  hideHoverCard();
  hideMarkerStack();
}

function resizeChart() {
  const el = document.getElementById("chart");
  if (el && el.data) Plotly.Plots.resize(el);
}
