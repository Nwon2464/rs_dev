import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Roll = [number, number, number];
type View = "home" | "instandard" | "open";
type Theme = "light" | "dark";
type InstandardTarget = "instandard" | "open";

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

const converterOrder = new Map(["일반 변환기", "개량된 변환기", "모조 변환기", "불타는 변환기", "협회 변환기"].map((name, index) => [name, index]));

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
    throw new Error("비규격 개방 옵션 데이터에 필수 필드가 없거나 비어 있습니다.");
  }
  return rows;
}

function displayName(option: InstandardOption): string {
  return option.name.endsWith("P") ? option.name.slice(0, -1) : option.name;
}

function displayTemplate(option: InstandardOption): string {
  const template = option.short_text || option.description;
  return option.option_id === 922 || option.option_id === 1045
    ? template.replaceAll("[1]", "[0]").replaceAll("[1.1%]", "[0.1%]")
    : template;
}

function renderValue(template: string, vector: Roll): string {
  return template.replace(/\[([012])(?:\.(\d+))?([%％])?\]/g, (_, index, digits, suffix) => {
    const value = vector[Number(index)];
    const precision = Number(digits || 0);
    return `${precision ? (value / 10 ** precision).toFixed(precision) : value}${suffix || ""}`;
  });
}

function candidateValues(option: InstandardOption): string[] {
  const template = displayTemplate(option);
  return [...new Set(option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.roll_values.map((vector) => renderValue(template, vector))))];
}

function rangeLabel(option: InstandardOption): string {
  const vectors = option.tiers.filter((tier) => tier.enabled).flatMap((tier) => tier.roll_values);
  const values = vectors.map((vector) => vector[0]);
  const template = displayTemplate(option);
  const minimum = renderValue(template, vectors[values.indexOf(Math.min(...values))]);
  const maximum = renderValue(template, vectors[values.indexOf(Math.max(...values))]);
  return minimum === maximum ? minimum : `${minimum} ~ ${maximum}`;
}

function App() {
  const requested = new URLSearchParams(window.location.search).get("view");
  const view: View = requested === "open" || requested === "instandard" ? requested : "home";
  const [theme, setTheme] = useState<Theme>(() => localStorage.getItem("redstone-ui-theme") === "dark" ? "dark" : "light");
  const [resources, setResources] = useState<{ source: SourceDataset; openRows: OpenOptionRow[]; instandardOpenRows: InstandardOpenOptionRow[] } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("redstone-ui-theme", theme);
  }, [theme]);

  useEffect(() => {
    let cancelled = false;
    const base = import.meta.env.BASE_URL;
    Promise.all([
      fetch(`${base}data/instandard_equipment.json`).then((response) => {
        if (!response.ok) throw new Error("비규격 옵션 JSON을 읽을 수 없습니다.");
        return response.json() as Promise<SourceDataset>;
      }),
      fetch(`${base}data/equipment_converter_type_options.csv`).then((response) => {
        if (!response.ok) throw new Error("개방 옵션 CSV를 읽을 수 없습니다.");
        return response.text();
      }),
      fetch(`${base}data/instandard_open_option_rows.csv`).then((response) => {
        if (!response.ok) throw new Error("비규격 개방 옵션 CSV를 읽을 수 없습니다.");
        return response.text();
      }),
    ]).then(([source, csv, instandardOpenCsv]) => {
      if (!cancelled) setResources({ source, openRows: prepareOpenRows(csv, source), instandardOpenRows: prepareInstandardOpenRows(instandardOpenCsv) });
    }).catch((error: unknown) => {
      if (!cancelled) setLoadError(error instanceof Error ? error.message : "데이터를 읽을 수 없습니다.");
    });
    return () => { cancelled = true; };
  }, []);

  const themeButton = <button className="theme" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme === "dark" ? "☾ 라이트 모드" : "☀ 다크 모드"}</button>;
  if (view === "home") return <Home themeButton={themeButton} />;
  if (loadError) return <><Header title="데이터를 불러올 수 없습니다" description={loadError} themeButton={themeButton} /><main><Empty /></main></>;
  if (!resources) return <><Header title="데이터 불러오는 중" description="옵션 데이터를 준비하고 있습니다." themeButton={themeButton} /><main><div className="empty">불러오는 중…</div></main></>;
  if (view === "open") return <OpenViewer rows={resources.openRows} themeButton={themeButton} />;
  if (view === "instandard") return <InstandardOpenViewer source={resources.source} openRows={resources.instandardOpenRows} themeButton={themeButton} />;
  return null;
}

