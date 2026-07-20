import type { SeoRoute } from "./routes";
import siteMetadata from "./siteMetadata.json";

export type LandingContent = {
  updatedDate: string;
  formattedDate: string;
};

function dataUpdateDate(): string {
  const date = siteMetadata.last_data_update;
  const parsed = new Date(`${date}T00:00:00Z`);
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
    Number.isNaN(parsed.valueOf()) ||
    parsed.toISOString().slice(0, 10) !== date
  ) {
    throw new Error(
      "siteMetadata.json의 last_data_update를 YYYY-MM-DD 형식으로 입력해야 합니다.",
    );
  }
  return date;
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
  const updatedDate = dataUpdateDate();
  return {
    updatedDate,
    formattedDate: formatDate(updatedDate, route.language),
  };
}
