const I18N = {
  ro: {
    appTitle: "Puncte de vedere despre IA",
    appSubtitle: "Cinci dimensiuni, de la −3 la +3",
    tabChart: "Grafic",
    tabDefs: "Definiții",
    tabArticles: "Articole",
    filterYear: "An",
    filterBucket: "Tip sursă",
    filterCapability: "Dimensiune",
    filterType: "Tip",
    filterSearch: "Căutare",
    filterAll: "Toate",
    filterSelectedCount: "{n} selectate",
    searchPlaceholder: "Autor sau titlu…",
    openSource: "Deschide sursa",
    level: "Nivel",
    category: "Categorie",
    meaning: "Semnificație",
    xAxis: "Nivel (−3 … +3)",
    noUrl: "Fără URL",
    viewOnline: "Vezi online",
    details: "Detalii",
    close: "Închide",
    prevPage: "Înapoi",
    nextPage: "Înainte",
    page: "Pagina",
    articlesEmpty: "Niciun articol pentru filtrele selectate.",
    articlesPageMeta: "{from}–{to} din {total}",
    col_id: "id",
    col_dimension: "dimension",
    col_author: "author",
    col_date: "date",
    col_source_type: "source_type",
    col_level_label: "level_label",
    col_source_title: "source_title",
    col_source_url: "source_url",
    col_type: "type",
    col_researched_on: "researched_on",
    col_actions: "Acțiuni",
    buckets: {
      Podcast: "Podcast",
      Interview: "Interviu",
      Research: "Cercetare",
      Industry: "Industrie",
      Institutional: "Instituțional",
      "Blog / essay": "Blog / eseu",
    },
  },
  en: {
    appTitle: "AI talking points",
    appSubtitle: "Five dimensions, from −3 to +3",
    tabChart: "Chart",
    tabDefs: "Definitions",
    tabArticles: "Articles",
    filterYear: "Year",
    filterBucket: "Source type",
    filterCapability: "Capability",
    filterType: "Type",
    filterSearch: "Search",
    filterAll: "All",
    filterSelectedCount: "{n} selected",
    searchPlaceholder: "Author or title…",
    openSource: "Open source",
    level: "Level",
    category: "Category",
    meaning: "Meaning",
    xAxis: "Level (−3 … +3)",
    noUrl: "No URL",
    viewOnline: "View online",
    details: "Details",
    close: "Close",
    prevPage: "Previous",
    nextPage: "Next",
    page: "Page",
    articlesEmpty: "No articles match the selected filters.",
    articlesPageMeta: "{from}–{to} of {total}",
    col_id: "id",
    col_dimension: "dimension",
    col_author: "author",
    col_date: "date",
    col_source_type: "source_type",
    col_level_label: "level_label",
    col_source_title: "source_title",
    col_source_url: "source_url",
    col_type: "type",
    col_researched_on: "researched_on",
    col_actions: "Actions",
    buckets: {
      Podcast: "Podcast",
      Interview: "Interview",
      Research: "Research",
      Industry: "Industry",
      Institutional: "Institutional",
      "Blog / essay": "Blog / essay",
    },
  },
};

const LANG_KEY = "ai_talk_lang";

function getLang() {
  const stored = localStorage.getItem(LANG_KEY);
  return stored === "en" || stored === "ro" ? stored : "ro";
}

function setLang(lang) {
  localStorage.setItem(LANG_KEY, lang);
}

function t(key) {
  const lang = getLang();
  return I18N[lang][key] || I18N.en[key] || key;
}

function bucketLabel(bucket) {
  const lang = getLang();
  return (I18N[lang].buckets && I18N[lang].buckets[bucket]) || bucket;
}

function applyStaticI18n() {
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    const value = t(key);
    if (el.tagName === "A" || el.tagName === "BUTTON" || el.tagName === "SPAN" || el.tagName === "LABEL") {
      el.textContent = value;
    } else {
      el.textContent = value;
    }
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.getAttribute("data-i18n-placeholder"));
  });
  document.documentElement.lang = getLang();
  document.title = t("appTitle");
}