function Header({ title, description, themeButton, home = true }: { title: string; description: string; themeButton: ReactNode; home?: boolean }) {
  return <header><div className="top"><div><h1>{title}</h1><p>{description}</p></div><div className="header-actions">{home && <a className="home" href="?">← 메인</a>}{themeButton}</div></div></header>;
}

function Home({ themeButton }: { themeButton: ReactNode }) {
  return <><Header title="Red Stone 장비 옵션 탐색기" description="확인할 옵션 시스템을 선택하세요." themeButton={themeButton} home={false} /><main className="home-main"><section className="viewer-cards"><a href="?view=open"><span>01</span><h2>장비 개방 옵션</h2><p>장비·변환기·등급·개방 줄별 후보와 확률을 확인합니다.</p><b>개방 옵션 보기 →</b></a><a href="?view=instandard"><span>02</span><h2>비규격 장비 옵션</h2><p>장비별 옵션 수치 범위와 가능한 값을 확인합니다.</p><b>비규격 옵션 보기 →</b></a></section></main></>;
}


const instandardConverterLabels: Record<InstandardOpenOptionRow["converter_type"], string> = {
  일반: "일반변환기",
  개량: "개량변환기",
  모조: "모조변환기",
  불타는: "불타는변환기",
};

function InstandardOpenViewer({ source, openRows, themeButton }: { source: SourceDataset; openRows: InstandardOpenOptionRow[]; themeButton: ReactNode }) {
  const [equipmentName, setEquipmentName] = useState("헬멧");
  const [target, setTarget] = useState<InstandardTarget>("instandard");
  const [tag, setTag] = useState("ALL");
  const [converter, setConverter] = useState<InstandardOpenOptionRow["converter_type"]>("일반");
  const [selectedOpenLines, setSelectedOpenLines] = useState<string[] | null>(null);
  const [query, setQuery] = useState("");
  const [selectedOption, setSelectedOption] = useState<InstandardOption | null>(null);
  const openLines = ["1", "2", "3", "4"];
  const optionMap = useMemo(() => new Map(source.options.map((option) => [option.option_id, option])), [source]);
  const equipment = source.equipment.find((item) => item.item_group_name === equipmentName) ?? source.equipment[0];
  const options = useMemo(() => equipment.option_ids.map((id) => optionMap.get(id)).filter((option): option is InstandardOption => Boolean(option)), [equipment]);
  const tags = useMemo(() => ["ALL", ...[...new Set(options.flatMap((option) => option.tags))].sort((a, b) => a.localeCompare(b, "ko"))], [options]);
  const filteredOptions = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return options.filter((option) => (tag === "ALL" || option.tags.includes(tag)) && (!normalized || [option.name, displayName(option), displayTemplate(option), option.tags.join(" ")].join(" ").toLocaleLowerCase().includes(normalized)));
  }, [options, query, tag]);
  const equipmentOpenRows = useMemo(() => openRows.filter((row) => Number(row.item_group_id) === equipment.item_group_id), [equipment.item_group_id, openRows]);
  const converters = useMemo(() => ["일반", "개량", "모조", "불타는"].filter((value) => equipmentOpenRows.some((row) => row.converter_type === value)) as InstandardOpenOptionRow["converter_type"][], [equipmentOpenRows]);
  const effectiveOpenLines = selectedOpenLines ?? openLines;
  const filteredOpenRows = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return equipmentOpenRows
      .filter((row) => converter === row.converter_type && effectiveOpenLines.includes(row.open_slot) && (!normalized || [row.option_name, row.option_display, row.option_id].join(" ").toLocaleLowerCase().includes(normalized)))
      .sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [converter, effectiveOpenLines, equipmentOpenRows, query]);
  const anomaly = filteredOpenRows.find((row) => row.probability_sum_valid === "false");
  const openGroups = new Map(openLines.map((line) => [line, filteredOpenRows.filter((row) => row.open_slot === line)]));
  const selectedOpenLineLabel = selectedOpenLines === null ? "ALL" : selectedOpenLines.map((line) => `${line}번째`).join(" · ");

  function changeEquipment(name: string) {
    const nextEquipment = source.equipment.find((item) => item.item_group_name === name);
    const nextConverters = openRows
      .filter((row) => Number(row.item_group_id) === nextEquipment?.item_group_id)
      .map((row) => row.converter_type);
    setEquipmentName(name);
    setTag("ALL");
    if (!nextConverters.includes(converter)) setConverter(nextConverters[0] ?? converter);
    setSelectedOpenLines(null);
    setQuery("");
    setSelectedOption(null);
  }

  function changeTarget(value: InstandardTarget) {
    setTarget(value);
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

  const formatProbability = (value: string) => Number(value).toLocaleString("ko-KR", { maximumFractionDigits: 8 });

  return <>
    <Header title="비규격 장비 옵션" description="장비별 비규격 옵션과 개방 옵션 후보를 전환해 확인합니다." themeButton={themeButton} />
    <main>
      <section className={`selection-panel instandard-panel ${target === "open" ? "inst-open-panel" : ""}`} aria-label="비규격 옵션 탐색 조건">
        <FilterGroup number="1" title="장비 선택">
          {source.equipment.map((item) => <Chip key={item.item_group_id} active={equipment.item_group_id === item.item_group_id} onClick={() => changeEquipment(item.item_group_name)}>◇ {item.item_group_name}</Chip>)}
        </FilterGroup>
        <FilterGroup number="2" title="조회 대상">
          <Chip active={target === "instandard"} onClick={() => changeTarget("instandard")}>비규격 옵션</Chip>
          <Chip active={target === "open"} onClick={() => changeTarget("open")}>개방 옵션</Chip>
        </FilterGroup>
        {target === "instandard" ? <FilterGroup number="3" title="옵션 분류">
          {tags.map((value) => <Chip key={value} active={tag === value} onClick={() => setTag(value)}>{value === "ALL" ? "전체 분류" : value}</Chip>)}
        </FilterGroup> : <>
          <FilterGroup number="3" title="변환기">
            {converters.map((value) => <Chip key={value} active={converter === value} onClick={() => { setConverter(value); setQuery(""); }}>{instandardConverterLabels[value]}</Chip>)}
          </FilterGroup>
          <FilterGroup number="4" title="개방 줄">
            <Chip active={selectedOpenLines === null} onClick={() => toggleOpenLine("ALL")}>ALL</Chip>
            {openLines.map((value) => <Chip key={value} active={selectedOpenLines?.includes(value) ?? false} onClick={() => toggleOpenLine(value)}>{value}</Chip>)}
          </FilterGroup>
        </>}
      </section>
      {target === "instandard" ? <>
        <Context breadcrumb={`${equipment.item_group_name} › 비규격 옵션 › ${tag === "ALL" ? "전체 분류" : tag}`} query={query} onQuery={setQuery} placeholder="현재 장비군의 옵션 검색" />
        <ResultsHead title={`${equipment.item_group_name} 비규격 옵션`} description="수치 범위를 클릭하면 실제 가능한 값을 모두 확인할 수 있습니다." count={filteredOptions.length} />
        {filteredOptions.length ? <section className="option-section"><SectionHead title="등장 가능 옵션" count={`${filteredOptions.length}개 옵션`} /><div className="table-wrap"><table><thead><tr><th>옵션</th><th>수치 범위</th></tr></thead><tbody>{filteredOptions.map((option) => <tr key={option.option_id}><td><strong>◇ {displayName(option)}</strong><small>{option.tags.join(" / ")}</small>{equipment.supplemental_option_ids.includes(option.option_id) && <em>로컬 교차검증 보완</em>}</td><td><button className="range-button" onClick={() => setSelectedOption(option)}><span>{rangeLabel(option)}</span><small>가능 수치 {candidateValues(option).length}개 보기</small></button></td></tr>)}</tbody></table></div></section> : <Empty />}
      </> : <>
        <Context breadcrumb={`${equipment.item_group_name} › 개방 옵션 › ${instandardConverterLabels[converter]} › ${selectedOpenLineLabel}`} query={query} onQuery={setQuery} placeholder="현재 개방 옵션 후보 검색" />
        <ResultsHead title={`${equipment.item_group_name} 개방 옵션 후보`} description="원본 후보 행을 중복 제거 없이 표시합니다." count={filteredOpenRows.length} />
        {anomaly && <aside className="probability-warning"><strong>확률 합계 이상치</strong><span>원본 후보 확률 합계가 {formatProbability(anomaly.slot_probability_sum)}%입니다. 누락 후보를 보정하거나 100%로 정규화하지 않았습니다.</span></aside>}
        {filteredOpenRows.length ? openLines.filter((line) => (openGroups.get(line)?.length ?? 0) > 0).map((line) => <section className="option-section instandard-open-section" key={line}>
          <SectionHead title={`${line}번째 개방 줄`} count={`${openGroups.get(line)?.length ?? 0}개 후보`} />
          <div className="table-wrap"><table className="instandard-open-table"><thead><tr><th>옵션명</th><th>수치</th><th>확률</th><th>내부 티어</th><th>매핑 근거</th></tr></thead><tbody>
            {openGroups.get(line)?.map((row) => <tr key={`${row.source_block_index}-${row.source_file_offset}`}><td><strong>◇ {row.option_name.endsWith("P") ? row.option_name.slice(0, -1) : row.option_name}</strong><small>option_id {row.option_id} · 후보 {row.candidate_index}</small></td><td>{row.option_display}</td><td><b className="probability">{formatProbability(row.probability)}%</b></td><td><span className="tier">{row.option_tier}</span></td><td><span className={`mapping-badge ${row.mapping_status}`}>{row.mapping_status === "screen_confirmed" ? "화면 확인" : "구조상 후보"}</span></td></tr>)}
          </tbody></table></div>
        </section>) : <Empty />}
      </>}
    </main>
    {target === "instandard" && selectedOption && <Modal title={displayName(selectedOption)} subtitle={`수치 범위: ${rangeLabel(selectedOption)}`} onClose={() => setSelectedOption(null)}><p>활성 티어 {selectedOption.tiers.filter((tier) => tier.enabled).length}개 · 가능한 수치 {candidateValues(selectedOption).length}개</p><div className="tier-value-groups">{selectedOption.tiers.filter((tier) => tier.enabled).map((tier) => <section className="tier-value-group" key={tier.raw_tier_index}><h3>Tier {tier.tier}</h3><div className="value-list">{tier.roll_values.map((vector, index) => <span key={`${tier.raw_tier_index}-${index}`}>{renderValue(displayTemplate(selectedOption), vector)}</span>)}</div></section>)}</div></Modal>}
  </>;
}

