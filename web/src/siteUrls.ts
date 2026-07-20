import type { Language } from "./i18n";
import type { InstandardMode } from "./components/instandard/modes";

const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export function homeUrl(language: Language): string {
  return language === "ko" ? `${BASE}/ko/` : `${BASE}/`;
}

export function openOptionsUrl(language: Language): string {
  return language === "ko"
    ? `${BASE}/ko/open-options/`
    : `${BASE}/open-options/`;
}

export function instandardUrl(
  language: Language,
  mode: InstandardMode,
): string {
  const path =
    mode === "option"
      ? "instandard/options"
      : mode === "open"
        ? "instandard/open-options"
        : "instandard/tier-values";
  const languagePrefix = language === "ko" ? "/ko" : "";
  return `${BASE}${languagePrefix}/${path}/`;
}

export function pageUrl(
  language: Language,
  view: "home" | "instandard" | "open",
  mode: InstandardMode | null,
): string {
  if (view === "open") return openOptionsUrl(language);
  if (view === "instandard" && mode) return instandardUrl(language, mode);
  return homeUrl(language);
}
