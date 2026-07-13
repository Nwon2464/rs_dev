import { useMemo, useState, type ReactNode } from "react";
import { Icon } from "./Icon";
import { equipmentIconId } from "./iconMap";
import { TagFilterPanel, SelectedTagChips } from "./TagFilterPanel";
import {
  formatCandidateCount,
  formatOpenSlot,
  formatResultCount,
  formatTierLevel,
  uiText,
  type Language,
} from "../i18n";
import { localizedOption } from "../domain/openOptions/localeCatalog";
import { matchesSelectedTags, tagSearchText, tagText } from "../domain/openOptions/tags";
import type {
  GeneralOpenOptionRow,
  OpenEquipmentBuckets,
  OpenMetadata,
  OptionLocales,
  OptionTagData,
} from "../domain/openOptions/types";

type Props = {
  rows: GeneralOpenOptionRow[];
  language: Language;
  optionLocales: OptionLocales;
  openEquipmentBuckets: OpenEquipmentBuckets;
  openMetadata: OpenMetadata;
  optionTags: OptionTagData;
  themeButton: ReactNode;
};

const CONVERTER_ORDER = new Map(["normal", "improved", "fake", "burning", "association"].map((name, index) => [name, index]));
const EQUIPMENT_ICON_ALIASES: Record<string, string> = { "귀걸이/망토": "귀걸이", "장갑/팔찌": "장갑", "전용 갑옷": "공용 갑옷", "무기": "한 손 검" };

function openEquipmentIconId(name: string): string {
  return equipmentIconId[name] ?? equipmentIconId[EQUIPMENT_ICON_ALIASES[name]] ?? "feature-open-option";
}

