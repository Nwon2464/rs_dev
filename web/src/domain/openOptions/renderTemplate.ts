import { hasPlaceholder, placeholders, PLACEHOLDER } from "./placeholders";

export function renderTemplate(template: string, values: number[], bindings: Record<string, number> = {}): string {
  const required = placeholders(template);
  if (required.some((placeholder) => {
    const sourceIndex = bindings[String(placeholder.index)] ?? placeholder.index;
    return sourceIndex >= values.length || !Number.isFinite(values[sourceIndex]);
  })) {
    throw new Error("template requires an unavailable value");
  }
  const rendered = template.replace(PLACEHOLDER, (_, sign: string, index: string, precision: string, suffix: string) => {
    const targetIndex = Number(index);
    const value = values[bindings[String(targetIndex)] ?? targetIndex];
    const digits = Number(precision || 0);
    const number = digits ? (value / 10 ** digits).toFixed(digits) : String(value);
    const signed = sign && value >= 0 ? `${sign}${number}` : number;
    return `${signed}${suffix || ""}`;
  });
  if (hasPlaceholder(rendered)) throw new Error("placeholder remains after rendering");
  return rendered;
}
