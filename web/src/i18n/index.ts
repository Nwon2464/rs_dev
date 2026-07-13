export type Language = "ko" | "ja";

const KO_UI_MESSAGES = {
  "app.title": "Red Stone 장비 옵션 탐색기",
  "app.description": "확인할 옵션 시스템을 선택하세요.",
  "common.home": "메인",
  "common.search": "검색",
  "common.reset": "초기화",
  "common.close": "닫기",
  "common.currentLocation": "현재 위치",
  "common.view": "조회하기 →",
  "common.allCategories": "전체 분류",
  "common.allTags": "전체 태그",
  "common.allOpenSlots": "전체 개방 줄",
  "common.noResults": "조건에 맞는 옵션이 없습니다.",
  "common.noSearchResults": "검색 결과가 없습니다.",
  "common.unknownName": "명칭 미확정",
  "language.selector": "언어 선택",
  "theme.dark": "다크 모드",
  "theme.light": "라이트 모드",
  "loading.title": "데이터 불러오는 중",
  "loading.description": "옵션 데이터를 준비하고 있습니다.",
  "loading.progress": "불러오는 중…",
  "error.title": "데이터를 불러올 수 없습니다",
  "error.dataset": "비규격 옵션 JSON을 읽을 수 없습니다.",
  "error.openCsv": "개방 옵션 CSV를 읽을 수 없습니다.",
  "error.instandardOpenCsv": "비규격 개방옵션 CSV를 읽을 수 없습니다.",
  "error.japaneseOptions": "일본어 옵션 JSON을 읽을 수 없습니다.",
  "error.japaneseEquipmentGroups": "일본어 장비 그룹 JSON을 읽을 수 없습니다.",
  "error.japaneseOpenEquipmentBuckets": "일본어 개방옵션 장비 분류 JSON을 읽을 수 없습니다.",
  "error.japaneseOpenMetadata": "일본어 개방옵션 메타데이터 JSON을 읽을 수 없습니다.",
  "error.optionTags": "옵션 태그 JSON을 읽을 수 없습니다.",
  "error.unknown": "데이터를 읽을 수 없습니다.",
  "home.open.title": "일반 장비 개방 옵션",
  "home.open.description": "장비·변환기·등급·개방 줄별 후보와 확률을 확인합니다.",
  "home.open.action": "일반 장비 개방 옵션 보기 →",
  "home.instandard.title": "비규격 장비 옵션",
  "home.instandard.description": "비규격 옵션, 비규격 개방옵션, 티어별 옵션을 탐색합니다.",
  "mode.option.title": "비규격 옵션",
  "mode.option.description": "장비별 비규격 옵션의 수치 범위와 가능한 값을 확인합니다.",
  "mode.open.title": "비규격 개방옵션",
  "mode.open.description": "변환기와 개방 줄별 원본 후보 및 확률을 확인합니다.",
  "mode.tier.title": "티어별 옵션",
  "mode.tier.description": "티어를 기준으로 장비와 옵션을 탐색합니다.",
  "mode.navigation": "비규격 장비 기능",
  "header.instandard.title": "비규격 장비 옵션",
  "header.instandard.description": "장비별 비규격 옵션과 비규격 개방옵션 후보를 전환해 확인합니다.",
  "header.tier.description": "티어를 기준으로 장비와 옵션을 탐색합니다.",
  "header.open.title": "일반 장비 개방 옵션 · 변환기별",
  "header.open.description": "변환기 종류별 확률 필드를 분리한 원본 DAT 직접 조인 결과입니다.",
  "filter.equipment": "장비 선택",
  "filter.changeEquipment": "장비 변경",
  "filter.collapseEquipment": "장비 목록 접기",
  "filter.closeEquipment": "장비 선택 닫기",
  "filter.equipmentSearch": "장비명 검색",
  "filter.equipmentSearchPlaceholder": "장비명 검색…",
  "filter.optionCategory": "옵션 분류",
  "filter.optionSearch": "옵션 검색",
  "filter.optionSearchPlaceholder": "옵션명 검색…",
  "filter.equipmentOrOptionSearchPlaceholder": "장비명 또는 옵션명 검색…",
  "filter.converter": "변환기",
  "filter.converterSelection": "변환기 선택",
  "filter.itemGrade": "아이템 등급",
  "filter.openSlot": "개방 줄",
  "filter.tier": "티어 선택",
  "filter.tags": "태그 필터",
  "filter.currentOptionSearch": "현재 장비군의 옵션 검색",
  "filter.currentOpenSearch": "현재 비규격 개방옵션 후보 검색",
  "filter.currentListSearch": "현재 목록에서 옵션 검색",
  "aria.tierFilters": "티어별 옵션 탐색 조건",
  "aria.optionFilters": "비규격 옵션 탐색 조건",
  "aria.openFilters": "비규격 개방옵션 탐색 조건",
  "tier.selectPrompt": "티어를 선택하세요",
  "tier.selectDescription": "티어를 선택하면 해당 옵션과 적용 장비를 확인할 수 있습니다.",
  "tier.resultsDescription": "옵션을 펼쳐 가능한 수치와 적용 장비를 확인합니다.",
  "tier.appliedEquipment": "적용 장비",
  "tier.possibleValues": "가능 수치",
  "option.resultsDescription": "티어별 수치 보기에서 실제 가능한 값을 모두 확인할 수 있습니다.",
  "option.name": "옵션명",
  "option.category": "분류",
  "option.range": "효과 범위",
  "option.tierDetails": "티어 상세",
  "option.viewTierValues": "티어별 수치 보기",
  "option.supplemental": "로컬 교차검증으로 보완된 옵션",
  "option.activeTiers": "활성 티어",
  "open.resultsTitle": "일반 장비 개방 옵션 후보",
  "open.resultsDescription": "현재 조건에서 가능한 옵션과 적용 확률입니다.",
  "open.effect": "효과",
  "open.nameAndTags": "옵션명 / 태그",
  "open.level": "단계",
  "open.converterProbability": "변환 확률",
  "instandardOpen.resultsDescription": "원본 후보 행을 중복 제거 없이 표시합니다.",
  "instandardOpen.optionName": "옵션명",
  "instandardOpen.value": "효과",
  "instandardOpen.probability": "확률",
  "instandardOpen.internalTier": "내부 티어",
  "warning.incompleteData": "데이터 불완전",
} as const;

