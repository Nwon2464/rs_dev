import type { Language } from "../../i18n";
import type { OptionLocales } from "./types";
import { normalizeTemplate } from "./normalizeTemplate";
import { renderTemplate } from "./renderTemplate";
import { titleTemplate } from "./placeholders";

export function localizedOption(
  optionId: string,
  values: [number, number],
  language: Language,
  locales: OptionLocales,
): { title: string; display: string } {
  const template = normalizeTemplate(locales[language][optionId] || "");
  if (!template) throw new Error(`missing ${language} template for option_id=${optionId}`);
  return {
    title: titleTemplate(template),
    display: renderTemplate(template, values),
  };
}
