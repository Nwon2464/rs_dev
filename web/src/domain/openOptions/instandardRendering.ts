import type {
  InstandardCatalog,
  InstandardOpenOptionRow,
  InstandardOption,
  InstandardTier,
} from "../../data/instandardOptions";
import type { Language } from "../../i18n";
import { titleTemplate } from "./placeholders";
import { renderTemplate } from "./renderTemplate";
import type { EquipmentGroups, OpenMetadata, OptionLocales } from "./types";

type ConverterConcept =
  | "normal"
  | "improved"
  | "fake"
  | "burning"
  | "association";

const converterConceptByKey: Record<string, ConverterConcept> = {
  "일반 변환기": "normal",
  "개량된 변환기": "improved",
  "모조 변환기": "fake",
  "불타는 변환기": "burning",
  "협회 변환기": "association",
  일반: "normal",
  개량: "improved",
  모조: "fake",
  불타는: "burning",
  normal: "normal",
  improved: "improved",
  fake: "fake",
  burning: "burning",
  association: "association",
};

export function localizedEquipmentName(
  itemGroupId: number,
  koreanName: string,
  language: Language,
  equipmentGroups: EquipmentGroups,
): string {
  return language === "ja"
    ? equipmentGroups[String(itemGroupId)] ?? koreanName
    : koreanName;
}

export function localizedConverterLabel(
  internalKey: string,
  language: Language,
  metadata: OpenMetadata,
): string {
  const concept = converterConceptByKey[internalKey];
  return concept
    ? metadata.converters[concept]?.[language] ?? internalKey
    : internalKey;
}

export function optionTemplate(
  option: InstandardOption,
  language: Language,
  optionLocales: OptionLocales,
): string {
  const template = optionLocales[language][String(option.option_id)];
  if (!template) {
    throw new Error(
      `missing ${language} template for option_id=${option.option_id}`,
    );
  }
  return template;
}

export function optionBindings(
  catalog: InstandardCatalog,
  optionId: number,
): Record<string, number> {
  return catalog.value_bindings[String(optionId)] ?? {};
}

export function localizedInstandardOptionTitle(
  option: InstandardOption,
  language: Language,
  optionLocales: OptionLocales,
  catalog: InstandardCatalog,
): string {
  return titleTemplate(
    optionTemplate(option, language, optionLocales),
    optionBindings(catalog, option.option_id),
  );
}

export function localizedInstandardOpenOptionRow(
  row: InstandardOpenOptionRow,
  language: Language,
  optionLocales: OptionLocales,
  catalog: InstandardCatalog,
): { title: string; display: string } {
  const template = optionLocales[language][row.option_id];
  if (!template) {
    throw new Error(
      `missing ${language} template for option_id=${row.option_id}`,
    );
  }
  const bindings = optionBindings(catalog, Number(row.option_id));
  return {
    title: titleTemplate(template, bindings),
    display: renderTemplate(
      template,
      [Number(row.value_0), Number(row.value_1)],
      bindings,
    ),
  };
}

export function candidateValues(
  option: InstandardOption,
  language: Language,
  optionLocales: OptionLocales,
  catalog: InstandardCatalog,
): string[] {
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(catalog, option.option_id);
  return [
    ...new Set(
      option.tiers
        .filter((tier) => tier.enabled)
        .flatMap((tier) =>
          tier.rolls.map((vector) =>
            renderTemplate(template, vector, bindings),
          ),
        ),
    ),
  ];
}

export function tierCandidateValues(
  option: InstandardOption,
  tier: InstandardTier,
  language: Language,
  optionLocales: OptionLocales,
  catalog: InstandardCatalog,
): string[] {
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(catalog, option.option_id);
  return [
    ...new Set(
      tier.rolls.map((vector) =>
        renderTemplate(template, vector, bindings),
      ),
    ),
  ];
}

export function rangeLabel(
  option: InstandardOption,
  language: Language,
  optionLocales: OptionLocales,
  catalog: InstandardCatalog,
): string {
  const vectors = option.tiers
    .filter((tier) => tier.enabled)
    .flatMap((tier) => tier.rolls);
  const values = vectors.map((vector) => vector[0]);
  const template = optionTemplate(option, language, optionLocales);
  const bindings = optionBindings(catalog, option.option_id);
  const minimum = renderTemplate(
    template,
    vectors[values.indexOf(Math.min(...values))],
    bindings,
  );
  const maximum = renderTemplate(
    template,
    vectors[values.indexOf(Math.max(...values))],
    bindings,
  );
  return minimum === maximum ? minimum : `${minimum} ~ ${maximum}`;
}

export function formatProbability(value: string): string {
  return Number(value).toLocaleString("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}
