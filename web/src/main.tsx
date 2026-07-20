import { useEffect, useState, type ReactNode } from "react";
import { Icon } from "./components/Icon";
import { OpenViewer } from "./components/OpenViewer";
import { PageHeader } from "./components/PageHeader";
import { Empty } from "./components/common/ExplorerPrimitives";
import { InstandardOpenViewer } from "./components/instandard/InstandardOpenViewer";
import { InstandardOptionViewer } from "./components/instandard/InstandardOptionViewer";
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
  saveLanguage,
  uiText,
  type Language,
  type UiMessageKey,
} from "./i18n";
import { instandardUrl, openOptionsUrl, pageUrl } from "./siteUrls";
import "./styles.css";

export type View = "home" | "instandard" | "open";

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

export function App({
  initialView = "home",
  initialMode = null,
  initialLanguage = "ja",
  staticTitle,
  staticDescription,
  dataUpdatedDate,
  formattedDataUpdatedDate,
}: {
  initialView?: View;
  initialMode?: InstandardMode | null;
  initialLanguage?: Language;
  staticTitle?: string;
  staticDescription?: string;
  dataUpdatedDate?: string;
  formattedDataUpdatedDate?: string;
}) {
  const view = initialView;
  const instandardMode = initialMode;
  const language = initialLanguage;
  const [resources, setResources] = useState<Partial<Resources> | null>(null);
  const [loadError, setLoadError] = useState<UiMessageKey | null>(null);

  useEffect(() => {
    document.documentElement.lang = language;
    saveLanguage(localStorage, language);
  }, [language]);

  useEffect(() => {
    if (view === "home") return;
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    const json = async <T,>(path: string, error: UiMessageKey): Promise<T> => {
      const response = await fetch(`${base}${path}`);
      if (!response.ok) throw new Error(error);
      return response.json() as Promise<T>;
    };
    const text = async (path: string, error: UiMessageKey): Promise<string> => {
      const response = await fetch(`${base}${path}`);
      if (!response.ok) throw new Error(error);
      return response.text();
    };
    const load = async (): Promise<Partial<Resources>> => {
      const [koreanBaseOptions, japaneseBaseOptions, optionTags] =
        await Promise.all([
          json<OptionLocales["ko"]>(
            "data/open_options/i18n/ko/base_options.json",
            "error.japaneseOptions",
          ),
          json<OptionLocales["ja"]>(
            "data/open_options/i18n/ja/base_options.json",
            "error.japaneseOptions",
          ),
          json<OptionTagData>(
            "data/open_options/catalogs/option_tags.json",
            "error.optionTags",
          ),
        ]);
      const common = {
        optionLocales: { ko: koreanBaseOptions, ja: japaneseBaseOptions },
        optionTags,
      };
      if (view === "open") {
        const [csv, openEquipmentBuckets, openMetadata] = await Promise.all([
          text(
            "data/open_options/general/open_option_rows.csv",
            "error.openCsv",
          ),
          json<OpenEquipmentBuckets>(
            "data/open_options/catalogs/open_equipment_buckets.json",
            "error.japaneseOpenEquipmentBuckets",
          ),
          json<OpenMetadata>(
            "data/open_options/catalogs/open_metadata.json",
            "error.japaneseOpenMetadata",
          ),
        ]);
        return {
          ...common,
          openRows: prepareGeneralOpenRows(csv, optionTags),
          openEquipmentBuckets,
          openMetadata,
        };
      }
      const [source, equipmentGroups] = await Promise.all([
        json<InstandardCatalog>(
          "data/open_options/instandard/catalog.json",
          "error.dataset",
        ),
        json<EquipmentGroups>(
          "data/open_options/catalogs/equipment_groups.json",
          "error.japaneseEquipmentGroups",
        ),
      ]);
      if (instandardMode !== "open") {
        return { ...common, source, equipmentGroups };
      }
      const [instandardOpenCsv, openMetadata] = await Promise.all([
        text(
          "data/open_options/instandard/open_option_rows.csv",
          "error.instandardOpenCsv",
        ),
        json<OpenMetadata>(
          "data/open_options/catalogs/open_metadata.json",
          "error.japaneseOpenMetadata",
        ),
      ]);
      return {
        ...common,
        source,
        equipmentGroups,
        instandardOpenRows: prepareInstandardOpenRows(
          instandardOpenCsv,
          optionTags,
        ),
        openMetadata,
      };
    };
    load()
      .then((loaded) => {
        if (!cancelled) setResources(loaded);
      })
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
  }, [instandardMode, view]);

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
        onClick={() => {
          window.location.assign(pageUrl("ko", view, instandardMode));
        }}
      >
        한국어
      </button>
      <button
        type="button"
        className={language === "ja" ? "active" : ""}
        aria-pressed={language === "ja"}
        onClick={() => {
          window.location.assign(pageUrl("ja", view, instandardMode));
        }}
      >
        日本語
      </button>
    </div>
  );
  const themeButton = (
    <button
      className="theme"
      onClick={() => {
        const current =
          document.documentElement.dataset.theme === "light"
            ? "light"
            : "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.dataset.theme = next;
        localStorage.setItem("redstone-ui-theme", next);
      }}
    >
      <span className="theme-action-dark">
        ☀ {uiText(language, "theme.light")}
      </span>
      <span className="theme-action-light">
        ☾ {uiText(language, "theme.dark")}
      </span>
    </button>
  );
  const headerControls = (
    <>
      {languageSelector}
      {themeButton}
    </>
  );
  const footer = (
    <Footer
      language={language}
      updatedDate={dataUpdatedDate}
      formattedUpdatedDate={formattedDataUpdatedDate}
      centered={view === "home"}
    />
  );

  if (view === "home") {
    return <><Home language={language} controls={headerControls} />{footer}</>;
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
        {footer}
      </>
    );
  }
  if (!resources) {
    return (
      <>
        <PageHeader
          language={language}
          title={staticTitle ?? uiText(language, "loading.title")}
          description={staticDescription ?? uiText(language, "loading.description")}
          controls={headerControls}
        />
        <main>
          <div className="empty">{uiText(language, "loading.progress")}</div>
        </main>
        {footer}
      </>
    );
  }
  if (view === "open") {
    return (
      <><OpenViewer
        rows={resources.openRows!}
        language={language}
        optionLocales={resources.optionLocales!}
        openEquipmentBuckets={resources.openEquipmentBuckets!}
        openMetadata={resources.openMetadata!}
        optionTags={resources.optionTags!}
        themeButton={headerControls}
      />{footer}</>
    );
  }
  if (view === "instandard" && instandardMode === "tier") {
    return (
      <><InstandardTierViewer
        source={resources.source!}
        language={language}
        optionLocales={resources.optionLocales!}
        equipmentGroups={resources.equipmentGroups!}
        optionTags={resources.optionTags!}
        controls={headerControls}
      />{footer}</>
    );
  }
  if (view === "instandard" && instandardMode === "option") {
    return (
      <><InstandardOptionViewer
        source={resources.source!}
        language={language}
        optionLocales={resources.optionLocales!}
        equipmentGroups={resources.equipmentGroups!}
        optionTags={resources.optionTags!}
        controls={headerControls}
      />{footer}</>
    );
  }
  if (view === "instandard" && instandardMode === "open") {
    return (
      <><InstandardOpenViewer
        source={resources.source!}
        openRows={resources.instandardOpenRows!}
        language={language}
        optionLocales={resources.optionLocales!}
        equipmentGroups={resources.equipmentGroups!}
        openMetadata={resources.openMetadata!}
        optionTags={resources.optionTags!}
        controls={headerControls}
      />{footer}</>
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
          <a
            className="home-open-card feature-card--open"
            href={openOptionsUrl(language)}
          >
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
                  href={instandardUrl(language, item.mode)}
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

function Footer({
  language,
  updatedDate,
  formattedUpdatedDate,
  centered = false,
}: {
  language: Language;
  updatedDate?: string;
  formattedUpdatedDate?: string;
  centered?: boolean;
}) {
  const dataBasis = language === "ja"
    ? "日本クライアント基準"
    : "일본 클라이언트 기준";
  const updatedLabel = language === "ja"
    ? "最終データ更新"
    : "마지막 데이터 갱신";
  return (
    <footer className={`site-footer${centered ? " site-footer--centered" : ""}`}>
      {updatedDate && formattedUpdatedDate && (
        <p className="footer-data-basis">
          {dataBasis} · {updatedLabel}{" "}
          <time dateTime={updatedDate}>{formattedUpdatedDate}</time>
        </p>
      )}
      <div className="footer-disclosure">
        <p>{uiText(language, "footer.notice")}</p>
        <p>{uiText(language, "footer.english")}</p>
      </div>
    </footer>
  );
}
