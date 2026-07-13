import type { GeneralOpenOptionRow, OptionTagData } from "../domain/openOptions/types";

export function parseCsv(value: string): Record<string, string>[] {
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

const REQUIRED_FIELDS = [
  "converter_type", "equipment_bucket", "group_ids", "group_names", "grade_code",
  "section_group", "open_slot", "candidate_index", "option_id", "value_0", "value_1",
  "probability", "probability_source", "tier", "source_block_index", "source_file_offset",
] as const;

export function prepareGeneralOpenRows(csv: string, optionTags: OptionTagData): GeneralOpenOptionRow[] {
  const rows = parseCsv(csv).map((raw) => ({
    ...raw,
    tags: optionTags.options[raw.option_id]?.canonical_tags ?? [],
  })) as GeneralOpenOptionRow[];
  if (!rows.length || rows.some((row) => REQUIRED_FIELDS.some((field) => !row[field]?.trim()))) {
    throw new Error("error.openCsv");
  }
  return rows;
}
