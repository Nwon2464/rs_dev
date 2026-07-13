import { useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { Icon } from "./components/Icon";
import { OpenViewer } from "./components/OpenViewer";
import { PageHeader } from "./components/PageHeader";
import { Empty } from "./components/common/ExplorerPrimitives";
import { InstandardOptionOpenViewer } from "./components/instandard/InstandardOptionOpenViewer";
import { InstandardTierViewer } from "./components/instandard/InstandardTierViewer";
import {
  instandardModes,
  type InstandardMode,
} from "./components/instandard/modes";
import { featureIconId } from "./components/iconMap";
import { prepareGeneralOpenRows } from "./data/generalOpenOptions";
import {
  prepareInstandardOpenRows,
  type InstandardCatalog,
  type InstandardOpenOptionRow,
} from "./data/instandardOptions";
import type {
  EquipmentGroups,
  GeneralOpenOptionRow,
  OpenEquipmentBuckets,
  OpenMetadata,
  OptionLocales,
  OptionTagData,
} from "./domain/openOptions/types";
import {
  loadLanguage,
  saveLanguage,
  uiText,
  type Language,
  type UiMessageKey,
} from "./i18n";
import "./styles.css";

type View = "home" | "instandard" | "open";
type Theme = "light" | "dark";

type Resources = {
  source: InstandardCatalog;
  openRows: GeneralOpenOptionRow[];
  instandardOpenRows: InstandardOpenOptionRow[];
  optionLocales: OptionLocales;
  equipmentGroups: EquipmentGroups;
  openEquipmentBuckets: OpenEquipmentBuckets;
  openMetadata: OpenMetadata;
  optionTags: OptionTagData;
};

function App() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("view");
  const view: View =
    requested === "open" || requested === "instandard" ? requested : "home";
  const requestedMode = params.get("mode");
  const instandardMode: InstandardMode | null =
    requestedMode === "option" ||
    requestedMode === "open" ||
    requestedMode === "tier"
      ? requestedMode
      : null;
  const [theme, setTheme] = useState<Theme>(() =>
    localStorage.getItem("redstone-ui-theme") === "dark" ? "dark" : "light",
  );
  const [language, setLanguage] = useState<Language>(() =>
    loadLanguage(localStorage),
  );
  const [resources, setResources] = useState<Resources | null>(null);
  const [loadError, setLoadError] = useState<UiMessageKey | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("redstone-ui-theme", theme);
  }, [theme]);

  useEffect(() => {
    document.documentElement.lang = language;
    saveLanguage(localStorage, language);
  }, [language]);

  useEffect(() => {
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/open_options/instandard/catalog.json`).then(
        (response) => {
          if (!response.ok) throw new Error("error.dataset");
          return response.json() as Promise<InstandardCatalog>;
        },
      ),
      fetch(`${base}data/open_options/general/open_option_rows.csv`).then(
        (response) => {
          if (!response.ok) throw new Error("error.openCsv");
          return response.text();
        },
      ),
      fetch(`${base}data/open_options/instandard/open_option_rows.csv`).then(
        (response) => {
          if (!response.ok) throw new Error("error.instandardOpenCsv");
          return response.text();
        },
      ),
      fetch(`${base}data/open_options/i18n/ko/base_options.json`).then(
        (response) => {
          if (!response.ok) throw new Error("error.japaneseOptions");
          return response.json() as Promise<OptionLocales["ko"]>;
        },
      ),
      fetch(`${base}data/open_options/i18n/ja/base_options.json`).then(
        (response) => {
          if (!response.ok) throw new Error("error.japaneseOptions");
          return response.json() as Promise<OptionLocales["ja"]>;
        },
      ),
      fetch(`${base}data/open_options/catalogs/equipment_groups.json`).then(
        (response) => {
          if (!response.ok) {
            throw new Error("error.japaneseEquipmentGroups");
          }
          return response.json() as Promise<EquipmentGroups>;
        },
      ),
      fetch(
        `${base}data/open_options/catalogs/open_equipment_buckets.json`,
      ).then((response) => {
        if (!response.ok) {
          throw new Error("error.japaneseOpenEquipmentBuckets");
        }
        return response.json() as Promise<OpenEquipmentBuckets>;
      }),
      fetch(`${base}data/open_options/catalogs/open_metadata.json`).then(
        (response) => {
          if (!response.ok) throw new Error("error.japaneseOpenMetadata");
          return response.json() as Promise<OpenMetadata>;
        },
      ),
      fetch(`${base}data/open_options/catalogs/option_tags.json`).then(
        (response) => {
          if (!response.ok) throw new Error("error.optionTags");
          return response.json() as Promise<OptionTagData>;
        },
      ),
    ])
      .then(
        ([
          rawSource,
          csv,
          instandardOpenCsv,
          koreanBaseOptions,
          japaneseBaseOptions,
          equipmentGroups,
          openEquipmentBuckets,
          openMetadata,
          optionTags,
        ]) => {
          if (!cancelled) {
            setResources({
              source: rawSource,
              openRows: prepareGeneralOpenRows(csv, optionTags),
              instandardOpenRows: prepareInstandardOpenRows(instandardOpenCsv),
              optionLocales: {
                ko: koreanBaseOptions,
                ja: japaneseBaseOptions,
              },
              equipmentGroups,
              openEquipmentBuckets,
              openMetadata,
              optionTags,
            });
          }
        },
      )
      .catch((error: unknown) => {
        if (!cancelled) {
          setLoadError(
            error instanceof Error && error.message.startsWith("error.")
              ? (error.message as UiMessageKey)
              : "error.unknown",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const languageSelector = (
    <div
      className="language-selector"
      role="group"
      aria-label={uiText(language, "language.selector")}
    >
      <button
        type="button"
        className={language === "ko" ? "active" : ""}
        aria-pressed={language === "ko"}
        onClick={() => setLanguage("ko")}
      >
        한국어
      </button>
      <button
        type="button"
        className={language === "ja" ? "active" : ""}
        aria-pressed={language === "ja"}
        onClick={() => setLanguage("ja")}
      >
        日本語
      </button>
    </div>
  );
  const themeButton = (
    <button
      className="theme"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark"
        ? `☾ ${uiText(language, "theme.light")}`
        : `☀ ${uiText(language, "theme.dark")}`}
    </button>
  );
  const headerControls = (
    <>
      {languageSelector}
      {themeButton}
    </>
  );

  if (view === "home") {
    return <Home language={language} controls={headerControls} />;
  }
  if (loadError) {
    return (
      <>
        <PageHeader
          language={language}
          title={uiText(language, "error.title")}
          description={uiText(language, loadError)}
          controls={headerControls}
        />
        <main>
          <Empty language={language} />
        </main>
      </>
    );
  }
  if (!resources) {
    return (
      <>
        <PageHeader
          language={language}
          title={uiText(language, "loading.title")}
          description={uiText(language, "loading.description")}
          controls={headerControls}
        />
        <main>
          <div className="empty">{uiText(language, "loading.progress")}</div>
        </main>
      </>
    );
  }
  if (view === "open") {
    return (
      <OpenViewer
        rows={resources.openRows}
        language={language}
        optionLocales={resources.optionLocales}
        openEquipmentBuckets={resources.openEquipmentBuckets}
        openMetadata={resources.openMetadata}
        optionTags={resources.optionTags}
        themeButton={headerControls}
      />
    );
  }
  if (view === "instandard" && instandardMode === "tier") {
    return (
      <InstandardTierViewer
        source={resources.source}
        language={language}
        optionLocales={resources.optionLocales}
        equipmentGroups={resources.equipmentGroups}
        optionTags={resources.optionTags}
        controls={headerControls}
      />
    );
  }
  if (
    view === "instandard" &&
    (instandardMode === "option" || instandardMode === "open")
  ) {
    return (
      <InstandardOptionOpenViewer
        mode={instandardMode}
        source={resources.source}
        openRows={resources.instandardOpenRows}
        language={language}
        optionLocales={resources.optionLocales}
        equipmentGroups={resources.equipmentGroups}
        openMetadata={resources.openMetadata}
        optionTags={resources.optionTags}
        controls={headerControls}
      />
    );
  }
  return null;
}

function Home({
  language,
  controls,
}: {
  language: Language;
  controls: ReactNode;
}) {
  return (
    <>
      <PageHeader
        language={language}
        title={uiText(language, "app.title")}
        description={uiText(language, "app.description")}
        controls={controls}
        home={false}
      />
      <main className="home-main">
        <div className="home-landing-stack">
          <a className="home-open-card feature-card--open" href="?view=open">
            <div className="home-wide-card-copy">
              <Icon className="app-icon" id="feature-open-option" size={38} />
              <div>
                <h2>{uiText(language, "home.open.title")}</h2>
                <p>{uiText(language, "home.open.description")}</p>
              </div>
            </div>
            <b>{uiText(language, "home.open.action")}</b>
          </a>
          <section
            className="home-instandard-panel"
            aria-labelledby="home-instandard-title"
          >
            <div className="home-instandard-heading">
              <Icon
                className="app-icon"
                id="feature-instandard-option"
                size={38}
              />
              <div>
                <h2 id="home-instandard-title">
                  {uiText(language, "home.instandard.title")}
                </h2>
                <p>{uiText(language, "home.instandard.description")}</p>
              </div>
            </div>
            <div className="instandard-feature-cards home-instandard-feature-cards">
              {instandardModes.map((item) => (
                <a
                  className={`instandard-feature-card home-instandard-feature-card feature-card--${item.className}`}
                  href={`?view=instandard&mode=${item.mode}`}
                  key={item.mode}
                >
                  <Icon
                    className="app-icon"
                    id={featureIconId[item.iconLabel]}
                    size={38}
                  />
                  <h2>{uiText(language, item.titleKey)}</h2>
                  <p>{uiText(language, item.descriptionKey)}</p>
                  <b>{uiText(language, "common.view")}</b>
                </a>
              ))}
            </div>
          </section>
        </div>
      </main>
    </>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