function OpenViewer({ rows, themeButton }: { rows: OpenOptionRow[]; themeButton: ReactNode }) {
  const equipmentValues = useMemo(() => [...new Set(rows.map((row) => row.equipment_bucket))].sort((a, b) => a.localeCompare(b, "ko")), [rows]);
  const [equipment, setEquipment] = useState(equipmentValues.includes("헬멧") ? "헬멧" : equipmentValues[0]);
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
  const [selectedRow, setSelectedRow] = useState<OpenOptionRow | null>(null);
  const gradeLabel = (code: string) => `${code} · ${rows.find((row) => row.grade_code === code && row.grade_name)?.grade_name || "명칭 미확정"}`;
  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === converter && row.grade_code === grade && effectiveLines.includes(row.open_slot) && (tag === "ALL" || row.tags.includes(tag)) && (!normalized || [row.option_display, row.option_name, row.option_display_name, row.tags.join(" ")].join(" ").toLocaleLowerCase().includes(normalized))).sort((a, b) => Number(a.open_slot) - Number(b.open_slot) || a.tags[0].localeCompare(b.tags[0], "ko") || a.tags.join("/").localeCompare(b.tags.join("/"), "ko") || Number(a.option_id) - Number(b.option_id) || Number(a.option_tier) - Number(b.option_tier) || Number(a.candidate_index) - Number(b.candidate_index));
  }, [equipment, converter, grade, effectiveLines.join("|"), tag, query, rows]);
  const groups = new Map(lines.map((line) => [line, filtered.filter((row) => row.open_slot === line)]));

  function changeEquipment(value: string) { const nextConverters = [...new Set(rows.filter((row) => row.equipment_bucket === value).map((row) => row.converter_type))].sort((a, b) => (converterOrder.get(a) ?? 99) - (converterOrder.get(b) ?? 99)); const nextConverter = nextConverters.includes(converter) ? converter : nextConverters[0]; const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === value && row.converter_type === nextConverter).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)); setEquipment(value); setConverter(nextConverter); setGrade(nextGrades[0]); setSelectedLines(null); setTag("ALL"); }
  function changeConverter(value: string) { const nextGrades = [...new Set(rows.filter((row) => row.equipment_bucket === equipment && row.converter_type === value).map((row) => row.grade_code))].sort((a, b) => Number(a) - Number(b)); setConverter(value); setGrade(nextGrades[0]); setSelectedLines(null); setTag("ALL"); }
  function toggleLine(value: string) { if (value === "ALL") setSelectedLines(effectiveLines.length === lines.length ? [] : null); else setSelectedLines(effectiveLines.includes(value) ? effectiveLines.filter((line) => line !== value) : [...effectiveLines, value].sort((a, b) => Number(a) - Number(b))); setTag("ALL"); }

  return <><Header title="장비 개방 옵션 · 변환기별" description="변환기 종류별 확률 필드를 분리한 원본 DAT 직접 조인 결과입니다." themeButton={themeButton} /><main><section className="selection-panel open-panel"><FilterGroup number="1" title="장비 선택">{equipmentValues.map((value) => <Chip key={value} active={equipment === value} onClick={() => changeEquipment(value)}>◇ {value}</Chip>)}</FilterGroup><FilterGroup number="2" title="변환기 선택">{converters.map((value) => <Chip key={value} active={converter === value} onClick={() => changeConverter(value)}>{value}</Chip>)}</FilterGroup><FilterGroup number="3" title="아이템 등급">{grades.map((value) => <Chip key={value} active={grade === value} onClick={() => { setGrade(value); setSelectedLines(null); setTag("ALL"); }}>{gradeLabel(value)}</Chip>)}</FilterGroup><FilterGroup number="4" title="개방 줄"><Chip active={effectiveLines.length === lines.length} onClick={() => toggleLine("ALL")}>▤ ALL</Chip>{lines.map((value) => <Chip key={value} active={effectiveLines.includes(value)} onClick={() => toggleLine(value)}>{value}번째 개방 줄</Chip>)}</FilterGroup><FilterGroup number="5" title="태그 필터">{tags.map((value) => <Chip key={value} active={tag === value} onClick={() => setTag(value)}>{value === "ALL" ? "전체 태그" : value}</Chip>)}</FilterGroup></section><Context breadcrumb={`${equipment} › ${converter} › ${gradeLabel(grade)} › ${effectiveLines.length === lines.length ? "전체 개방 줄" : effectiveLines.map((line) => `${line}번째`).join(" · ")} › ${tag === "ALL" ? "전체 태그" : tag}`} query={query} onQuery={setQuery} placeholder="현재 목록에서 옵션 검색" /><ResultsHead title="개방 옵션 후보" description="행을 누르면 원본 데이터와 적용 확률을 확인할 수 있습니다." count={filtered.length} />{filtered.length ? lines.filter((line) => (groups.get(line)?.length ?? 0) > 0).map((line) => <section className="option-section open-section" key={line}><SectionHead title={`${line}번째 개방 줄`} count={`${groups.get(line)?.length ?? 0}개 후보`} /><div className="table-wrap"><table className="open-table"><thead><tr><th>옵션 효과</th><th>옵션명 / 태그</th><th>단계</th><th>변환 확률</th><th>후보</th></tr></thead><tbody>{groups.get(line)?.map((row, index) => <tr key={`${row.option_id}-${row.option_tier}-${row.candidate_index}-${index}`} onClick={() => setSelectedRow(row)} tabIndex={0}><td><strong>◇ {row.option_display}</strong></td><td>{row.option_display_name}<small>{row.tags.join(" / ")}</small></td><td><span className="tier">{row.option_tier}단계</span></td><td><b className="probability">{row.converter_probability}%</b></td><td>{row.candidate_index}</td></tr>)}</tbody></table></div></section>) : <Empty />}</main>{selectedRow && <Modal title={selectedRow.option_display_name} subtitle={selectedRow.option_display} onClose={() => setSelectedRow(null)}><dl className="details"><Detail label="장비" value={selectedRow.equipment_bucket} /><Detail label="변환기" value={selectedRow.converter_type} /><Detail label="등급" value={gradeLabel(selectedRow.grade_code)} /><Detail label="개방 줄" value={`${selectedRow.open_slot}번째`} /><Detail label="태그" value={selectedRow.tags.join(" / ")} /><Detail label="변환 확률" value={`${selectedRow.converter_probability}% (${selectedRow.converter_probability_source})`} /><Detail label="옵션 ID" value={selectedRow.option_id} /><Detail label="원본 값" value={selectedRow.value_raw} /></dl></Modal>}</>;
}

