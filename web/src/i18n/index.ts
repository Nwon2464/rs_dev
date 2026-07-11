export type Language = "ko" | "ja";

export const LANGUAGE_STORAGE_KEY = "redstone-ui-language";

type LanguageStorage = Pick<Storage, "getItem" | "setItem">;

export function loadLanguage(storage: LanguageStorage): Language {
  const stored = storage.getItem(LANGUAGE_STORAGE_KEY);
  return stored === "ko" || stored === "ja" ? stored : "ko";
}

export function saveLanguage(
  storage: LanguageStorage,
  language: Language,
): void {
  storage.setItem(LANGUAGE_STORAGE_KEY, language);
}
