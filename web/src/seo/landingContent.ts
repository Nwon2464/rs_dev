import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { parseCsv } from "../data/generalOpenOptions";
import { normalizeTemplate } from "../domain/openOptions/normalizeTemplate";
import { titleTemplate } from "../domain/openOptions/placeholders";
import type { OptionLocales, OptionTagData } from "../domain/openOptions/types";
import type { InstandardCatalog } from "../data/instandardOptions";
import type { SeoRoute } from "./routes";

export type LandingContent = {
  updatedDate: string;
  formattedDate: string;
  representativeOptions: string[];
};

const CHANGELOG_PATH = resolve(process.cwd(), "..", "CHANGELOG.md");
const DATA_ROOT = resolve(process.cwd(), "public", "data", "open_options");

async function readJson<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(resolve(DATA_ROOT, path), "utf8")) as T;
}

async function latestChangelogDate(): Promise<string> {
  const changelog = await readFile(CHANGELOG_PATH, "utf8");
  const headings = [...changelog.matchAll(
    /^## (?:Unreleased — )?(\d{4}-\d{2}-\d{2})\s*$/gm,
  )];
  const dates = headings
    .filter((heading, index) => {
      const bodyStart = (heading.index ?? 0) + heading[0].length;
      const bodyEnd = headings[index + 1]?.index ?? changelog.length;
      return /^### 게임 데이터 변경\s*$/m.test(
        changelog.slice(bodyStart, bodyEnd),
      );
    })
    .map((heading) => heading[1])
    .sort((left, right) => right.localeCompare(left));
  if (!dates.length) {
    throw new Error(
      "CHANGELOG.md에서 '게임 데이터 변경' 항목의 YYYY-MM-DD 갱신일을 찾을 수 없습니다.",
    );
  }
  return dates[0];
}

function formatDate(date: string, language: SeoRoute["language"]): string {
  const [year, month, day] = date.split("-").map(Number);
  return language === "ja"
    ? `${year}年${month}月${day}日`
    : `${year}년 ${month}월 ${day}일`;
}

async function routeOptionIds(route: SeoRoute): Promise<string[]> {
  if (route.key === "home") return [];
  if (route.key === "open" || route.key === "instandard-open") {
    const path = route.key === "open"
      ? "general/open_option_rows.csv"
      : "instandard/open_option_rows.csv";
    const rows = parseCsv(await readFile(resolve(DATA_ROOT, path), "utf8"));
    return [...new Set(rows.map((row) => row.option_id).filter(Boolean))];
  }
  const catalog = await readJson<InstandardCatalog>("instandard/catalog.json");
  return catalog.options.map((option) => String(option.option_id));
}

function cleanTitle(template: string): string {
  return titleTemplate(normalizeTemplate(template))
    .replace(/<[^>]+>/g, "")
    .replace(/\s*\r?\n[- ]*/g, " / ")
    .replace(/\s+/g, " ")
    .trim();
}

function selectRepresentativeIds(
  optionIds: string[],
  locales: OptionLocales,
  optionTags: OptionTagData,
): string[] {
  const available = optionIds.filter(
    (optionId) => locales.ko[optionId] && locales.ja[optionId],
  );
  const selected: string[] = [];
  const seenKinds = new Set<string>();
  for (const optionId of available) {
    const kind = optionTags.options[optionId]?.canonical_tags[0] ?? "untagged";
    if (seenKinds.has(kind)) continue;
    seenKinds.add(kind);
    selected.push(optionId);
    if (selected.length === 3) return selected;
  }
  for (const optionId of available) {
    if (!selected.includes(optionId)) selected.push(optionId);
    if (selected.length === 3) break;
  }
  return selected;
}

export async function loadLandingContent(
  route: SeoRoute,
): Promise<LandingContent> {
  const [updatedDate, optionIds, ko, ja, optionTags] = await Promise.all([
    latestChangelogDate(),
    routeOptionIds(route),
    readJson<OptionLocales["ko"]>("i18n/ko/base_options.json"),
    readJson<OptionLocales["ja"]>("i18n/ja/base_options.json"),
    readJson<OptionTagData>("catalogs/option_tags.json"),
  ]);
  const locales: OptionLocales = { ko, ja };
  const representativeOptions = selectRepresentativeIds(
    optionIds,
    locales,
    optionTags,
  ).map((optionId) => cleanTitle(locales[route.language][optionId]));
  if (route.key !== "home" && representativeOptions.length !== 3) {
    throw new Error(`${route.publicPath}의 대표 옵션 3개를 만들 수 없습니다.`);
  }
  return {
    updatedDate,
    formattedDate: formatDate(updatedDate, route.language),
    representativeOptions,
  };
}
