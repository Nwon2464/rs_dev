import type { Language } from "../../i18n";
import type { OptionTagData } from "./types";

export function tagText(language: Language, tag: string, optionTags: OptionTagData): string {
  return optionTags.tags[tag]?.labels[language] ?? tag;
}

export function tagSearchText(tags: string[], optionTags: OptionTagData): string {
  return tags.flatMap((tag) => [tag, tagText("ja", tag, optionTags)]).join(" ");
}

export function matchesSelectedTags(optionTagValues: string[], selectedTags: string[], optionTags: OptionTagData): boolean {
  const selectedByGroup = new Map<string, string[]>();
  selectedTags.forEach((tag) => {
    const group = optionTags.tags[tag]?.group;
    if (group) selectedByGroup.set(group, [...(selectedByGroup.get(group) ?? []), tag]);
  });
  return [...selectedByGroup.values()].every((groupTags) => groupTags.some((tag) => optionTagValues.includes(tag)));
}

export function toggleSelectedTag(selectedTags: string[], tag: string): string[] {
  return selectedTags.includes(tag) ? selectedTags.filter((value) => value !== tag) : [...selectedTags, tag];
}
