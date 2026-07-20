import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { SeoRoute } from "./routes";

export type LandingContent = {
  updatedDate: string;
  formattedDate: string;
};

const CHANGELOG_PATH = resolve(process.cwd(), "..", "CHANGELOG.md");

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

export async function loadLandingContent(
  route: SeoRoute,
): Promise<LandingContent> {
  const updatedDate = await latestChangelogDate();
  return {
    updatedDate,
    formattedDate: formatDate(updatedDate, route.language),
  };
}
