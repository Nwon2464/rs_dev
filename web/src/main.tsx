import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { Icon } from "./components/Icon";
import { equipmentIconId, featureIconId } from "./components/iconMap";
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
  formatTierLevel,
  formatTierOptionsTitle,
  formatTierValuesTitle,
  loadLanguage,
  saveLanguage,
  tagText,
  uiText,
  type Language,
  type UiMessageKey,
} from "./i18n";
import "./styles.css";

type Roll = [number, number, number];
type View = "home" | "instandard" | "open";
type Theme = "light" | "dark";
type InstandardMode = "option" | "open" | "tier";

type Tier = {
  tier: number;
  raw_tier_index: number;
  option_level_group_index: number | null;
  enabled: boolean;
  roll_values: Roll[];
};

type InstandardOption = {
  option_id: number;
  name: string;
  description: string;
  short_text: string;
  tags: string[];
  tiers: Tier[];
};

type Equipment = {
  item_group_id: number;
  item_group_name: string;
  option_ids: number[];
  supplemental_option_ids: number[];
};

type SourceDataset = {
  equipment: Equipment[];
  options: InstandardOption[];
};

type JapaneseBaseOptions = Record<string, string>;
type JapaneseEquipmentGroups = Record<string, string>;
type JapaneseOpenEquipmentBuckets = Record<string, string>;
type ConverterConcept = "normal" | "improved" | "replica" | "burning" | "association";
type JapaneseOpenMetadata = {
  grades: Record<string, string>;
  converters: Record<ConverterConcept, string>;
};

type OpenOptionRow = {
  converter_type: string;
  converter_probability: string;
  converter_probability_source: string;
  equipment_bucket: string;
  item_group_ids: string;
  item_group_names: string;
  grade_code: string;
  grade_name: string;
  section_group: string;
  open_slot: string;
  candidate_index: string;
  option_id: string;
  option_name: string;
  option_value_arity: string;
  option_display: string;
  value_raw: string;
  value_0_low16: string;
  value_1_high16: string;
  normal_probability: string;
  improved_probability: string;
  option_tier: string;
  probability_sum_valid: string;
  source_file_name: string;
  source_block_index: string;
  source_file_offset: string;
  mapping_basis: string;
  mapping_confidence: string;
  option_display_name: string;
  tags: string[];
};

type InstandardOpenOptionRow = {
  item_group_id: string;
  item_group_name: string;
  bucket_signature_index: string;
  bucket_group_ids: string;
  bucket_group_names: string;
  converter_type: "일반" | "개량" | "모조" | "불타는";
  mapping_status: "screen_confirmed" | "structural_candidate";
  section_type: string;
  section_group: string;
  open_slot: string;
  candidate_index: string;
  option_id: string;
  option_name: string;
  option_value_arity: string;
  option_display: string;
  value_raw: string;
  value_0_low16: string;
  value_1_high16: string;
  option_tier: string;
  probability: string;
  probability_source: string;
  slot_probability_sum: string;
  probability_sum_valid: "true" | "false";
  source_file_name: string;
  source_block_index: string;
  source_file_offset: string;
};

type LocalizableOpenOptionRow = {
  option_id: string;
  option_name: string;
  option_display_name?: string;
  option_value_arity: string;
  option_display: string;
  value_0_low16: string;
  value_1_high16: string;
};

const converterOrder = new Map(["일반 변환기", "개량된 변환기", "모조 변환기", "불타는 변환기", "협회 변환기"].map((name, index) => [name, index]));
const converterConceptByKey: Record<string, ConverterConcept> = {
  "일반 변환기": "normal", "개량된 변환기": "improved", "모조 변환기": "replica", "불타는 변환기": "burning", "협회 변환기": "association",
  일반: "normal", 개량: "improved", 모조: "replica", 불타는: "burning",
};
const koreanConverterLabels: Record<string, string> = {
  "일반 변환기": "개방옵션변환기", "개량된 변환기": "개방옵션변환기改", "모조 변환기": "모조변환기", "불타는 변환기": "불타는변환기", "협회 변환기": "협회변환기",
  일반: "개방옵션변환기", 개량: "개방옵션변환기改", 모조: "모조변환기", 불타는: "불타는변환기",
};
const openEquipmentIconAliases: Record<string, string> = {
  "귀걸이/망토": "귀걸이",
  "장갑/팔찌": "장갑",
  "전용 갑옷": "공용 갑옷",
  "무기": "한 손 검",
};

function openEquipmentIconId(equipmentName: string): string {
  return equipmentIconId[equipmentName] ?? equipmentIconId[openEquipmentIconAliases[equipmentName]] ?? "feature-open-option";
}

