const I18N = {
  ro: {
    appTitle: "Puncte de vedere despre IA",
    appSubtitle: "Cinci dimensiuni, de la −3 la +3",
    tabChart: "Grafic",
    tabDefs: "Definiții",
    filterYear: "An",
    filterBucket: "Tip sursă",
    openSource: "Deschide sursa",
    level: "Nivel",
    category: "Categorie",
    meaning: "Semnificație",
    xAxis: "Nivel (−3 … +3)",
    noUrl: "Fără URL",
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
    filterYear: "Year",
    filterBucket: "Source type",
    openSource: "Open source",
    level: "Level",
    category: "Category",
    meaning: "Meaning",
    xAxis: "Level (−3 … +3)",
    noUrl: "No URL",
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
    if (el.tagName === "A" || el.tagName === "BUTTON" || el.tagName === "SPAN") {
      el.textContent = value;
    } else {
      el.textContent = value;
    }
  });
  document.documentElement.lang = getLang();
  document.title = t("appTitle");
}
