import { parseCsv } from "./generalOpenOptions";

export type Roll = [number, number, number];
export type InstandardTier = {
  tier: number;
  option_level_raw: number;
  enabled: boolean;
  rolls: Roll[];
};
export type InstandardOption = {
  option_id: number;
  source_tags: string[];
  canonical_tags: string[];
  tiers: InstandardTier[];
};
export type InstandardEquipment = {
  item_group_id: number;
  item_group_name: string;
  bucket_signature_index: number;
  option_ids: number[];
  supplemental_option_ids: number[];
};
export type InstandardCatalog = {
  schema_version: 1;
  value_bindings: Record<string, Record<string, number>>;
  equipment: InstandardEquipment[];
  options: InstandardOption[];
};
export type InstandardOpenOptionRow = {
  converter_type: "normal" | "improved" | "fake" | "burning";
  item_group_id: string;
  bucket_signature_index: string;
  bucket_group_ids: string;
  section_type: string;
  section_group: string;
  open_slot: string;
  candidate_index: string;
  option_id: string;
  value_0: string;
  value_1: string;
  probability: string;
  probability_source: "float_a" | "float_b";
  tier: string;
  mapping_status: "screen_confirmed" | "structural_candidate";
  source_block_index: string;
  source_file_offset: string;
};

export function prepareInstandardOpenRows(csv: string): InstandardOpenOptionRow[] {
  const rows = parseCsv(csv) as unknown as InstandardOpenOptionRow[];
  const required = ["converter_type", "item_group_id", "open_slot", "option_id", "value_0", "value_1", "probability", "tier"] as const;
  if (!rows.length || rows.some((row) => required.some((field) => !row[field]?.trim()))) {
    throw new Error("error.instandardOpenCsv");
  }
  return rows;
}
