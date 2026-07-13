const PLACEHOLDER = /\[([+-]?)(\d+)(?:\.(\d+))?([%％])?\]/g;

export type Placeholder = {
  sign: string;
  index: number;
  precision: number;
  suffix: string;
};

export function placeholders(template: string): Placeholder[] {
  return [...template.matchAll(PLACEHOLDER)].map((match) => ({
    sign: match[1],
    index: Number(match[2]),
    precision: Number(match[3] || 0),
    suffix: match[4] || "",
  }));
}

export function titleTemplate(template: string, bindings: Record<string, number> = {}): string {
  const sourceIndex = (index: number) => bindings[String(index)] ?? index;
  const uniqueIndices = [...new Set(placeholders(template).map((placeholder) => sourceIndex(placeholder.index)))];
  const names = new Map(uniqueIndices.map((index, position) => [index, uniqueIndices.length === 1 ? "n" : `n${position + 1}`]));
  return template.replace(PLACEHOLDER, (_, sign: string, index: string, _precision: string, suffix: string) => `[${sign}${names.get(sourceIndex(Number(index)))}${suffix || ""}]`);
}

export function hasPlaceholder(template: string): boolean {
  PLACEHOLDER.lastIndex = 0;
  return PLACEHOLDER.test(template);
}

export { PLACEHOLDER };