export type UiMessageKey = keyof typeof KO_UI_MESSAGES;

const JA_UI_MESSAGES: Record<UiMessageKey, string> = {
  "app.title": "Red Stone 装備オプション検索",
  "app.description": "確認するオプションシステムを選択してください。",
  "common.home": "メイン",
  "common.search": "検索",
  "common.reset": "リセット",
  "common.close": "閉じる",
  "common.currentLocation": "現在位置",
  "common.view": "表示する →",
  "common.allCategories": "すべての分類",
  "common.allTags": "すべてのタグ",
  "common.allOpenSlots": "すべての解放スロット",
  "common.noResults": "条件に一致するオプションがありません。",
  "common.noSearchResults": "検索結果がありません。",
  "common.unknownName": "名称未確認",
  "language.selector": "言語選択",
  "theme.dark": "ダークモード",
  "theme.light": "ライトモード",
  "loading.title": "データ読み込み中",
  "loading.description": "オプションデータを準備しています。",
  "loading.progress": "読み込み中…",
  "error.title": "データを読み込めません",
  "error.dataset": "非規格オプションJSONを読み込めません。",
  "error.openCsv": "解放オプションCSVを読み込めません。",
  "error.instandardOpenCsv": "非規格解放オプションCSVを読み込めません。",
  "error.japaneseOptions": "日本語オプションJSONを読み込めません。",
  "error.japaneseEquipmentGroups": "日本語装備グループJSONを読み込めません。",
  "error.japaneseOpenEquipmentBuckets": "日本語解放オプション装備分類JSONを読み込めません。",
  "error.japaneseOpenMetadata": "日本語解放オプションメタデータJSONを読み込めません。",
  "error.optionTags": "オプションタグJSONを読み込めません。",
  "error.unknown": "データを読み込めません。",
  "home.open.title": "一般装備の解放オプション",
  "home.open.description": "装備・変換器・等級・解放スロット別の候補と確率を確認します。",
  "home.open.action": "一般装備の解放オプションを見る →",
  "home.instandard.title": "非規格装備オプション",
  "home.instandard.description": "非規格オプション、非規格解放オプション、ティア別オプションを検索します。",
  "mode.option.title": "非規格オプション",
  "mode.option.description": "装備別に非規格オプションの数値範囲と候補を確認します。",
  "mode.open.title": "非規格解放オプション",
  "mode.open.description": "変換器と解放スロット別の候補と確率を確認します。",
  "mode.tier.title": "ティア別オプション",
  "mode.tier.description": "ティアを基準に装備とオプションを検索します。",
  "mode.navigation": "非規格装備機能",
  "header.instandard.title": "非規格装備オプション",
  "header.instandard.description": "非規格オプションと非規格解放オプションの候補を切り替えて確認します。",
  "header.tier.description": "ティアを基準に装備とオプションを検索します。",
  "header.open.title": "一般装備の解放オプション・変換器別",
  "header.open.description": "変換器別の確率を分離した元DATの結合結果です。",
  "filter.equipment": "装備選択",
  "filter.changeEquipment": "装備を変更",
  "filter.collapseEquipment": "装備一覧を閉じる",
  "filter.closeEquipment": "装備選択を閉じる",
  "filter.equipmentSearch": "装備名検索",
  "filter.equipmentSearchPlaceholder": "装備名を検索…",
  "filter.optionCategory": "オプション分類",
  "filter.optionSearch": "オプション検索",
  "filter.optionSearchPlaceholder": "オプション名を検索…",
  "filter.equipmentOrOptionSearchPlaceholder": "装備名またはオプション名を検索…",
  "filter.converter": "変換器",
  "filter.converterSelection": "変換器選択",
  "filter.itemGrade": "アイテム等級",
  "filter.openSlot": "解放スロット",
  "filter.tier": "ティア選択",
  "filter.tags": "タグフィルター",
  "filter.currentOptionSearch": "現在の装備グループから検索",
  "filter.currentOpenSearch": "現在の非規格解放候補から検索",
  "filter.currentListSearch": "現在の一覧からオプションを検索",
  "aria.tierFilters": "ティア別オプション検索条件",
  "aria.optionFilters": "非規格オプション検索条件",
  "aria.openFilters": "非規格解放オプション検索条件",
  "tier.selectPrompt": "ティアを選択してください",
  "tier.selectDescription": "ティアを選択すると、オプションと適用装備を確認できます。",
  "tier.resultsDescription": "オプションを開いて数値候補と適用装備を確認します。",
  "tier.appliedEquipment": "適用装備",
  "tier.possibleValues": "数値候補",
  "option.resultsDescription": "ティア別数値から実際の候補をすべて確認できます。",
  "option.name": "オプション名",
  "option.category": "分類",
  "option.range": "効果範囲",
  "option.tierDetails": "ティア詳細",
  "option.viewTierValues": "ティア別数値を見る",
  "option.supplemental": "ローカル照合で補完されたオプション",
  "option.activeTiers": "有効ティア",
  "open.resultsTitle": "一般装備の解放オプション候補",
  "open.resultsDescription": "現在の条件で利用可能なオプションと確率です。",
  "open.effect": "効果",
  "open.nameAndTags": "オプション名 / タグ",
  "open.level": "段階",
  "open.converterProbability": "変換確率",
  "instandardOpen.resultsDescription": "元の候補行を重複除去せず表示します。",
  "instandardOpen.optionName": "オプション名",
  "instandardOpen.value": "効果",
  "instandardOpen.probability": "確率",
  "instandardOpen.internalTier": "内部ティア",
  "warning.incompleteData": "データ不完全",
};

