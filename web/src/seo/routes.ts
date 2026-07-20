import type { Language } from "../i18n";
import type { InstandardMode } from "../components/instandard/modes";
import type { View } from "../main";

export type SeoRoute = {
  key: "home" | "open" | "instandard-option" | "instandard-open" | "tier";
  path: string | undefined;
  publicPath: string;
  language: Language;
  view: View;
  mode: InstandardMode | null;
  heading: string;
  title: string;
  description: string;
  featureSummary: string;
};

const SITE_NAMES: Record<Language, string> = {
  ja: "Red Stone 装備オプション検索",
  ko: "붉은보석 장비 옵션 검색",
};

type PageCopy = Pick<SeoRoute, "key" | "view" | "mode"> & {
  slug: string;
  title: Record<Language, string>;
  description: Record<Language, string>;
  featureSummary: Record<Language, string>;
};

const PAGES: PageCopy[] = [
  {
    key: "home",
    slug: "",
    view: "home",
    mode: null,
    title: {
      ja: "Red Stone 装備オプション検索",
      ko: "붉은보석 장비 옵션 검색",
    },
    description: {
      ja: "一般装備の解放オプションと、非規格装備のオプション・解放オプション・ティア別数値を検索できます。",
      ko: "일반 장비 개방 옵션과 비규격 장비의 옵션·개방 옵션·티어별 수치를 검색할 수 있습니다.",
    },
    featureSummary: {
      ja: "一般装備と非規格装備のオプション情報を日本語・韓国語で確認できます。",
      ko: "일반 장비와 비규격 장비의 옵션 정보를 일본어·한국어로 확인할 수 있습니다.",
    },
  },
  {
    key: "open",
    slug: "open-options",
    view: "open",
    mode: null,
    title: {
      ja: "一般装備の解放オプション",
      ko: "붉은보석 일반 장비 개방 옵션",
    },
    description: {
      ja: "一般装備の解放オプション候補と確率を、装備・変換器・等級・解放スロット別に確認できます。",
      ko: "일반 장비의 개방 옵션 후보와 확률을 장비·변환기·등급·개방 줄별로 확인할 수 있습니다.",
    },
    featureSummary: {
      ja: "装備・変換器・等級・解放スロット・タグで候補と確率を絞り込めます。",
      ko: "장비·변환기·등급·개방 줄·태그로 후보와 확률을 좁혀 볼 수 있습니다.",
    },
  },
  {
    key: "instandard-option",
    slug: "instandard/options",
    view: "instandard",
    mode: "option",
    title: {
      ja: "非規格装備オプション",
      ko: "붉은보석 비규격 장비 옵션",
    },
    description: {
      ja: "非規格装備のオプションと数値範囲を装備別に確認できます。",
      ko: "비규격 장비의 옵션과 수치 범위를 장비별로 확인할 수 있습니다.",
    },
    featureSummary: {
      ja: "装備選択、オプション検索、タグ絞り込み、ティア別数値の確認に対応しています。",
      ko: "장비 선택, 옵션 검색, 태그 필터와 티어별 수치 확인을 지원합니다.",
    },
  },
  {
    key: "instandard-open",
    slug: "instandard/open-options",
    view: "instandard",
    mode: "open",
    title: {
      ja: "非規格装備の解放オプション",
      ko: "붉은보석 비규격 장비 개방 옵션",
    },
    description: {
      ja: "非規格装備の解放オプション候補と確率を、変換器と解放スロット別に確認できます。",
      ko: "비규격 장비의 개방 옵션 후보와 확률을 변환기와 개방 줄별로 확인할 수 있습니다.",
    },
    featureSummary: {
      ja: "装備・変換器・解放スロット・タグで候補と出現確率を確認できます。",
      ko: "장비·변환기·개방 줄·태그별 후보와 출현 확률을 확인할 수 있습니다.",
    },
  },
  {
    key: "tier",
    slug: "instandard/tier-values",
    view: "instandard",
    mode: "tier",
    title: {
      ja: "非規格装備のティア別オプション数値",
      ko: "붉은보석 비규격 장비 티어별 옵션 수치",
    },
    description: {
      ja: "ティアを基準に、非規格装備のオプション数値と適用装備を確認できます。",
      ko: "티어를 기준으로 비규격 장비의 옵션 수치와 적용 장비를 확인할 수 있습니다.",
    },
    featureSummary: {
      ja: "ティアを選び、オプション数値、適用装備、タグをまとめて確認できます。",
      ko: "티어를 선택해 옵션 수치, 적용 장비와 태그를 함께 확인할 수 있습니다.",
    },
  },
];

export const SEO_ROUTES: SeoRoute[] = (["ja", "ko"] as const).flatMap(
  (language) =>
    PAGES.map((page) => {
      const languagePrefix = language === "ko" ? "ko/" : "";
      const path = `${languagePrefix}${page.slug}`.replace(/\/$/, "");
      const pageTitle = page.title[language];
      return {
        key: page.key,
        path: path || undefined,
        publicPath: `/rs_dev/${path ? `${path}/` : ""}`,
        language,
        view: page.view,
        mode: page.mode,
        heading: pageTitle,
        title:
          page.key === "home"
            ? pageTitle
            : `${pageTitle} | ${SITE_NAMES[language]}`,
        description: page.description[language],
        featureSummary: page.featureSummary[language],
      };
    }),
);

export function translatedRoute(route: SeoRoute): SeoRoute {
  const language = route.language === "ja" ? "ko" : "ja";
  return SEO_ROUTES.find(
    (candidate) => candidate.key === route.key && candidate.language === language,
  )!;
}