function parseCsv(value: string): Record<string, string>[] {
  const table: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < value.length; index += 1) {
    const character = value[index];
    if (quoted) {
      if (character === '"' && value[index + 1] === '"') { field += '"'; index += 1; }
      else if (character === '"') quoted = false;
      else field += character;
    } else if (character === '"') quoted = true;
    else if (character === ",") { row.push(field); field = ""; }
    else if (character === "\n") { row.push(field.replace(/\r$/, "")); table.push(row); row = []; field = ""; }
    else field += character;
  }
  if (field || row.length) { row.push(field); table.push(row); }
  const [rawHeader, ...rows] = table;
  const header = rawHeader.map((name, index) => index === 0 ? name.replace(/^\uFEFF/, "") : name);
  return rows.filter((values) => values.length === header.length).map((values) => Object.fromEntries(header.map((name, index) => [name, values[index]])));
}

function inferredTags(optionName: string): string[] {
  const tags: string[] = [];
  const name = optionName.replaceAll(" ", "");
  if (name.includes("소환수") || name.includes("펫") || name.includes("조련")) tags.push("소환수/펫");
  if (name.startsWith("vs")) tags.push("대상", "피해");
  if (name.toLocaleLowerCase().includes("pvp")) tags.push("PvP");
  if (["힘", "민첩", "건강", "지혜", "지식", "카리스마", "운", "능력치"].some((word) => name.includes(word))) tags.push("스탯");
  if (["체력", "CP", "마나"].some((word) => name.includes(word))) tags.push("자원");
  if (name.includes("속도")) tags.push("속도");
  if (["치명", "강타"].some((word) => name.includes(word))) tags.push("치명타");
  if (["흡수", "흡혈"].some((word) => name.includes(word))) tags.push("흡수");
  if (["저항", "방어", "피격", "감소"].some((word) => name.includes(word))) tags.push("방어");
  if (["공격력", "대미지", "즉사"].some((word) => name.includes(word))) tags.push("피해");
  if (name.includes("물리")) tags.push("물리");
  if (name.includes("마법") || name.includes("속성")) tags.push("속성");
  if (name.includes("착용레벨")) tags.push("착용 조건");
  return [...new Set(tags.length ? tags : ["기타"])];
}

function prepareOpenRows(csv: string, source: SourceDataset): OpenOptionRow[] {
  const knownTags = new Map(source.options.map((option) => [String(option.option_id), option.tags]));
  const rows = parseCsv(csv).map((raw) => ({
    ...raw,
    option_display_name: raw.option_name.endsWith("P") ? raw.option_name.slice(0, -1) : raw.option_name,
    tags: knownTags.get(raw.option_id) ?? inferredTags(raw.option_name),
  })) as OpenOptionRow[];
  const requiredFields = ["converter_type", "equipment_bucket", "grade_code", "open_slot", "option_id", "option_display", "converter_probability"] as const;
  if (!rows.length || rows.some((row) => requiredFields.some((field) => !row[field]?.trim()))) {
    throw new Error("개방 옵션 데이터에 필수 필드가 없거나 비어 있습니다.");
  }
  return rows;
}

function prepareInstandardOpenRows(csv: string): InstandardOpenOptionRow[] {
  const rows = parseCsv(csv) as unknown as InstandardOpenOptionRow[];
  const requiredFields = ["item_group_id", "converter_type", "mapping_status", "open_slot", "option_id", "option_display", "probability", "option_tier"] as const;
  if (!rows.length || rows.some((row) => requiredFields.some((field) => !row[field]?.trim()))) {
    throw new Error("비규격 개방옵션 데이터에 필수 필드가 없거나 비어 있습니다.");
  }
  return rows;
}

function displayName(option: InstandardOption): string {
  return option.name.endsWith("P") ? option.name.slice(0, -1) : option.name;
}

function localizedEquipmentName(itemGroupId: number, koreanName: string, language: Language, japaneseEquipmentGroups: JapaneseEquipmentGroups): string {
  return language === "ja" ? japaneseEquipmentGroups[String(itemGroupId)] ?? koreanName : koreanName;
}

function localizedOpenEquipmentBucket(koreanBucket: string, language: Language, japaneseOpenEquipmentBuckets: JapaneseOpenEquipmentBuckets): string {
  return language === "ja" ? japaneseOpenEquipmentBuckets[koreanBucket] ?? koreanBucket : koreanBucket;
}

function localizedConverterLabel(internalKey: string, language: Language, japaneseOpenMetadata: JapaneseOpenMetadata): string {
  const koreanLabel = koreanConverterLabels[internalKey] ?? internalKey;
  const concept = converterConceptByKey[internalKey];
  return language === "ja" && concept ? japaneseOpenMetadata.converters[concept] ?? koreanLabel : koreanLabel;
}

function localizedGradeLabel(gradeCode: string, koreanName: string, language: Language, japaneseOpenMetadata: JapaneseOpenMetadata): string {
  return language === "ja" ? japaneseOpenMetadata.grades[gradeCode] ?? koreanName : koreanName;
}

function tagSearchText(tags: string[]): string {
  return tags.flatMap((tag) => [tag, tagText("ja", tag)]).join(" ");
}

