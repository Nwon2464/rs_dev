import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { Icon } from "./components/Icon";
import { OpenViewer } from "./components/OpenViewer";
import { SelectedTagChips, TagFilterPanel } from "./components/TagFilterPanel";
import { equipmentIconId, featureIconId } from "./components/iconMap";
import { prepareGeneralOpenRows } from "./data/generalOpenOptions";
import {
  prepareInstandardOpenRows,
  type InstandardCatalog,
  type InstandardEquipment,
  type InstandardOpenOptionRow,
  type InstandardOption,
  type InstandardTier,
} from "./data/instandardOptions";
import { matchesSelectedTags, tagSearchText, tagText, toggleSelectedTag } from "./domain/openOptions/tags";
import { renderTemplate } from "./domain/openOptions/renderTemplate";
import { titleTemplate } from "./domain/openOptions/placeholders";
import type {
  EquipmentGroups,
  GeneralOpenOptionRow,
  OpenEquipmentBuckets,
  OpenMetadata,
  OptionLocales,
  OptionTagData,
} from "./domain/openOptions/types";
import {
  formatActiveTierSummary,
  formatAppliedEquipmentCount,
  formatCandidateCount,
  formatEquipmentOpenTitle,
  formatEquipmentOptionTitle,
  formatIncompleteWarning,
  formatIncompleteWarningTitle,
  formatOpenSlot,
  formatPossibleValueCount,
  formatRangeSubtitle,
  formatResultCount,
  formatTierOptionsTitle,
  formatTierValuesTitle,
  loadLanguage,
  saveLanguage,
  uiText,
  type Language,
  type UiMessageKey,
} from "./i18n";
import "./styles.css";

type View = "home" | "instandard" | "open";
type Theme = "light" | "dark";
type InstandardMode = "option" | "open" | "tier";

type Tier = InstandardTier;
type Equipment = InstandardEquipment;
type SourceDataset = InstandardCatalog;

type JapaneseBaseOptions = Record<string, string>;
type JapaneseEquipmentGroups = EquipmentGroups;
type ConverterConcept = "normal" | "improved" | "fake" | "burning" | "association";

const converterConceptByKey: Record<string, ConverterConcept> = {
  "일반 변환기": "normal", "개량된 변환기": "improved", "모조 변환기": "fake", "불타는 변환기": "burning", "협회 변환기": "association",
  일반: "normal", 개량: "improved", 모조: "fake", 불타는: "burning",
  normal: "normal", improved: "improved", fake: "fake", burning: "burning", association: "association",
};

function localizedEquipmentName(itemGroupId: number, koreanName: string, language: Language, japaneseEquipmentGroups: JapaneseEquipmentGroups): string {
  return language === "ja" ? japaneseEquipmentGroups[String(itemGroupId)] ?? koreanName : koreanName;
}

function localizedConverterLabel(internalKey: string, language: Language, openMetadata: OpenMetadata): string {
  const concept = converterConceptByKey[internalKey];
  return concept ? openMetadata.converters[concept]?.[language] ?? internalKey : internalKey;
}

function optionTemplate(option: InstandardOption, language: Language, optionLocales: OptionLocales): string {
  const template = optionLocales[language][String(option.option_id)];
  if (!template) throw new Error(`missing ${language} template for option_id=${option.option_id}`);
  return template;
}

function optionBindings(source: SourceDataset, optionId: number): Record<string, number> {
  return source.value_bindings[String(optionId)] ?? {};
}

function localizedDisplayName(option: InstandardOption, language: Language, optionLocales: OptionLocales, source: SourceDataset): string {
  return titleTemplate(optionTemplate(option, language, optionLocales), optionBindings(source, option.option_id));
}

function localizedInstandardOpenOptionRow(
  row: InstandardOpenOptionRow,
  language: Language,
  optionLocales: OptionLocales,
  source: SourceDataset,
): { title: string; display: string } {
  const template = optionLocales[language][row.option_id];
  if (!template) throw new Error(`missing ${language} template for option_id=${row.option_id}`);
  const bindings = optionBindings(source, Number(row.option_id));
  return {
    title: titleTemplate(template, bindings),
    display: renderTemplate(template, [Number(row.value_0), Number(row.value_1)], bindings),
  };
}

function candidateValues(option: InstandardOption, language: Language, optionLocales: OptionLocales, source: SourceDataset): string[] {
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(source, option.option_id);
  return [...new Set(option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.rolls.map((vector) => renderTemplate(template, vector, bindings))))];
}

function tierCandidateValues(option: InstandardOption, tier: Tier, language: Language, optionLocales: OptionLocales, source: SourceDataset): string[] {
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(source, option.option_id);
  return [...new Set(tier.rolls.map((vector) => renderTemplate(template, vector, bindings)))];
}