function FilterGroup({ number, title, children }: { number: string; title: string; children: ReactNode }) { return <section className="filter-group"><h2><span>{number}</span>{title}</h2><div className="chip-grid">{children}</div></section>; }
function Chip({ active, children, onClick }: { active: boolean; children: ReactNode; onClick: () => void }) { return <button className={`chip ${active ? "active" : ""}`} aria-pressed={active} onClick={onClick}>{children}</button>; }
function Context({ breadcrumb, query, onQuery, placeholder }: { breadcrumb: string; query: string; onQuery: (value: string) => void; placeholder: string }) { return <section className="context-row"><div className="breadcrumb">현재 위치 <b>{breadcrumb}</b></div><label className="search"><span className="visually-hidden">옵션 검색</span><input value={query} onChange={(event) => onQuery(event.target.value)} placeholder={placeholder} /></label></section>; }
function ResultsHead({ title, description, count }: { title: string; description: string; count: number }) { return <section className="results-head"><div><h2>{title}</h2><p>{description}</p></div><b>{count.toLocaleString()}개</b></section>; }
function SectionHead({ title, count }: { title: string; count: string }) { return <div className="option-section-head"><h3>{title}</h3><span>{count}</span></div>; }
function Empty() { return <div className="empty">조건에 맞는 옵션이 없습니다.</div>; }
function Detail({ label, value }: { label: string; value: string }) { return <div><dt>{label}</dt><dd>{value}</dd></div>; }

function Modal({ title, subtitle, children, onClose }: { title: string; subtitle: string; children: ReactNode; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { dialog.current?.showModal(); }, []);
  return <dialog ref={dialog} className="candidate-dialog" onCancel={onClose} onClick={(event) => { if (event.currentTarget === event.target) onClose(); }}><div className="dialog-inner"><div className="dialog-head"><div><h2>{title}</h2><p>{subtitle}</p></div><button aria-label="닫기" onClick={onClose}>×</button></div>{children}</div></dialog>;
}

createRoot(document.getElementById("root")!).render(<App />);