function localizedOptionTemplate(option: InstandardOption, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string {
  const koreanTemplate = option.short_text || option.description;
  return language === "ja"
    ? japaneseBaseOptions[String(option.option_id)] ?? koreanTemplate
    : koreanTemplate;
}

function displayTemplate(option: InstandardOption, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string {
  const template = localizedOptionTemplate(option, language, japaneseBaseOptions);
  return option.option_id === 922 || option.option_id === 1045
    ? template.replaceAll("[1]", "[0]").replaceAll("[1.1%]", "[0.1%]")
    : template;
}

function displayTitlePlaceholders(template: string): string {
  const placeholderPattern = /\[([+-]?)([012])(?:\.\d+)?([%％]?)\]/g;
  const indices = [...template.matchAll(placeholderPattern)].map((match) => match[2]);
  const uniqueIndices = [...new Set(indices)];
  const names = new Map(uniqueIndices.map((index, position) => [index, uniqueIndices.length === 1 ? "n" : `n${position + 1}`]));
  return template.replace(placeholderPattern, (_, sign: string, index: string, suffix: string) => `[${sign}${names.get(index)}${suffix}]`);
}

function localizedDisplayName(option: InstandardOption, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string {
  return displayTitlePlaceholders(localizedOptionTemplate(option, language, japaneseBaseOptions));
}

function safelyRenderOpenOptionValue(template: string, row: LocalizableOpenOptionRow): string | null {
  const rawValues = [row.value_0_low16, row.value_1_high16];
  const values = rawValues.map(Number);
  const arity = Number(row.option_value_arity);
  if (rawValues.some((value) => !value.trim()) || values.some((value) => !Number.isFinite(value)) || !Number.isInteger(arity) || arity < 0 || arity > 2) {
    return null;
  }

  if (!template.trim()) return null;
  const valuePlaceholders = [...template.matchAll(/\[([+-]?)(\d+)(?:\.\d+)?([%％]?)\]/g)];
  if (valuePlaceholders.some((match) => Number(match[2]) >= 2 || Number(match[2]) >= arity)) {
    return null;
  }

  try {
    const display = renderValue(template, [values[0], values[1], 0]);
    return /\[([+-]?)(\d+)(?:\.\d+)?([%％]?)\]/.test(display) ? null : display;
  } catch {
    return null;
  }
}

function fallbackOpenOptionTitle(row: LocalizableOpenOptionRow): string {
  return row.option_display_name || (row.option_name.endsWith("P") ? row.option_name.slice(0, -1) : row.option_name);
}

function localizedInstandardOpenOptionRow(
  row: InstandardOpenOptionRow,
  optionMap: Map<number, InstandardOption>,
  language: Language,
  japaneseBaseOptions: JapaneseBaseOptions,
): { title: string; display: string } {
  const optionId = Number(row.option_id);
  const option = Number.isInteger(optionId) ? optionMap.get(optionId) : undefined;
  if (language === "ja") {
    const template = japaneseBaseOptions[row.option_id];
    if (template?.trim()) {
      return {
        title: displayTitlePlaceholders(template),
        display: safelyRenderOpenOptionValue(template, row) ?? row.option_display,
      };
    }
  }
  if (!option) return { title: fallbackOpenOptionTitle(row), display: row.option_display };
  const template = localizedOptionTemplate(option, language, japaneseBaseOptions);
  return {
    title: localizedDisplayName(option, language, japaneseBaseOptions),
    display: safelyRenderOpenOptionValue(template, row) ?? row.option_display,
  };
}

function localizedGeneralOpenOptionRow(
  row: OpenOptionRow,
  optionMap: Map<number, InstandardOption>,
  language: Language,
  japaneseBaseOptions: JapaneseBaseOptions,
): { title: string; display: string } {
  const option = optionMap.get(Number(row.option_id));
  if (language === "ko") {
    return {
      title: option ? localizedDisplayName(option, language, japaneseBaseOptions) : fallbackOpenOptionTitle(row),
      display: row.option_display,
    };
  }

  const template = japaneseBaseOptions[row.option_id];
  if (!template?.trim()) return { title: fallbackOpenOptionTitle(row), display: row.option_display };
  return {
    title: displayTitlePlaceholders(template),
    display: safelyRenderOpenOptionValue(template, row) ?? row.option_display,
  };
}

function renderValue(template: string, vector: Roll): string {
  return template.replace(/\[([+-]?)([012])(?:\.(\d+))?([%％])?\]/g, (_, sign, index, digits, suffix) => {
    const value = vector[Number(index)];
    const precision = Number(digits || 0);
    const rendered = precision ? (value / 10 ** precision).toFixed(precision) : String(value);
    const signed = sign && value >= 0 ? `${sign}${rendered}` : rendered;
    return `${signed}${suffix || ""}`;
  });
}

function candidateValues(option: InstandardOption, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string[] {
  const template = displayTemplate(option, language, japaneseBaseOptions);
  return [...new Set(option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.roll_values.map((vector) => renderValue(template, vector))))];
}

function tierCandidateValues(option: InstandardOption, tier: Tier, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string[] {
  const template = displayTemplate(option, language, japaneseBaseOptions);
  return [...new Set(tier.roll_values.map((vector) => renderValue(template, vector)))];
}

function rangeLabel(option: InstandardOption, language: Language, japaneseBaseOptions: JapaneseBaseOptions): string {
  const vectors = option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.roll_values);
  const values = vectors.map((vector) => vector[0]);
  const template = displayTemplate(option, language, japaneseBaseOptions);
  const minimum = renderValue(template, vectors[values.indexOf(Math.min(...values))]);
  const maximum = renderValue(template, vectors[values.indexOf(Math.max(...values))]);
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
  const [resources, setResources] = useState<{ source: SourceDataset; openRows: OpenOptionRow[]; instandardOpenRows: InstandardOpenOptionRow[]; japaneseBaseOptions: JapaneseBaseOptions; japaneseEquipmentGroups: JapaneseEquipmentGroups; japaneseOpenEquipmentBuckets: JapaneseOpenEquipmentBuckets; japaneseOpenMetadata: JapaneseOpenMetadata } | null>(null);
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
      fetch(`${base}data/instandard_equipment.json`).then((response) => {
        if (!response.ok) throw new Error("error.dataset");
        return response.json() as Promise<SourceDataset>;
      }),
      fetch(`${base}data/equipment_converter_type_options.csv`).then((response) => {
        if (!response.ok) throw new Error("error.openCsv");
        return response.text();
      }),
      fetch(`${base}data/instandard_open_option_rows.csv`).then((response) => {
        if (!response.ok) throw new Error("error.instandardOpenCsv");
        return response.text();
      }),
      fetch(`${base}data/i18n/ja/base_options.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOptions");
        return response.json() as Promise<JapaneseBaseOptions>;
      }),
      fetch(`${base}data/i18n/ja/equipment_groups.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseEquipmentGroups");
        return response.json() as Promise<JapaneseEquipmentGroups>;
      }),
      fetch(`${base}data/i18n/ja/open_equipment_buckets.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOpenEquipmentBuckets");
        return response.json() as Promise<JapaneseOpenEquipmentBuckets>;
      }),
      fetch(`${base}data/i18n/ja/open_metadata.json`).then((response) => {
        if (!response.ok) throw new Error("error.japaneseOpenMetadata");
        return response.json() as Promise<JapaneseOpenMetadata>;
      }),
    ]).then(([source, csv, instandardOpenCsv, japaneseBaseOptions, japaneseEquipmentGroups, japaneseOpenEquipmentBuckets, japaneseOpenMetadata]) => {
      if (!cancelled) setResources({ source, openRows: prepareOpenRows(csv, source), instandardOpenRows: prepareInstandardOpenRows(instandardOpenCsv), japaneseBaseOptions, japaneseEquipmentGroups, japaneseOpenEquipmentBuckets, japaneseOpenMetadata });
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
  if (view === "open") return <OpenViewer rows={resources.openRows} source={resources.source} language={language} japaneseBaseOptions={resources.japaneseBaseOptions} japaneseOpenEquipmentBuckets={resources.japaneseOpenEquipmentBuckets} japaneseOpenMetadata={resources.japaneseOpenMetadata} themeButton={headerControls} />;
  if (view === "instandard" && instandardMode === "tier") return <InstandardTierViewer source={resources.source} language={language} japaneseBaseOptions={resources.japaneseBaseOptions} japaneseEquipmentGroups={resources.japaneseEquipmentGroups} themeButton={headerControls} />;
  if (view === "instandard" && (instandardMode === "option" || instandardMode === "open")) return <InstandardOpenViewer mode={instandardMode} source={resources.source} openRows={resources.instandardOpenRows} language={language} japaneseBaseOptions={resources.japaneseBaseOptions} japaneseEquipmentGroups={resources.japaneseEquipmentGroups} japaneseOpenMetadata={resources.japaneseOpenMetadata} themeButton={headerControls} />;
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

function InstandardTierViewer({ source, language, japaneseBaseOptions, japaneseEquipmentGroups, themeButton }: { source: SourceDataset; language: Language; japaneseBaseOptions: JapaneseBaseOptions; japaneseEquipmentGroups: JapaneseEquipmentGroups; themeButton: ReactNode }) {
  const [selectedTier, setSelectedTier] = useState<number | null>(null);
  const [tierTag, setTierTag] = useState("ALL");
  const [tierQuery, setTierQuery] = useState("");
  const [expandedOptionIds, setExpandedOptionIds] = useState<Set<number>>(() => new Set());
  const tierNumbers = useMemo(() => [...new Set(source.options.flatMap((option) => option.tiers.filter((tier) => tier.enabled).map((tier) => tier.tier)))].sort((a, b) => a - b), [source.options]);
  const tierOptions = useMemo(() => selectedTier === null ? [] : source.options.filter((option) => option.tiers.some((tier) => tier.enabled && tier.tier === selectedTier)), [selectedTier, source.options]);
  const tierTags = useMemo(() => ["ALL", ...[...new Set(tierOptions.flatMap((option) => option.tags))].sort((a, b) => a.localeCompare(b, "ko"))], [tierOptions]);
  const optionResults = useMemo(() => {
    if (selectedTier === null) return [];
    const normalized = tierQuery.trim().toLocaleLowerCase();
    return tierOptions
      .filter((option) => tierTag === "ALL" || option.tags.includes(tierTag))
      .map((option) => ({ option, equipment: source.equipment.filter((item) => item.option_ids.includes(option.option_id)) }))
      .filter(({ option, equipment }) => !normalized || [option.name, displayName(option), displayTemplate(option, language, japaneseBaseOptions), localizedDisplayName(option, language, japaneseBaseOptions), tagSearchText(option.tags)].join(" ").toLocaleLowerCase().includes(normalized) || equipment.some((item) => [item.item_group_name, localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)].join(" ").toLocaleLowerCase().includes(normalized)));
  }, [japaneseBaseOptions, japaneseEquipmentGroups, language, selectedTier, source.equipment, tierOptions, tierQuery, tierTag]);

  function changeTier(tierNumber: number) {
    setSelectedTier(tierNumber);
    setTierTag("ALL");
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
            {tierTags.map((value) => <Chip key={value} active={tierTag === value} onClick={() => setTierTag(value)}>{value === "ALL" ? uiText(language, "common.allCategories") : tagText(language, value)}</Chip>)}
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
          const values = tierCandidateValues(option, tierData, language, japaneseBaseOptions);
          return <article className={`tier-option-accordion ${expanded ? "expanded" : ""}`} key={option.option_id}>
            <button className="tier-option-toggle" type="button" aria-expanded={expanded} aria-controls={contentId} onClick={() => toggleOption(option.option_id)}><strong>{localizedDisplayName(option, language, japaneseBaseOptions)}</strong><div className="option-tag-badges">{option.tags.map((optionTag) => <span key={optionTag}>{tagText(language, optionTag)}</span>)}</div><span>{formatAppliedEquipmentCount(language, equipment.length)}</span><span>{formatPossibleValueCount(language, values.length)}</span><Icon className="app-icon tier-chevron" id={expanded ? "ui-chevron-down" : "ui-chevron-right"} size={18} /></button>
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


function InstandardOpenViewer({ mode, source, openRows, language, japaneseBaseOptions, japaneseEquipmentGroups, japaneseOpenMetadata, themeButton }: { mode: "option" | "open"; source: SourceDataset; openRows: InstandardOpenOptionRow[]; language: Language; japaneseBaseOptions: JapaneseBaseOptions; japaneseEquipmentGroups: JapaneseEquipmentGroups; japaneseOpenMetadata: JapaneseOpenMetadata; themeButton: ReactNode }) {
  const [equipmentName, setEquipmentName] = useState("헬멧");
  const [tag, setTag] = useState("ALL");
  const [converter, setConverter] = useState<InstandardOpenOptionRow["converter_type"]>("일반");
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
  const tags = useMemo(() => ["ALL", ...[...new Set(options.flatMap((option) => option.tags))].sort((a, b) => a.localeCompare(b, "ko"))], [options]);
  const filteredEquipment = useMemo(() => {
    const normalized = equipmentQuery.trim().toLocaleLowerCase();
    return source.equipment.filter((item) => !normalized || [item.item_group_name, localizedEquipmentName(item.item_group_id, item.item_group_name, language, japaneseEquipmentGroups)].join(" ").toLocaleLowerCase().includes(normalized));
  }, [equipmentQuery, japaneseEquipmentGroups, language, source.equipment]);
  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return options.filter((option) => (tag === "ALL" || option.tags.includes(tag)) && (!normalized || [option.name, displayName(option), displayTemplate(option, language, japaneseBaseOptions), localizedDisplayName(option, language, japaneseBaseOptions), tagSearchText(option.tags)].join(" ").toLocaleLowerCase().includes(normalized)));
  }, [japaneseBaseOptions, language, options, query, tag]);
  const equipmentOpenRows = useMemo(() => openRows.filter((row) => Number(row.item_group_id) === equipment.item_group_id), [equipment.item_group_id, openRows]);
  const localizedOpenRows = useMemo(() => new Map(equipmentOpenRows.map((row) => [row, localizedInstandardOpenOptionRow(row, optionMap, language, japaneseBaseOptions)])), [equipmentOpenRows, japaneseBaseOptions, language, optionMap]);
  const converters = useMemo(() => ["일반", "개량", "모조", "불타는"].filter((value) => equipmentOpenRows.some((row) => row.converter_type === value)) as InstandardOpenOptionRow["converter_type"][], [equipmentOpenRows]);
  const effectiveOpenLines = selectedOpenLines ?? openLines;
  const filteredOpenRows = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return equipmentOpenRows
      .filter((row) => {
        const localized = localizedOpenRows.get(row);
        return converter === row.converter_type && effectiveOpenLines.includes(row.open_slot) && (!normalized || [row.option_name, row.option_display, localized?.title, localized?.display, row.option_id, row.converter_type, localizedConverterLabel(row.converter_type, "ko", japaneseOpenMetadata), localizedConverterLabel(row.converter_type, "ja", japaneseOpenMetadata)].join(" ").toLocaleLowerCase().includes(normalized));
      })
      .sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [converter, effectiveOpenLines, equipmentOpenRows, japaneseOpenMetadata, localizedOpenRows, query]);
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
    setTag("ALL");
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
        <FilterGroup className="option-tag-filter" number="2" title={uiText(language, "filter.optionCategory")}>
          {tags.map((value) => <Chip key={value} active={tag === value} onClick={() => setTag(value)}>{value === "ALL" ? uiText(language, "common.allCategories") : tagText(language, value)}</Chip>)}
        </FilterGroup>
        <FilterGroup className="option-search-filter" number="3" title={uiText(language, "filter.optionSearch")}>
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
        <Context language={language} breadcrumb={`${equipmentDisplayName} › ${uiText(language, "mode.option.title")} › ${tag === "ALL" ? uiText(language, "common.allCategories") : tagText(language, tag)}`} query={query} onQuery={setQuery} placeholder={uiText(language, "filter.currentOptionSearch")} hideSearch />
        <ResultsHead language={language} title={formatEquipmentOptionTitle(language, equipmentDisplayName)} description={uiText(language, "option.resultsDescription")} count={filteredOptions.length} />
        {filteredOptions.length ? <section className="option-section instandard-option-results-section"><div className="table-wrap"><table className="instandard-option-results"><thead><tr><th>{uiText(language, "option.name")}</th><th>{uiText(language, "option.category")}</th><th>{uiText(language, "option.range")}</th><th>{uiText(language, "option.tierDetails")}</th></tr></thead><tbody>{filteredOptions.map((option) => <tr key={option.option_id}><td><strong>{localizedDisplayName(option, language, japaneseBaseOptions)}</strong>{equipment.supplemental_option_ids.includes(option.option_id) && <em>{uiText(language, "option.supplemental")}</em>}</td><td><div className="option-tag-badges">{option.tags.map((optionTag) => <span key={optionTag}>{tagText(language, optionTag)}</span>)}</div></td><td><span className="option-range-text">{rangeLabel(option, language, japaneseBaseOptions)}</span></td><td><div className="tier-detail-group"><button className="tier-detail-button" onClick={() => setSelectedOption(option)}>{uiText(language, "option.viewTierValues")}</button><small>{formatPossibleValueCount(language, candidateValues(option, language, japaneseBaseOptions).length)}</small></div></td></tr>)}</tbody></table></div></section> : <Empty language={language} />}
      </> : <>
        <Context language={language} breadcrumb={`${equipmentDisplayName} › ${uiText(language, "mode.open.title")} › ${localizedConverterLabel(converter, language, japaneseOpenMetadata)} › ${selectedOpenLineLabel}`} query={query} onQuery={setQuery} placeholder={uiText(language, "filter.currentOpenSearch")} />
        <ResultsHead language={language} title={formatEquipmentOpenTitle(language, equipmentDisplayName)} description={uiText(language, "instandardOpen.resultsDescription")} count={filteredOpenRows.length} />
        {filteredOpenRows.length ? openLines.filter((line) => (openGroups.get(line)?.length ?? 0) > 0).map((line) => {
          const group = openGroups.get(line) ?? [];
          const anomaly = group.find((row) => row.probability_sum_valid === "false");
          const missingProbability = anomaly ? 100 - Number(anomaly.slot_probability_sum) : 0;
          return <section className="option-section instandard-open-section" key={line}>
            <SectionHead title={formatOpenSlot(language, line)} count={formatCandidateCount(language, group.length)} />
            {anomaly && <aside className="probability-warning"><strong>{formatIncompleteWarningTitle(language, line)}</strong><span>{formatIncompleteWarning(language, formatProbability(anomaly.slot_probability_sum), formatProbability(String(missingProbability))).map((message, index) => <span key={message}>{message}{index < 2 && <br />}</span>)}</span></aside>}
            <div className="table-wrap"><table className="instandard-open-table"><thead><tr><th>{uiText(language, "instandardOpen.optionName")}</th><th>{uiText(language, "instandardOpen.value")}</th><th>{uiText(language, "instandardOpen.probability")}</th><th>{uiText(language, "instandardOpen.internalTier")}</th></tr></thead><tbody>
              {group.map((row) => { const localized = localizedOpenRows.get(row); return <tr key={`${row.source_block_index}-${row.source_file_offset}`}><td><strong>{localized?.title ?? row.option_name}</strong></td><td>{localized?.display ?? row.option_display}</td><td><b className="probability">{formatProbability(row.probability)}%</b></td><td><span className="tier">{row.option_tier}</span></td></tr>; })}
            </tbody></table></div>
          </section>;
        }) : <Empty language={language} />}
      </>}
    </main>
    {mode === "option" && selectedOption && <Modal language={language} title={localizedDisplayName(selectedOption, language, japaneseBaseOptions)} subtitle={formatRangeSubtitle(language, rangeLabel(selectedOption, language, japaneseBaseOptions))} onClose={() => setSelectedOption(null)}><p>{formatActiveTierSummary(language, selectedOption.tiers.filter((tier) => tier.enabled).length, candidateValues(selectedOption, language, japaneseBaseOptions).length)}</p><div className="tier-value-groups">{selectedOption.tiers.filter((tier) => tier.enabled).map((tier) => <section className="tier-value-group" key={tier.raw_tier_index}><h3>Tier {tier.tier}</h3><div className="value-list">{tierCandidateValues(selectedOption, tier, language, japaneseBaseOptions).map((value) => <span key={`${tier.raw_tier_index}-${value}`}>{value}</span>)}</div></section>)}</div></Modal>}
  </>;
}

function OpenViewer({ rows, source, language, japaneseBaseOptions, japaneseOpenEquipmentBuckets, japaneseOpenMetadata, themeButton }: { rows: OpenOptionRow[]; source: SourceDataset; language: Language; japaneseBaseOptions: JapaneseBaseOptions; japaneseOpenEquipmentBuckets: JapaneseOpenEquipmentBuckets; japaneseOpenMetadata: JapaneseOpenMetadata; themeButton: ReactNode }) {
  const optionMap = useMemo(() => new Map(source.options.map((option) => [option.option_id, option])), [source.options]);
  const localizedRows = useMemo(() => new Map(rows.map((row) => [row, localizedGeneralOpenOptionRow(row, optionMap, language, japaneseBaseOptions)])), [japaneseBaseOptions, language, optionMap, rows]);
  const equipmentValues = useMemo(() => [...new Set(rows.map((row) => row.equipment_bucket))].sort((a, b) => a.localeCompare(b, "ko")), [rows]);
  const [equipment, setEquipment] = useState(equipmentValues.includes("헬멧") ? "헬멧" : equipmentValues[0]);
  const equipmentDisplayName = localizedOpenEquipmentBucket(equipment, language, japaneseOpenEquipmentBuckets);
  const converters = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment).map((row) => row.converter_type))].sort((a, b) => (converterOrder.get(a) ?? 99) - (converterOrder.get(b) ?? 99)), [equipment, rows]);
  const [converter, setConverter] = useState(converters[0]);
  const grades = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)), [equipment, converter, rows]);
  const [grade, setGrade] = useState(grades[0]);
  const lines = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade).map((row) => row.open_slot))].sort((a, b) => Number(a) - Number(b)), [equipment, converter, grade, rows]);
  const [selectedLines, setSelectedLines] = useState<string[] | null>(null);
  const effectiveLines = selectedLines === null ? lines : selectedLines.filter((line) => lines.includes(line));
  const tags = useMemo(() => ["ALL", ...[...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade && effectiveLines.includes(row.open_slot)).flatMap((row) => row.tags))].sort((a, b) => a.localeCompare(b, "ko"))], [equipment, converter, grade, effectiveLines.join("|"), rows]);
  const [tag, setTag] = useState("ALL");
  const [query, setQuery] = useState("");
  const gradeLabel = (code: string) => {
    const koreanName = rows.find((row) => row.grade_code === code && row.grade_name)?.grade_name || uiText(language, "common.unknownName");
    return `${code} · ${localizedGradeLabel(code, koreanName, language, japaneseOpenMetadata)}`;
  };
  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return rows.filter((row) => {
      const localized = localizedRows.get(row);
      return row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade && effectiveLines.includes(row.open_slot) && (tag === "ALL" || row.tags.includes(tag)) && (!normalized || [row.equipment_bucket, localizedOpenEquipmentBucket(row.equipment_bucket, language, japaneseOpenEquipmentBuckets), row.converter_type, localizedConverterLabel(row.converter_type, "ko", japaneseOpenMetadata), localizedConverterLabel(row.converter_type, "ja", japaneseOpenMetadata), row.grade_code, row.grade_name, localizedGradeLabel(row.grade_code, row.grade_name, "ja", japaneseOpenMetadata), row.option_name, row.option_display_name, row.option_display, localized?.title, localized?.display, row.option_id, tagSearchText(row.tags)].join(" ").toLocaleLowerCase().includes(normalized));
    }).sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || a.tags[0].localeCompare(b.tags[0], "ko") || a.tags.join("/").localeCompare(b.tags.join("/"), "ko") || Number(a.option_id) - Number(b.option_id) || Number(a.option_tier) - Number(b.option_tier) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [equipment, converter, grade, effectiveLines.join("|"), japaneseOpenEquipmentBuckets, japaneseOpenMetadata, language, tag, query, localizedRows, rows]);
  const groups = new Map(lines.map((line) => [line, filtered.filter((row) => row.open_slot === line)]));

  function changeEquipment(value: string) { const nextConverters = [...new Set(rows.filter((row) => row.equipment_bucket === value).map((row) => row.converter_type))].sort((a, b) => (converterOrder.get(a) ?? 99) - (converterOrder.get(b) ?? 99)); const nextConverter = nextConverters.includes(converter) ? converter : nextConverters[0]; const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === value && row.converter_type === nextConverter).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)); setEquipment(value); setConverter(nextConverter); setGrade(nextGrades[0]); setSelectedLines(null); setTag("ALL"); }
  function changeConverter(value: string) { const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === value).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)); setConverter(value); setGrade(nextGrades[0]); setSelectedLines(null); setTag("ALL"); }
  function toggleLine(value: string) { if (value === "ALL") setSelectedLines(effectiveLines.length === lines.length ? [] : null); else setSelectedLines(effectiveLines.includes(value) ? effectiveLines.filter((line) => line !== value) : [...effectiveLines, value].sort((a, b) => Number(a) - Number(b))); setTag("ALL"); }
  const generalConverterLabel = (_displayLanguage: Language, value: string) => localizedConverterLabel(value, language, japaneseOpenMetadata);

  return <><Header language={language} title={uiText(language, "header.open.title")} description={uiText(language, "header.open.description")} themeButton={themeButton} /><main className="open-viewer-mode"><section className="selection-panel open-panel"><FilterGroup number="1" title={uiText(language, "filter.equipment")}>{equipmentValues.map((value) => <Chip key={value} active={equipment === value} onClick={() => changeEquipment(value)}><span className="open-equipment-chip"><Icon className="app-icon" id={openEquipmentIconId(value)} size={18} />{localizedOpenEquipmentBucket(value, language, japaneseOpenEquipmentBuckets)}</span></Chip>)}</FilterGroup><FilterGroup number="2" title={uiText(language, "filter.converterSelection")}>{converters.map((value) => <Chip key={value} active={converter === value} onClick={() => changeConverter(value)}>{generalConverterLabel(language, value)}</Chip>)}</FilterGroup><FilterGroup number="3" title={uiText(language, "filter.itemGrade")}>{grades.map((value) => <Chip key={value} active={grade === value} onClick={() => { setGrade(value); setSelectedLines(null); setTag("ALL"); }}>{gradeLabel(value)}</Chip>)}</FilterGroup><FilterGroup number="4" title={uiText(language, "filter.openSlot")}><Chip active={effectiveLines.length === lines.length} onClick={() => toggleLine("ALL")}>▤ ALL</Chip>{lines.map((value) => <Chip key={value} active={effectiveLines.includes(value)} onClick={() => toggleLine(value)}>{formatOpenSlot(language, value)}</Chip>)}</FilterGroup><FilterGroup number="5" title={uiText(language, "filter.tags")}>{tags.map((value) => <Chip key={value} active={tag === value} onClick={() => setTag(value)}>{value === "ALL" ? uiText(language, "common.allTags") : tagText(language, value)}</Chip>)}</FilterGroup></section><Context language={language} breadcrumb={`${equipmentDisplayName} › ${generalConverterLabel(language, converter)} › ${gradeLabel(grade)} › ${effectiveLines.length === lines.length ? uiText(language, "common.allOpenSlots") : effectiveLines.map((line) => formatOpenSlot(language, line)).join(" · ")} › ${tag === "ALL" ? uiText(language, "common.allTags") : tagText(language, tag)}`} query={query} onQuery={setQuery} placeholder={uiText(language, "filter.currentListSearch")} /><ResultsHead language={language} title={uiText(language, "open.resultsTitle")} description={uiText(language, "open.resultsDescription")} count={filtered.length} />{filtered.length ? lines.filter((line) => (groups.get(line)?.length ?? 0) > 0).map((line) => <section className="option-section open-section" key={line}><SectionHead title={formatOpenSlot(language, line)} count={formatCandidateCount(language, groups.get(line)?.length ?? 0)} /><div className="table-wrap"><table className="open-table"><thead><tr><th>{uiText(language, "open.effect")}</th><th>{uiText(language, "open.nameAndTags")}</th><th>{uiText(language, "open.level")}</th><th>{uiText(language, "open.converterProbability")}</th></tr></thead><tbody>{groups.get(line)?.map((row, index) => { const localized = localizedRows.get(row); return <tr key={`${row.option_id}-${row.option_tier}-${row.candidate_index}-${index}`}><td><strong>{localized?.display ?? row.option_display}</strong></td><td>{localized?.title ?? row.option_display_name}<small>{row.tags.map((tag) => tagText(language, tag)).join(" / ")}</small></td><td><span className="tier">{formatTierLevel(language, row.option_tier)}</span></td><td><b className="probability">{row.converter_probability}%</b></td></tr>; })}</tbody></table></div></section>) : <Empty language={language} />}</main></>;
}

function FilterGroup({ number, title, children, className = "" }: { number: string; title: string; children: ReactNode; className?: string }) { return <section className={`filter-group ${className}`}><h2><span>{number}</span>{title}</h2><div className="chip-grid">{children}</div></section>; }
function Chip({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) { return <button className={`chip ${active ? "active" : ""}`} aria-pressed={active} onClick={onClick}>{children}</button>; }
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