function rangeLabel(option: InstandardOption, language: Language, optionLocales: OptionLocales, source: SourceDataset): string {
  const vectors = option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.rolls);
  const values = vectors.map((vector) => vector[0]);
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(source, option.option_id);
  const minimum = renderTemplate(template, vectors[values.indexOf(Math.min(...values))], bindings);
  const maximum = renderTemplate(template, vectors[values.indexOf(Math.max(...values))], bindings);
  return minimum === maximum ? minimum : `${minimum} ~ ${maximum}`;
}

function App() {
  const params = new URLSearchParams(window.location.search);
  const requested = params.get("view");
  const view: View = requested === "open" || requested === "instandard" ? requested : "home";
  const requestedMode = params.get("mode");
  const instandardMode: InstandardMode | null = requestedMode === "option" || requestedMode === "open" || requestedMode === "tier" ? requestedMode : null;
  const [theme, setTheme] = useState<Theme>(() => localStorage.getItem("redstone-ui-theme") === "dark" ? "dark" : "light");
  const [language, setLanguage] = useState<Language>(
    () => loadLanguage(localStorage),
  );
  const [resources, setResources] = useState<{ source: SourceDataset; openRows: GeneralOpenOptionRow[]; instandardOpenRows: InstandardOpenOptionRow[]; optionLocales: OptionLocales; japaneseEquipmentGroups: JapaneseEquipmentGroups; openEquipmentBuckets: OpenEquipmentBuckets; openMetadata: OpenMetadata; optionTags: OptionTagData } | null>(null);
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
      fetch(`${base}data/open_options/instandard/catalog.json`).then((response) => {
        if (!response.ok) throw new Error("error.dataset");
        return response.json() as Promise<SourceDataset>;
      }),
      fetch(`${base}data/open_options/general/open_option_rows.csv`).then((response) => {
        if (!response.ok) throw new Error("error.openCsv");
        return response.text();
      }),
      fetch(`${base}data/open_options/instandard/open_option_rows.csv`).then((response) => {
        if (!response.ok) throw new Error("error.instandardOpenCsv");
        return response.text();
      }),
      fetch(`${base}data/open_options/i18n/ko/base_options.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOptions");
        return response.json() as Promise<JapaneseBaseOptions>;
      }),
      fetch(`${base}data/open_options/i18n/ja/base_options.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOptions");
        return response.json() as Promise<JapaneseBaseOptions>;
      }),
      fetch(`${base}data/open_options/catalogs/equipment_groups.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseEquipmentGroups");
        return response.json() as Promise<JapaneseEquipmentGroups>;
      }),
      fetch(`${base}data/open_options/catalogs/open_equipment_buckets.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOpenEquipmentBuckets");
        return response.json() as Promise<OpenEquipmentBuckets>;
      }),
      fetch(`${base}data/open_options/catalogs/open_metadata.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOpenMetadata");
        return response.json() as Promise<OpenMetadata>;
      }),
      fetch(`${base}data/open_options/catalogs/option_tags.json`).then((response) => {
        if (!response.ok) throw new Error("error.optionTags");
        return response.json() as Promise<OptionTagData>;
      }),
    ]).then(([rawSource, csv, instandardOpenCsv, koreanBaseOptions, japaneseBaseOptions, japaneseEquipmentGroups, openEquipmentBuckets, openMetadata, optionTags]) => {
      if (!cancelled) setResources({ source: rawSource, openRows: prepareGeneralOpenRows(csv, optionTags), instandardOpenRows: prepareInstandardOpenRows(instandardOpenCsv), optionLocales: { ko: koreanBaseOptions, ja: japaneseBaseOptions }, japaneseEquipmentGroups, openEquipmentBuckets, openMetadata, optionTags });
    }).catch((error: unknown) => {
      if (!cancelled) setLoadError(error instanceof Error && error.message.startsWith("error.") ? error.message as UiMessageKey : "error.unknown");
    });
    return () => { cancelled = true; };
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
  const themeButton = <button className="theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? `☾ ${uiText(language, "theme.light")}` : `☀ ${uiText(language, "theme.dark")}`}</button>;
  const headerControls = (
    <>
      {languageSelector}
      {themeButton}
    </>
  );
  if (view === "home") return <Home language={language} themeButton={headerControls} />;
  if (loadError) return <><Header language={language} title={uiText(language, "error.title")} description={uiText(language, loadError)} themeButton={headerControls} /><main><Empty language={language} /></main></>;
  if (!resources) return <><Header language={language} title={uiText(language, "loading.title")} description={uiText(language, "loading.description")} themeButton={headerControls} /><main><div className="empty">{uiText(language, "loading.progress")}</div></main></>;
  if (view === "open") return <OpenViewer rows={resources.openRows} language={language} optionLocales={resources.optionLocales} openEquipmentBuckets={resources.openEquipmentBuckets} openMetadata={resources.openMetadata} optionTags={resources.optionTags} themeButton={headerControls} />;
  if (view === "instandard" && instandardMode === "tier") return <InstandardTierViewer source={resources.source} language={language} optionLocales={resources.optionLocales} japaneseEquipmentGroups={resources.japaneseEquipmentGroups} optionTags={resources.optionTags} themeButton={headerControls} />;
  if (view === "instandard" && (instandardMode === "option" || instandardMode === "open")) return <InstandardOpenViewer mode={instandardMode} source={resources.source} openRows={resources.instandardOpenRows} language={language} optionLocales={resources.optionLocales} japaneseEquipmentGroups={resources.japaneseEquipmentGroups} japaneseOpenMetadata={resources.openMetadata} optionTags={resources.optionTags} themeButton={headerControls} />;
  return null;
}

function Header({ language, title, description, themeButton, home = true }: { language: Language; title: string; description: string; themeButton: ReactNode; home?: boolean }) {
  return <header><div className="top"><div><h1>{title}</h1><p>{description}</p></div><div className="header-actions">{home && <a className="home" href="?">← {uiText(language, "common.home")}</a>}{themeButton}</div></div></header>;
}

function Home({ language, themeButton }: { language: Language; themeButton: ReactNode }) {
  return <><Header language={language} title={uiText(language, "app.title")} description={uiText(language, "app.description")} themeButton={themeButton} home={false} /><main className="home-main"><div className="home-landing-stack"><a className="home-open-card feature-card--open" href="?view=open"><div className="home-wide-card-copy"><Icon className="app-icon" id="feature-open-option" size={38} /><div><h2>{uiText(language, "home.open.title")}</h2><p>{uiText(language, "home.open.description")}</p></div></div><b>{uiText(language, "home.open.action")}</b></a><section className="home-instandard-panel" aria-labelledby="home-instandard-title"><div className="home-instandard-heading"><Icon className="app-icon" id="feature-instandard-option" size={38} /><div><h2 id="home-instandard-title">{uiText(language, "home.instandard.title")}</h2><p>{uiText(language, "home.instandard.description")}</p></div></div><div className="instandard-feature-cards home-instandard-feature-cards">{instandardModes.map((item) => <a className={`instandard-feature-card home-instandard-feature-card feature-card--${item.className}`} href={`?view=instandard&mode=${item.mode}`} key={item.mode}><Icon className="app-icon" id={featureIconId[item.iconLabel]} size={38} /><h2>{uiText(language, item.titleKey)}</h2><p>{uiText(language, item.descriptionKey)}</p><b>{uiText(language, "common.view")}</b></a>)}</div></section></div></main></>;
}

const instandardModes: { mode: InstandardMode; titleKey: UiMessageKey; descriptionKey: UiMessageKey; iconLabel: string; className: string }[] = [
  { mode: "option", titleKey: "mode.option.title", descriptionKey: "mode.option.description", iconLabel: "비규격 옵션", className: "option" },
  { mode: "open", titleKey: "mode.open.title", descriptionKey: "mode.open.description", iconLabel: "비규격 개방옵션", className: "open" },
  { mode: "tier", titleKey: "mode.tier.title", descriptionKey: "mode.tier.description", iconLabel: "티어별 옵션", className: "tier" },
];

function InstandardModeTabs({ mode, language }: { mode: InstandardMode; language: Language }) {
  return <nav className="instandard-mode-tabs" aria-label={uiText(language, "mode.navigation")}>{instandardModes.map((item) => <a className={`mode-tab mode-tab--${item.className} ${mode === item.mode ? "active" : ""}`} href={`?view=instandard&mode=${item.mode}`} aria-current={mode === item.mode ? "page" : undefined} key={item.mode}><Icon className="app-icon" id={featureIconId[item.iconLabel]} size={18} />{uiText(language, item.titleKey)}</a>)}</nav>;
}

function InstandardTierViewer({ source, language, optionLocales, japaneseEquipmentGroups, optionTags, themeButton }: { source: SourceDataset; language: Language; optionLocales: OptionLocales; japaneseEquipmentGroups: JapaneseEquipmentGroups; optionTags: OptionTagData; themeButton: ReactNode }) {
  const [selectedTier, setSelectedTier] = useState<number | null>(null);
  const [selectedTierTags, setSelectedTierTags] = useState<string[]>([]);
  const [tierQuery, setTierQuery] = useState("");
  const [expandedOptionIds, setExpandedOptionIds] = useState<Set<number>>(() => new Set());
  const tierNumbers = useMemo(() => [...new Set(source.options.flatMap((option) => option.tiers.filter((tier) => tier.enabled).map((tier) => tier.tier)))].sort((a, b) => a - b), [source.options]);
  const tierOptions = useMemo(() => selectedTier === null ? [] : source.options.filter((option) => option.tiers.some((tier) => tier.enabled && tier.tier === selectedTier)), [selectedTier, source.options]);
  const tierTags = useMemo(() => [...new Set(tierOptions.flatMap((option) => option.canonical_tags))].sort((a, b) => a.localeCompare(b, "ko")), [tierOptions]);
  const optionResults = useMemo(() => {
    if (selectedTier === null) return [];
    const normalized = tierQuery.trim().toLocaleLowerCase();
    return tierOptions
      .filter((option) => matchesSelectedTags(option.canonical_tags, selectedTierTags, optionTags))
      .map((option) => ({ option, equipment: source.equipment.filter((item) => item.option_ids.includes(option.option_id)) }))
      .filter(({ option, equipment }) => !normalized || [optionLocales.ko[String(option.option_id)], optionLocales.ja[String(option.option_id)], localizedDisplayName(option, "ko", optionLocales, source), localizedDisplayName(option, "ja", optionLocales, source), tagSearchText(option.canonical_tags, optionTags)].join(" ").toLocaleLowerCase().includes(normalized) || equipment.some((item) => [item.item_group_name, localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)].join(" ").toLocaleLowerCase().includes(normalized)));
  }, [japaneseEquipmentGroups, language, optionLocales, optionTags, selectedTier, selectedTierTags, source, tierOptions, tierQuery]);

  function changeTier(tierNumber: number) {
    setSelectedTier(tierNumber);
    setSelectedTierTags([]);
    setExpandedOptionIds(new Set());
  }

  function toggleOption(optionId: number) {
    setExpandedOptionIds((current) => {
      const next = new Set(current);
      if (next.has(optionId)) next.delete(optionId);
      else next.add(optionId);
      return next;
    });
  }

  return <>
    <Header language={language} title={uiText(language, "header.instandard.title")} description={uiText(language, "header.tier.description")} themeButton={themeButton} />
    <main className="instandard-mode-page instandard-tier-mode tier-mode-page">
      <InstandardModeTabs mode="tier" language={language} />
      <section className={`selection-panel tier-filter-panel ${selectedTier === null ? "tier-filter-awaiting" : ""}`} aria-label={uiText(language, "aria.tierFilters")}>
        <FilterGroup className="tier-number-filter" number="1" title={uiText(language, "filter.tier")}>
          {tierNumbers.map((tierNumber) => <Chip key={tierNumber} active={selectedTier === tierNumber} onClick={() => changeTier(tierNumber)}>Tier {tierNumber}</Chip>)}
        </FilterGroup>
        {selectedTier !== null && <>
          <FilterGroup className="tier-tag-filter" number="2" title={uiText(language, "filter.optionCategory")}>
            <TagFilterChips availableTags={tierTags} selectedTags={selectedTierTags} onChange={setSelectedTierTags} language={language} optionTags={optionTags} allLabelKey="common.allCategories" />
          </FilterGroup>
          <FilterGroup className="tier-search-filter" number="3" title={uiText(language, "common.search")}>
            <div className="panel-search-control"><input value={tierQuery} onChange={(event) => setTierQuery(event.target.value)} placeholder={uiText(language, "filter.equipmentOrOptionSearchPlaceholder")} aria-label={uiText(language, "filter.equipmentOrOptionSearchPlaceholder")} />{tierQuery && <button type="button" onClick={() => setTierQuery("")}>{uiText(language, "common.reset")}</button>}</div>
          </FilterGroup>
        </>}
      </section>
      {selectedTier === null ? <section className="tier-mode-empty"><Icon className="app-icon" id={featureIconId["티어별 옵션"]} size={34} /><h2>{uiText(language, "tier.selectPrompt")}</h2><p>{uiText(language, "tier.selectDescription")}</p></section> : <section className="tier-results">
        <ResultsHead language={language} title={formatTierOptionsTitle(language, selectedTier)} description={uiText(language, "tier.resultsDescription")} count={optionResults.length} />
        {optionResults.length ? <div className="tier-option-accordion-list">{optionResults.map(({ option, equipment }) => {
          const expanded = expandedOptionIds.has(option.option_id);
          const contentId = `tier-option-${option.option_id}`;
          const tierData = option.tiers.find((tier) => tier.enabled && tier.tier === selectedTier)!;
          const values = tierCandidateValues(option, tierData, language, optionLocales, source);
          return <article className={`tier-option-accordion ${expanded ? "expanded" : ""}`} key={option.option_id}>
            <button className="tier-option-toggle" type="button" aria-expanded={expanded} aria-controls={contentId} onClick={() => toggleOption(option.option_id)}><strong>{localizedDisplayName(option, language, optionLocales, source)}</strong><div className="option-tag-badges">{option.canonical_tags.map((optionTag) => <span key={optionTag}>{tagText(language, optionTag, optionTags)}</span>)}</div><span>{formatAppliedEquipmentCount(language, equipment.length)}</span><span>{formatPossibleValueCount(language, values.length)}</span><Icon className="app-icon tier-chevron" id={expanded ? "ui-chevron-down" : "ui-chevron-right"} size={18} /></button>
            {expanded && <section className="tier-option-content" id={contentId}>
              <div className="tier-option-values"><h3>{formatTierValuesTitle(language, selectedTier)}</h3><div className="value-list">{values.map((value) => <span key={value}>{value}</span>)}</div></div>
              <div className="tier-option-equipment"><h3>{uiText(language, "tier.appliedEquipment")}</h3><div className="tier-applied-equipment-grid">{equipment.map((item) => <div className="tier-applied-equipment" key={item.item_group_id}><Icon className="app-icon" id={equipmentIconId[item.item_group_name] ?? "feature-instandard-option"} size={20} /><span>{localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)}</span></div>)}</div></div>
            </section>}
          </article>;
        })}</div> : <Empty language={language} />}
      </section>}
    </main>
  </>;
}


function InstandardOpenViewer({ mode, source, openRows, language, optionLocales, japaneseEquipmentGroups, japaneseOpenMetadata, optionTags, themeButton }: { mode: "option" | "open"; source: SourceDataset; openRows: InstandardOpenOptionRow[]; language: Language; optionLocales: OptionLocales; japaneseEquipmentGroups: JapaneseEquipmentGroups; japaneseOpenMetadata: OpenMetadata; optionTags: OptionTagData; themeButton: ReactNode }) {
  const [equipmentName, setEquipmentName] = useState("헬멧");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [converter, setConverter] = useState<InstandardOpenOptionRow["converter_type"]>("normal");
  const [selectedOpenLines, setSelectedOpenLines] = useState<string[] | null>(null);
  const [query, setQuery] = useState("");
  const [equipmentPickerOpen, setEquipmentPickerOpen] = useState(false);
  const [equipmentQuery, setEquipmentQuery] = useState("");
  const [selectedOption, setSelectedOption] = useState<InstandardOption | null>(null);
  const equipmentToggleRef = useRef<HTMLButtonElement>(null);
  const equipmentPickerRef = useRef<HTMLElement>(null);
  const equipmentSearchRef = useRef<HTMLInputElement>(null);
  const openLines = ["1", "2", "3", "4"];
  const optionMap = useMemo(() => new Map(source.options.map((option) => [option.option_id, option])), [source]);
  const equipment = source.equipment.find((item) => item.item_group_name === equipmentName) ?? source.equipment[0];
  const equipmentDisplayName = localizedEquipmentName(equipment.item_group_id, equipment.item_group_name, language, japaneseEquipmentGroups);
  const options = useMemo(() => equipment.option_ids.map((id) => optionMap.get(id)).filter((option): option is InstandardOption => Boolean(option)), [equipment]);
  const tags = useMemo(() => [...new Set(options.flatMap((option) => option.canonical_tags))].sort((a, b) => a.localeCompare(b, "ko")), [options]);
  const filteredEquipment = useMemo(() => {
    const normalized = equipmentQuery.trim().toLocaleLowerCase();
    return source.equipment.filter((item) => !normalized || [item.item_group_name, localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)].join(" ").toLocaleLowerCase().includes(normalized));
  }, [equipmentQuery, japaneseEquipmentGroups, language, source.equipment]);
  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return options.filter((option) => matchesSelectedTags(option.canonical_tags, selectedTags, optionTags) && (!normalized || [optionLocales.ko[String(option.option_id)], optionLocales.ja[String(option.option_id)], localizedDisplayName(option, "ko", optionLocales, source), localizedDisplayName(option, "ja", optionLocales, source), tagSearchText(option.canonical_tags, optionTags)].join(" ").toLocaleLowerCase().includes(normalized)));
  }, [optionLocales, optionTags, options, query, selectedTags, source]);
  const equipmentOpenRows = useMemo(() => openRows.filter((row) => Number(row.item_group_id) === equipment.item_group_id), [equipment.item_group_id, openRows]);
  const localizedOpenRows = useMemo(() => new Map(equipmentOpenRows.map((row) => [row, localizedInstandardOpenOptionRow(row, language, optionLocales, source)])), [equipmentOpenRows, language, optionLocales, source]);
  const converters = useMemo(() => ["normal", "improved", "fake", "burning"].filter((value) => equipmentOpenRows.some((row) => row.converter_type === value)) as InstandardOpenOptionRow["converter_type"][], [equipmentOpenRows]);
  const effectiveOpenLines = selectedOpenLines ?? openLines;
  const filteredOpenRows = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return equipmentOpenRows
      .filter((row) => {
        const localized = localizedOpenRows.get(row);
        return converter === row.converter_type && effectiveOpenLines.includes(row.open_slot) && (!normalized || [optionLocales.ko[row.option_id], optionLocales.ja[row.option_id], localized?.title, localized?.display, row.option_id, row.converter_type, localizedConverterLabel(row.converter_type, "ko", japaneseOpenMetadata), localizedConverterLabel(row.converter_type, "ja", japaneseOpenMetadata)].join(" ").toLocaleLowerCase().includes(normalized));
      })
      .sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [converter, effectiveOpenLines, equipmentOpenRows, japaneseOpenMetadata, localizedOpenRows, optionLocales, query]);
  const openGroups = new Map(openLines.map((line) => [line, filteredOpenRows.filter((row) => row.open_slot === line)]));
  const selectedOpenLineLabel = selectedOpenLines === null ? "ALL" : selectedOpenLines.map((line) => formatOpenSlot(language, line)).join(" · ");

  useEffect(() => {
    if (!equipmentPickerOpen) return;
    equipmentSearchRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeEquipmentPicker();
    };
    const closeOnOutsideClick = (event: PointerEvent) => {
      const target = event.target as Node;
      if (!equipmentPickerRef.current?.contains(target) && !equipmentToggleRef.current?.contains(target)) closeEquipmentPicker();
    };
    document.addEventListener("keydown", closeOnEscape);
    document.addEventListener("pointerdown", closeOnOutsideClick);
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.removeEventListener("pointerdown", closeOnOutsideClick);
    };
  }, [equipmentPickerOpen]);

  function closeEquipmentPicker() {
    setEquipmentPickerOpen(false);
    setEquipmentQuery("");
    requestAnimationFrame(() => equipmentToggleRef.current?.focus());
  }

  function changeEquipment(name: string) {
    const nextEquipment = source.equipment.find((item) => item.item_group_name === name);
    const nextConverters = openRows
      .filter((row) => Number(row.item_group_id) === nextEquipment?.item_group_id)
      .map((row) => row.converter_type);
    setEquipmentName(name);
    setSelectedTags([]);
    closeEquipmentPicker();
    if (!nextConverters.includes(converter)) setConverter(nextConverters[0] ?? converter);
    setSelectedOpenLines(null);
    setQuery("");
    setSelectedOption(null);
  }

  function toggleOpenLine(value: string) {
    if (value === "ALL") {
      setSelectedOpenLines(null);
    } else {
      const current = selectedOpenLines ?? [];
      const next = current.includes(value)
        ? current.filter((line) => line !== value)
        : [...current, value].sort((a, b) => Number(a) - Number(b));
      setSelectedOpenLines(next.length ? next : null);
    }
    setQuery("");
  }

  const formatProbability = (value: string) => Number(value).toLocaleString("ko-KR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

  return <>
    <Header language={language} title={uiText(language, "header.instandard.title")} description={uiText(language, "header.instandard.description")} themeButton={themeButton} />
    <main className={`instandard-mode-page instandard-${mode}-mode`}>
      <InstandardModeTabs mode={mode} language={language} />
      {mode === "option" ? <section className="selection-panel instandard-option-toolbar" aria-label={uiText(language, "aria.optionFilters")}>
        <FilterGroup className="option-equipment-filter" number="1" title={uiText(language, "filter.equipment")}>
          <div className="selected-equipment-card">
            <Icon className="app-icon" id={equipmentIconId[equipment.item_group_name] ?? "feature-instandard-option"} size={24} />
            <strong>{equipmentDisplayName}</strong>
            <button ref={equipmentToggleRef} type="button" aria-expanded={equipmentPickerOpen} aria-controls="instandard-equipment-picker" onClick={() => equipmentPickerOpen ? closeEquipmentPicker() : setEquipmentPickerOpen(true)}>{uiText(language, equipmentPickerOpen ? "filter.collapseEquipment" : "filter.changeEquipment")}</button>
          </div>
        </FilterGroup>
        <FilterGroup className="option-search-filter" number="2" title={uiText(language, "filter.optionSearch")}>
          <div className="panel-search-control"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={uiText(language, "filter.optionSearchPlaceholder")} aria-label={uiText(language, "filter.optionSearch")} />{query && <button type="button" onClick={() => setQuery("")}>{uiText(language, "common.reset")}</button>}</div>
        </FilterGroup>
        {equipmentPickerOpen && <section ref={equipmentPickerRef} className="equipment-picker-floating" id="instandard-equipment-picker" role="dialog" aria-label={uiText(language, "filter.equipment")}>
          <div className="equipment-picker-head"><h3>{uiText(language, "filter.equipment")}</h3><button type="button" aria-label={uiText(language, "filter.closeEquipment")} onClick={closeEquipmentPicker}>×</button></div>
          <label className="equipment-name-search"><span className="visually-hidden">{uiText(language, "filter.equipmentSearch")}</span><input ref={equipmentSearchRef} value={equipmentQuery} onChange={(event) => setEquipmentQuery(event.target.value)} placeholder={uiText(language, "filter.equipmentSearchPlaceholder")} /></label>
          <div className="equipment-icon-grid">{filteredEquipment.map((item) => <button type="button" className={`equipment-picker-item ${equipment.item_group_id === item.item_group_id ? "active" : ""}`} aria-pressed={equipment.item_group_id === item.item_group_id} onClick={() => changeEquipment(item.item_group_name)} key={item.item_group_id}><Icon className="app-icon" id={equipmentIconId[item.item_group_name] ?? "feature-instandard-option"} size={20} /><span>{localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)}</span></button>)}</div>
          {!filteredEquipment.length && <p className="equipment-picker-empty">{uiText(language, "common.noSearchResults")}</p>}
        </section>}
      </section> : <section className="selection-panel instandard-panel inst-open-panel" aria-label={uiText(language, "aria.openFilters")}>
          <FilterGroup number="1" title={uiText(language, "filter.equipment")}>
            {source.equipment.map((item) => <Chip key={item.item_group_id} active={equipment.item_group_id === item.item_group_id} onClick={() => changeEquipment(item.item_group_name)}><span className="inst-open-equipment-chip"><Icon className="app-icon" id={equipmentIconId[item.item_group_name] ?? "feature-instandard-option"} size={18} />{localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)}</span></Chip>)}
          </FilterGroup>
          <FilterGroup number="2" title={uiText(language, "filter.converter")}>
            {converters.map((value) => <Chip key={value} active={converter === value} onClick={() => { setConverter(value); setQuery(""); }}>{localizedConverterLabel(value, language, japaneseOpenMetadata)}</Chip>)}
          </FilterGroup>
          <FilterGroup number="3" title={uiText(language, "filter.openSlot")}>
            <Chip active={selectedOpenLines === null} onClick={() => toggleOpenLine("ALL")}>ALL</Chip>
            {openLines.map((value) => <Chip key={value} active={selectedOpenLines?.includes(value) ?? false} onClick={() => toggleOpenLine(value)}>{value}</Chip>)}
          </FilterGroup>
      </section>}
      {mode === "option" ? <>
        <TagFilterPanel availableTags={tags} selectedTags={selectedTags} onChange={setSelectedTags} language={language} optionTags={optionTags} />
        <Context language={language} breadcrumb={`${equipmentDisplayName} › ${uiText(language, "mode.option.title")} › ${selectedTagLabel(selectedTags, language, optionTags, "common.allCategories")}`} query={query} onQuery={setQuery} placeholder={uiText(language, "filter.currentOptionSearch")} hideSearch />
        <ResultsHead language={language} title={formatEquipmentOptionTitle(language, equipmentDisplayName)} description={uiText(language, "option.resultsDescription")} count={filteredOptions.length} />
        <SelectedTagChips selectedTags={selectedTags} onChange={setSelectedTags} language={language} optionTags={optionTags} />
        {filteredOptions.length ? <section className="option-section instandard-option-results-section"><div className="table-wrap"><table className="instandard-option-results"><thead><tr><th>{uiText(language, "option.name")}</th><th>{uiText(language, "option.category")}</th><th>{uiText(language, "option.range")}</th><th>{uiText(language, "option.tierDetails")}</th></tr></thead><tbody>{filteredOptions.map((option) => <tr key={option.option_id}><td><strong>{localizedDisplayName(option, language, optionLocales, source)}</strong>{equipment.supplemental_option_ids.includes(option.option_id) && <em>{uiText(language, "option.supplemental")}</em>}</td><td><div className="option-tag-badges">{option.canonical_tags.map((optionTag) => <span key={optionTag}>{tagText(language, optionTag, optionTags)}</span>)}</div></td><td><span className="option-range-text">{rangeLabel(option, language, optionLocales, source)}</span></td><td><div className="tier-detail-group"><button className="tier-detail-button" onClick={() => setSelectedOption(option)}>{uiText(language, "option.viewTierValues")}</button><small>{formatPossibleValueCount(language, candidateValues(option, language, optionLocales, source).length)}</small></div></td></tr>)}</tbody></table></div></section> : <Empty language={language} />}
      </> : <>
        <Context language={language} breadcrumb={`${equipmentDisplayName} › ${uiText(language, "mode.open.title")} › ${localizedConverterLabel(converter, language, japaneseOpenMetadata)} › ${selectedOpenLineLabel}`} query={query} onQuery={setQuery} placeholder={uiText(language, "filter.currentOpenSearch")} />
        <ResultsHead language={language} title={formatEquipmentOpenTitle(language, equipmentDisplayName)} description={uiText(language, "instandardOpen.resultsDescription")} count={filteredOpenRows.length} />
        {filteredOpenRows.length ? openLines.filter((line) => (openGroups.get(line)?.length ?? 0) > 0).map((line) => {
          const group = openGroups.get(line) ?? [];
          const probabilitySum = group.reduce((sum, row) => sum + Number(row.probability), 0);
          const anomaly = Math.abs(probabilitySum - 100) > 0.06;
          const missingProbability = anomaly ? 100 - probabilitySum : 0;
          return <section className="option-section instandard-open-section" key={line}>
            <SectionHead title={formatOpenSlot(language, line)} count={formatCandidateCount(language, group.length)} />
            {anomaly && <aside className="probability-warning"><strong>{formatIncompleteWarningTitle(language, line)}</strong><span>{formatIncompleteWarning(language, formatProbability(String(probabilitySum)), formatProbability(String(missingProbability))).map((message, index) => <span key={message}>{message}{index < 2 && <br />}</span>)}</span></aside>}
            <div className="table-wrap"><table className="instandard-open-table"><thead><tr><th>{uiText(language, "instandardOpen.optionName")}</th><th>{uiText(language, "instandardOpen.value")}</th><th>{uiText(language, "instandardOpen.probability")}</th><th>{uiText(language, "instandardOpen.internalTier")}</th></tr></thead><tbody>
              {group.map((row) => { const localized = localizedOpenRows.get(row)!; return <tr key={`${row.source_block_index}-${row.source_file_offset}`}><td><strong>{localized.title}</strong></td><td>{localized.display}</td><td><b className="probability">{formatProbability(row.probability)}%</b></td><td><span className="tier">{row.tier}</span></td></tr>; })}
            </tbody></table></div>
          </section>;
        }) : <Empty language={language} />}
      </>}
    </main>
    {mode === "option" && selectedOption && <Modal language={language} title={localizedDisplayName(selectedOption, language, optionLocales, source)} subtitle={formatRangeSubtitle(language, rangeLabel(selectedOption, language, optionLocales, source))} onClose={() => setSelectedOption(null)}><p>{formatActiveTierSummary(language, selectedOption.tiers.filter((tier) => tier.enabled).length, candidateValues(selectedOption, language, optionLocales, source).length)}</p><div className="tier-value-groups">{selectedOption.tiers.filter((tier) => tier.enabled).map((tier) => <section className="tier-value-group" key={tier.tier}><h3>Tier {tier.tier}</h3><div className="value-list">{tierCandidateValues(selectedOption, tier, language, optionLocales, source).map((value) => <span key={`${tier.tier}-${value}`}>{value}</span>)}</div></section>)}</div></Modal>}
  </>;
}

function FilterGroup({ number, title, children, className = "" }: { number: string; title: string; children: ReactNode; className?: string }) { return <section className={`filter-group ${className}`}><h2><span>{number}</span>{title}</h2><div className="chip-grid">{children}</div></section>; }
function Chip({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) { return <button className={`chip ${active ? "active" : ""}`} aria-pressed={active} onClick={onClick}>{children}</button>; }
function selectedTagLabel(selectedTags: string[], language: Language, optionTags: OptionTagData, allLabelKey: UiMessageKey): string { return selectedTags.length ? selectedTags.map((tag) => tagText(language, tag, optionTags)).join(" · ") : uiText(language, allLabelKey); }
function TagFilterChips({ availableTags, selectedTags, onChange, language, optionTags, allLabelKey }: { availableTags: string[]; selectedTags: string[]; onChange: (tags: string[]) => void; language: Language; optionTags: OptionTagData; allLabelKey: UiMessageKey }) {
  const groups = Object.entries(optionTags.groups).map(([groupId, labels]) => ({
    groupId,
    label: labels[language],
    tags: availableTags.filter((tag) => optionTags.tags[tag]?.group === groupId),
  })).filter((group) => group.tags.length);
  return <><Chip active={!selectedTags.length} onClick={() => onChange([])}>{uiText(language, allLabelKey)}</Chip>{groups.map((group) => <div className="tag-filter-group" key={group.groupId}><small>{group.label}</small><div>{group.tags.map((tag) => <Chip key={tag} active={selectedTags.includes(tag)} onClick={() => onChange(toggleSelectedTag(selectedTags, tag))}>{tagText(language, tag, optionTags)}</Chip>)}</div></div>)}</>;
}
function Context({ language, breadcrumb, query, onQuery, placeholder, hideSearch = false }: { language: Language; breadcrumb: string; query: string; onQuery: (value: string) => void; placeholder: string; hideSearch?: boolean }) { return <section className={`context-row ${hideSearch ? "breadcrumb-only" : ""}`}><div className="breadcrumb">{uiText(language, "common.currentLocation")} <b>{breadcrumb}</b></div>{!hideSearch && <label className="search"><span className="visually-hidden">{uiText(language, "filter.optionSearch")}</span><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={placeholder} /></label>}</section>; }
function ResultsHead({ language, title, description, count }: { language: Language; title: string; description: string; count: number }) { return <section className="results-head"><div><h2>{title}</h2><p>{description}</p></div><b>{formatResultCount(language, count)}</b></section>; }
function SectionHead({ title, count }: { title: string; count: string }) { return <div className="option-section-head"><h3>{title}</h3><span>{count}</span></div>; }
function Empty({ language }: { language: Language }) { return <div className="empty">{uiText(language, "common.noResults")}</div>; }

function Modal({ language, title, subtitle, children, onClose }: { language: Language; title: string; subtitle: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className="candidate-dialog" onCancel={onClose} onClick={(event) => { if (event.currentTarget === event.target) onClose(); }}><div className="dialog-inner"><div className="dialog-head"><div><h2>{title}</h2><p>{subtitle}</p></div><button aria-label={uiText(language, "common.close")} onClick={onClose}>×</button></div>{children}</div></dialog>;
}

createRoot(document.getElementById("root")!).render(<App />);