export function OpenViewer({ rows, language, optionLocales, openEquipmentBuckets, openMetadata, optionTags, themeButton }: Props) {
  const equipmentValues = useMemo(() => [...new Set(rows.map((row) => row.equipment_bucket))].sort((a, b) => a.localeCompare(b, "ko")), [rows]);
  const [equipment, setEquipment] = useState(equipmentValues[0]);
  const converters = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment).map((row) => row.converter_type))].sort((a, b) => (CONVERTER_ORDER.get(a) ?? 99) - (CONVERTER_ORDER.get(b) ?? 99)), [equipment, rows]);
  const [converter, setConverter] = useState(converters[0]);
  const grades = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)), [equipment, converter, rows]);
  const [grade, setGrade] = useState(grades[0]);
  const lines = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade).map((row) => row.open_slot))].sort((a, b) => Number(a) - Number(b)), [equipment, converter, grade, rows]);
  const [selectedLines, setSelectedLines] = useState<string[] | null>(null);
  const effectiveLines = selectedLines === null ? lines : selectedLines.filter((line) => lines.includes(line));
  const tags = useMemo(() => [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade && effectiveLines.includes(row.open_slot)).flatMap((row) => row.tags))].sort((a, b) => a.localeCompare(b, "ko")), [equipment, converter, grade, effectiveLines.join("|"), rows]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [query, setQuery] = useState("");

  const localizedRows = useMemo(() => new Map(rows.map((row) => [row, localizedOption(row.option_id, [Number(row.value_0), Number(row.value_1)], language, optionLocales)])), [language, optionLocales, rows]);
  const searchRows = useMemo(() => new Map(rows.map((row) => {
    const values: [number, number] = [Number(row.value_0), Number(row.value_1)];
    const ko = localizedOption(row.option_id, values, "ko", optionLocales);
    const ja = localizedOption(row.option_id, values, "ja", optionLocales);
    return [row, `${ko.title} ${ko.display} ${ja.title} ${ja.display}`];
  })), [optionLocales, rows]);

  const equipmentLabel = (value: string, displayLanguage: Language = language) => displayLanguage === "ja" ? openEquipmentBuckets[value] ?? value : value;
  const converterLabel = (value: GeneralOpenOptionRow["converter_type"], displayLanguage: Language = language) => openMetadata.converters[value]?.[displayLanguage] ?? value;
  const gradeLabel = (value: string, displayLanguage: Language = language) => `${value} · ${openMetadata.grades[value]?.[displayLanguage] ?? value}`;

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return rows.filter((row) => row.equipment_bucket === equipment
      && row.converter_type === converter
      && row.grade_code === grade
      && effectiveLines.includes(row.open_slot)
      && matchesSelectedTags(row.tags, selectedTags, optionTags)
      && (!normalized || [
        row.equipment_bucket, equipmentLabel(row.equipment_bucket, "ja"), row.converter_type,
        converterLabel(row.converter_type, "ko"), converterLabel(row.converter_type, "ja"),
        row.grade_code, gradeLabel(row.grade_code, "ko"), gradeLabel(row.grade_code, "ja"),
        row.option_id, searchRows.get(row), tagSearchText(row.tags, optionTags),
      ].join(" ").toLocaleLowerCase().includes(normalized)))
      .sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || (a.tags[0] ?? "").localeCompare(b.tags[0] ?? "", "ko") || Number(a.option_id) - Number(b.option_id) || Number(a.tier) - Number(b.tier) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [converter, effectiveLines.join("|"), equipment, grade, openEquipmentBuckets, openMetadata, optionTags, query, rows, searchRows, selectedTags]);
  const groups = new Map(lines.map((line) => [line, filtered.filter((row) => row.open_slot === line)]));

  function changeEquipment(value: string) {
    const nextConverters = [...new Set(rows.filter((row) => row.equipment_bucket === value).map((row) => row.converter_type))].sort((a, b) => (CONVERTER_ORDER.get(a) ?? 99) - (CONVERTER_ORDER.get(b) ?? 99));
    const nextConverter = nextConverters.includes(converter) ? converter : nextConverters[0];
    const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === value && row.converter_type === nextConverter).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b));
    setEquipment(value); setConverter(nextConverter); setGrade(nextGrades[0]); setSelectedLines(null); setSelectedTags([]);
  }
  function changeConverter(value: GeneralOpenOptionRow["converter_type"]) {
    const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === value).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b));
    setConverter(value); setGrade(nextGrades[0]); setSelectedLines(null); setSelectedTags([]);
  }
  function toggleLine(value: string) {
    if (value === "ALL") setSelectedLines(effectiveLines.length === lines.length ? [] : null);
    else setSelectedLines(effectiveLines.includes(value) ? effectiveLines.filter((line) => line !== value) : [...effectiveLines, value].sort((a, b) => Number(a) - Number(b)));
    setSelectedTags([]);
  }

  return <>
    <Header language={language} title={uiText(language, "header.open.title")} description={uiText(language, "header.open.description")} themeButton={themeButton} />
    <main className="open-viewer-mode">
      <section className="selection-panel open-panel">
        <FilterGroup number="1" title={uiText(language, "filter.equipment")}>{equipmentValues.map((value) => <Chip key={value} active={equipment === value} onClick={() => changeEquipment(value)}><span className="open-equipment-chip"><Icon className="app-icon" id={openEquipmentIconId(value)} size={18} />{equipmentLabel(value)}</span></Chip>)}</FilterGroup>
        <FilterGroup number="2" title={uiText(language, "filter.converterSelection")}>{converters.map((value) => <Chip key={value} active={converter === value} onClick={() => changeConverter(value)}>{converterLabel(value)}</Chip>)}</FilterGroup>
        <FilterGroup number="3" title={uiText(language, "filter.itemGrade")}>{grades.map((value) => <Chip key={value} active={grade === value} onClick={() => { setGrade(value); setSelectedLines(null); setSelectedTags([]); }}>{gradeLabel(value)}</Chip>)}</FilterGroup>
        <FilterGroup number="4" title={uiText(language, "filter.openSlot")}><Chip active={effectiveLines.length === lines.length} onClick={() => toggleLine("ALL")}>▤ ALL</Chip>{lines.map((value) => <Chip key={value} active={effectiveLines.includes(value)} onClick={() => toggleLine(value)}>{formatOpenSlot(language, value)}</Chip>)}</FilterGroup>
      </section>
      <TagFilterPanel availableTags={tags} selectedTags={selectedTags} onChange={setSelectedTags} language={language} optionTags={optionTags} />
      <Context language={language} breadcrumb={`${equipmentLabel(equipment)} › ${converterLabel(converter)} › ${gradeLabel(grade)} › ${effectiveLines.length === lines.length ? uiText(language, "common.allOpenSlots") : effectiveLines.map((line) => formatOpenSlot(language, line)).join(" · ")}`} query={query} onQuery={setQuery} />
      <ResultsHead language={language} count={filtered.length} />
      <SelectedTagChips selectedTags={selectedTags} onChange={setSelectedTags} language={language} optionTags={optionTags} />
      {filtered.length ? lines.filter((line) => (groups.get(line)?.length ?? 0) > 0).map((line) => <section className="option-section open-section" key={line}>
        <div className="option-section-head"><h3>{formatOpenSlot(language, line)}</h3><span>{formatCandidateCount(language, groups.get(line)?.length ?? 0)}</span></div>
        <div className="table-wrap"><table className="open-table"><thead><tr><th>{uiText(language, "open.effect")}</th><th>{uiText(language, "open.nameAndTags")}</th><th>{uiText(language, "open.level")}</th><th>{uiText(language, "open.converterProbability")}</th></tr></thead><tbody>{groups.get(line)?.map((row, index) => {
          const localized = localizedRows.get(row)!;
          return <tr key={`${row.source_block_index}-${row.candidate_index}-${index}`}><td><strong>{localized.display}</strong></td><td>{localized.title}<small>{row.tags.map((tag) => tagText(language, tag, optionTags)).join(" / ")}</small></td><td><span className="tier">{formatTierLevel(language, row.tier)}</span></td><td><b className="probability">{row.probability}%</b></td></tr>;
        })}</tbody></table></div>
      </section>) : <div className="empty">{uiText(language, "common.noResults")}</div>}
    </main>
  </>;
}

function Header({ language, title, description, themeButton }: { language: Language; title: string; description: string; themeButton: ReactNode }) {
  return <header><div className="top"><div><h1>{title}</h1><p>{description}</p></div><div className="header-actions"><a className="home" href="?">← {uiText(language, "common.home")}</a>{themeButton}</div></div></header>;
}
function FilterGroup({ number, title, children }: { number: string; title: string; children: ReactNode }) { return <section className="filter-group"><h2><span>{number}</span>{title}</h2><div className="chip-grid">{children}</div></section>; }
function Chip({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) { return <button className={`chip ${active ? "active" : ""}`} aria-pressed={active} onClick={onClick}>{children}</button>; }
function Context({ language, breadcrumb, query, onQuery }: { language: Language; breadcrumb: string; query: string; onQuery: (value: string) => void }) { return <section className="context-row"><div className="breadcrumb">{uiText(language, "common.currentLocation")} <b>{breadcrumb}</b></div><label className="search"><span className="visually-hidden">{uiText(language, "filter.optionSearch")}</span><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={uiText(language, "filter.currentListSearch")} /></label></section>; }
function ResultsHead({ language, count }: { language: Language; count: number }) { return <section className="results-head"><div><h2>{uiText(language, "open.resultsTitle")}</h2><p>{uiText(language, "open.resultsDescription")}</p></div><b>{formatResultCount(language, count)}</b></section>; }
