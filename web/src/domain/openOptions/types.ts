import type { Language } from "../../i18n";

export type ConverterType = "normal" | "improved" | "fake" | "burning" | "association";

export type GeneralOpenOptionRow = {
  converter_type: ConverterType;
  equipment_bucket: string;
  group_ids: string;
  group_names: string;
  grade_code: string;
  section_group: string;
  open_slot: string;
  candidate_index: string;
  option_id: string;
  value_0: string;
  value_1: string;
  probability: string;
  probability_source: "float_a" | "float_b";
  tier: string;
  source_block_index: string;
  source_file_offset: string;
  tags: string[];
};

export type OptionLocaleCatalog = Record<string, string>;
export type OptionLocales = Record<Language, OptionLocaleCatalog>;
export type OpenEquipmentBuckets = Record<string, string>;
export type EquipmentGroups = Record<string, string>;
export type LocalizedLabel = Record<Language, string>;
export type OpenMetadata = {
  grades: Record<string, LocalizedLabel>;
  converters: Record<ConverterType, LocalizedLabel>;
};

export type OptionTagData = {
  schema_version: number;
  groups: Record<string, { ko: string; ja: string }>;
  tags: Record<string, { group: string; labels: Record<Language, string> }>;
  options: Record<string, { source_tags: string[]; canonical_tags: string[] }>;
};