const UI_MESSAGES: Record<Language, Record<UiMessageKey, string>> = {
  ko: KO_UI_MESSAGES,
  ja: JA_UI_MESSAGES,
};

export function uiText(language: Language, key: UiMessageKey): string {
  return UI_MESSAGES[language][key];
}

export function formatResultCount(language: Language, count: number): string { return language === "ja" ? `${count.toLocaleString()}件` : `${count.toLocaleString()}개`; }
export function formatCandidateCount(language: Language, count: number): string { return language === "ja" ? `${count}件の候補` : `${count}개 후보`; }
export function formatAppliedEquipmentCount(language: Language, count: number): string { return language === "ja" ? `適用装備 ${count}件` : `적용 장비 ${count}개`; }
export function formatPossibleValueCount(language: Language, count: number): string { return language === "ja" ? `数値候補 ${count}件` : `가능 수치 ${count}개`; }
export function formatSelectedTagCount(language: Language, count: number): string { return language === "ja" ? `${count}件選択` : `${count}개 선택`; }
export function formatOpenSlot(language: Language, slot: string): string { return language === "ja" ? `解放スロット ${slot}` : `${slot}번째 개방 줄`; }
export function formatTierOptionsTitle(language: Language, tier: number): string { return language === "ja" ? `Tier ${tier} のオプション` : `Tier ${tier}에서 가능한 옵션`; }
export function formatTierValuesTitle(language: Language, tier: number): string { return language === "ja" ? `Tier ${tier} の数値候補` : `Tier ${tier} 가능 수치`; }
export function formatEquipmentOptionTitle(language: Language, equipment: string): string { return language === "ja" ? `${equipment}・非規格オプション` : `${equipment} 비규격 옵션`; }
export function formatEquipmentOpenTitle(language: Language, equipment: string): string { return language === "ja" ? `${equipment}・非規格解放オプション候補` : `${equipment} 비규격 개방옵션 후보`; }
export function formatRangeSubtitle(language: Language, range: string): string { return language === "ja" ? `数値範囲: ${range}` : `수치 범위: ${range}`; }
export function formatActiveTierSummary(language: Language, tiers: number, values: number): string { return language === "ja" ? `有効ティア ${tiers}件・数値候補 ${values}件` : `활성 티어 ${tiers}개 · 가능한 수치 ${values}개`; }
export function formatTierLevel(language: Language, tier: string): string { return language === "ja" ? `${tier}段階` : `${tier}단계`; }
export function formatIncompleteWarningTitle(language: Language, slot: string): string { return `${formatOpenSlot(language, slot)} ${uiText(language, "warning.incompleteData")}`; }
export function formatIncompleteWarning(language: Language, sum: string, missing: string): string[] {
  return language === "ja"
    ? [`現在確認できる候補の確率合計は${sum}%です。`, `元データで約${missing}%分の候補を確認できないため、以下は完全な100%の確率分布ではありません。`, "欠落候補の推測や確率の補正は行っていません。"]
    : [`현재 확인 가능한 후보의 확률 합계는 ${sum}%입니다.`, `약 ${missing}%에 해당하는 후보가 원본 데이터에서 확인되지 않아, 아래 목록은 완전한 100% 확률 분포가 아닙니다.`, "누락 후보를 추정하거나 확률을 임의로 보정하지 않았습니다."];
}

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
