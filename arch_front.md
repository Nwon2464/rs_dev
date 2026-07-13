현재 main.tsx는 다음을 동시에 담당합니다.

main.tsx
├─ 앱 시작
├─ URL 기반 화면 선택
├─ 데이터 로딩
├─ 언어·테마 상태
├─ 홈 화면
├─ 비규격 언어 렌더링
├─ 비규격 옵션 화면
├─ 비규격 개방옵션 화면
├─ 비규격 티어 화면
├─ 장비 선택 팝업
├─ 공통 필터 컴포넌트
└─ 모달

특히 비규격용 순수 계산 함수 7개가 main.tsx에 있고, InstandardTierViewer와 InstandardOpenViewer까지 모두 같은 파일에 들어 있습니다.
또한 현재 InstandardOpenViewer 하나가 mode="option"과 mode="open"을 모두 처리하면서 서로 다른 상태와 UI를 한 컴포넌트에 함께 가지고 있습니다.

1. 이번 리팩터링의 완료 기준

최종적으로 main.tsx에는 아래 책임만 남깁니다.

main.tsx
├─ React 앱 시작
├─ URL에서 view/mode 판별
├─ 전역 언어·테마 상태
├─ 데이터 fetch
├─ 로딩·오류 처리
└─ 해당 Viewer 선택

비규격 옵션 계산이나 화면 JSX는 남기지 않습니다.

2. 권장 최종 폴더 구조
web/src/
├─ main.tsx
│
├─ components/
│  ├─ OpenViewer.tsx
│  ├─ PageHeader.tsx
│  │
│  ├─ common/
│  │  ├─ ExplorerPrimitives.tsx
│  │  └─ Modal.tsx
│  │
│  └─ instandard/
│     ├─ modes.ts
│     ├─ InstandardModeTabs.tsx
│     ├─ InstandardTierViewer.tsx
│     └─ InstandardOptionOpenViewer.tsx
│
├─ data/
│  ├─ generalOpenOptions.ts
│  └─ instandardOptions.ts
│
└─ domain/
   └─ openOptions/
      ├─ instandardRendering.ts
      ├─ localeCatalog.ts
      ├─ normalizeTemplate.ts
      ├─ placeholders.ts
      ├─ renderTemplate.ts
      ├─ tags.ts
      └─ types.ts

이번에는 option과 open 화면을 완전히 두 파일로 나누기보다, 우선 현재 동작을 그대로 유지한 채 InstandardOptionOpenViewer.tsx로 이동하는 것을 권장합니다.

1차 리팩터링
InstandardOptionOpenViewer.tsx
└─ mode="option" | "open" 유지

2차 리팩터링
├─ InstandardOptionViewer.tsx
└─ InstandardOpenViewer.tsx

한 번에 화면 구조까지 쪼개면 기능 회귀 가능성이 커지므로, 이번 작업은 책임 이동만 수행하는 편이 안전합니다.

3. 1단계: 비규격 렌더링 함수를 domain으로 이동

새 파일:

web/src/domain/openOptions/instandardRendering.ts

main.tsx에서 다음 함수들을 그대로 옮깁니다.

localizedEquipmentName()
localizedConverterLabel()
optionTemplate()
optionBindings()
localizedDisplayName()
localizedInstandardOpenOptionRow()
candidateValues()
tierCandidateValues()
rangeLabel()

현재 이 함수들은 locale 템플릿과 value_bindings를 이용해 제목, 실제 수치, 수치 후보 및 범위를 계산합니다. UI JSX가 없는 순수한 도메인 로직이므로 main.tsx에 있을 이유가 없습니다.

권장 이름 변경

이동하면서 한 함수만 이름을 명확하게 바꿉니다.

localizedDisplayName()
→ localizedInstandardOptionTitle()

displayName이라고 하면 실제 수치가 들어간 문구인지 제목인지 구분하기 어렵기 때문입니다.

파일 형태
import type { Language } from "../../i18n";
import type {
  InstandardCatalog,
  InstandardEquipment,
  InstandardOpenOptionRow,
  InstandardOption,
  InstandardTier,
} from "../../data/instandardOptions";
import type {
  EquipmentGroups,
  OpenMetadata,
  OptionLocales,
} from "./types";
import { renderTemplate } from "./renderTemplate";
import { titleTemplate } from "./placeholders";

export function localizedEquipmentName(
  itemGroupId: number,
  koreanName: string,
  language: Language,
  equipmentGroups: EquipmentGroups,
): string {
  return language === "ja"
    ? equipmentGroups[String(itemGroupId)] ?? koreanName
    : koreanName;
}

export function localizedConverterLabel(
  internalKey: string,
  language: Language,
  metadata: OpenMetadata,
): string {
  // 현재 main.tsx의 converterConceptByKey 규칙 이동
}

export function optionBindings(
  catalog: InstandardCatalog,
  optionId: number,
): Record<string, number> {
  return catalog.value_bindings[String(optionId)] ?? {};
}

export function localizedInstandardOptionTitle(
  option: InstandardOption,
  language: Language,
  locales: OptionLocales,
  catalog: InstandardCatalog,
): string {
  // 기존 localizedDisplayName 이동
}

export function localizedInstandardOpenOptionRow(
  row: InstandardOpenOptionRow,
  language: Language,
  locales: OptionLocales,
  catalog: InstandardCatalog,
): { title: string; display: string } {
  // 기존 구현 이동
}

export function candidateValues(/* 기존 인자 */): string[] {
  // 기존 구현 이동
}

export function tierCandidateValues(/* 기존 인자 */): string[] {
  // 기존 구현 이동
}

export function rangeLabel(/* 기존 인자 */): string {
  // 기존 구현 이동
}

export function formatProbability(value: string): string {
  return Number(value).toLocaleString("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });
}

renderTemplate()은 이미 값 배열과 비규격 binding을 처리하므로 변경할 필요가 없습니다.

4. 2단계: 비규격 모드 정의를 분리

새 파일:

web/src/components/instandard/modes.ts

이동 대상:

type InstandardMode = "option" | "open" | "tier";

const instandardModes = [
  ...
];

현재 main.tsx에서 홈 카드와 비규격 탭이 같은 배열을 사용합니다.

다음처럼 export합니다.

import type { UiMessageKey } from "../../i18n";

export type InstandardMode = "option" | "open" | "tier";

export type InstandardModeDefinition = {
  mode: InstandardMode;
  titleKey: UiMessageKey;
  descriptionKey: UiMessageKey;
  iconLabel: string;
  className: string;
};

export const instandardModes: InstandardModeDefinition[] = [
  {
    mode: "option",
    titleKey: "mode.option.title",
    descriptionKey: "mode.option.description",
    iconLabel: "비규격 옵션",
    className: "option",
  },
  {
    mode: "open",
    titleKey: "mode.open.title",
    descriptionKey: "mode.open.description",
    iconLabel: "비규격 개방옵션",
    className: "open",
  },
  {
    mode: "tier",
    titleKey: "mode.tier.title",
    descriptionKey: "mode.tier.description",
    iconLabel: "티어별 옵션",
    className: "tier",
  },
];
5. 3단계: 공통 UI 부품 분리

현재 아래 함수들은 비규격 Viewer가 사용하지만 main.tsx 마지막 부분에 정의되어 있습니다.

FilterGroup
Chip
selectedTagLabel
TagFilterChips
Context
ResultsHead
SectionHead
Empty
Modal
ExplorerPrimitives.tsx

새 파일:

web/src/components/common/ExplorerPrimitives.tsx

다음을 이동합니다.

FilterGroup
Chip
selectedTagLabel
TagFilterChips
Context
ResultsHead
SectionHead
Empty

각 함수 앞에 export만 붙이고 JSX와 CSS 클래스는 변경하지 않습니다.

export function FilterGroup(...) { ... }
export function Chip(...) { ... }
export function selectedTagLabel(...) { ... }
export function TagFilterChips(...) { ... }
export function Context(...) { ... }
export function ResultsHead(...) { ... }
export function SectionHead(...) { ... }
export function Empty(...) { ... }
Modal.tsx

새 파일:

web/src/components/common/Modal.tsx

현재 Modal()을 그대로 이동합니다.

import {
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { uiText, type Language } from "../../i18n";

export function Modal({
  language,
  title,
  subtitle,
  children,
  onClose,
}: {
  language: Language;
  title: string;
  subtitle: string;
  children: ReactNode;
  onClose: () => void;
}) {
  // 현재 구현 그대로
}

CSS 클래스는 변경하지 않습니다.

6. 4단계: 공통 페이지 헤더 이동

새 파일:

web/src/components/PageHeader.tsx

main.tsx의 Header()를 이동합니다.

import type { ReactNode } from "react";
import { uiText, type Language } from "../i18n";

export function PageHeader({
  language,
  title,
  description,
  controls,
  home = true,
}: {
  language: Language;
  title: string;
  description: string;
  controls: ReactNode;
  home?: boolean;
}) {
  return (
    <header>
      <div className="top">
        <div>
          <h1>{title}</h1>
          <p>{description}</p>
        </div>
        <div className="header-actions">
          {home && <a className="home" href="?">← {uiText(language, "common.home")}</a>}
          {controls}
        </div>
      </div>
    </header>
  );
}

기존 prop 이름 themeButton은 실제로 언어 선택기와 테마 버튼을 모두 받고 있으므로 controls로 바꾸는 편이 정확합니다.

OpenViewer.tsx 안의 내부 Header까지 이번에 반드시 바꿀 필요는 없습니다. 이번 작업은 비규격 책임 분리가 목적입니다.

7. 5단계: 비규격 탭 컴포넌트 이동

새 파일:

web/src/components/instandard/InstandardModeTabs.tsx

현재 InstandardModeTabs()를 그대로 이동합니다.

import { Icon } from "../Icon";
import { featureIconId } from "../iconMap";
import { uiText, type Language } from "../../i18n";
import {
  instandardModes,
  type InstandardMode,
} from "./modes";

export function InstandardModeTabs({
  mode,
  language,
}: {
  mode: InstandardMode;
  language: Language;
}) {
  // 기존 JSX 그대로
}
8. 6단계: 티어 Viewer 이동

새 파일:

web/src/components/instandard/InstandardTierViewer.tsx

main.tsx의 InstandardTierViewer() 전체를 이동합니다.

현재 이 컴포넌트는 자체적으로 다음 상태와 계산을 관리합니다.

selectedTier
selectedTierTags
tierQuery
expandedOptionIds
tierNumbers
tierOptions
tierTags
optionResults

필요한 import:

import { useMemo, useState, type ReactNode } from "react";

import { Icon } from "../Icon";
import { equipmentIconId, featureIconId } from "../iconMap";
import { TagFilterPanel } from "../TagFilterPanel";
import { PageHeader } from "../PageHeader";
import {
  Empty,
  FilterGroup,
  ResultsHead,
  TagFilterChips,
} from "../common/ExplorerPrimitives";
import { InstandardModeTabs } from "./InstandardModeTabs";

import {
  localizedEquipmentName,
  localizedInstandardOptionTitle,
  tierCandidateValues,
} from "../../domain/openOptions/instandardRendering";

기존 JSX와 CSS class를 바꾸지 말고 기계적으로 이동합니다.

9. 7단계: 옵션·개방 Viewer 이동

새 파일:

web/src/components/instandard/InstandardOptionOpenViewer.tsx

현재 InstandardOpenViewer() 전체를 이동한 뒤 이름만 변경합니다.

InstandardOpenViewer
→ InstandardOptionOpenViewer

현재 컴포넌트는 실제로 두 화면을 처리하므로 새 이름이 더 정확합니다.

export function InstandardOptionOpenViewer({
  mode,
  source,
  openRows,
  language,
  optionLocales,
  equipmentGroups,
  openMetadata,
  optionTags,
  controls,
}: Props) {
  // 현재 구현 이동
}
prop 이름도 정리

현재 이름:

japaneseEquipmentGroups
japaneseOpenMetadata
themeButton

권장 이름:

equipmentGroups
openMetadata
controls

해당 JSON들은 현재 한국어·일본어 공통 UI 메타데이터이므로 더 이상 japanese라는 이름이 적절하지 않습니다.

이 컴포넌트로 이동할 상태
equipmentName
selectedTags
converter
selectedOpenLines
query
equipmentPickerOpen
equipmentQuery
selectedOption
equipmentToggleRef
equipmentPickerRef
equipmentSearchRef
이 컴포넌트로 이동할 이벤트 함수
closeEquipmentPicker()
changeEquipment()
toggleOpenLine()

그리고 기존 로컬 formatProbability는 instandardRendering.ts에서 import합니다.

유지해야 할 동작
option mode
├─ 장비 선택 팝업
├─ 태그 필터
├─ 옵션 검색
├─ 수치 범위
├─ 티어 상세 모달
└─ supplemental 표시

open mode
├─ 장비 필터
├─ 변환기 필터
├─ 개방 슬롯 필터
├─ 옵션 검색
├─ 확률 합계 경고
└─ 개방옵션 테이블

현재 두 화면의 JSX는 mode 조건으로 분리돼 있으므로 그대로 옮기면 됩니다.

10. main.tsx에서 정확히 삭제할 대상
타입 및 상수 삭제
type InstandardMode = ...
type Tier = ...
type Equipment = ...
type SourceDataset = ...
type JapaneseBaseOptions = ...
type JapaneseEquipmentGroups = ...
type ConverterConcept = ...

const converterConceptByKey = ...
const instandardModes = ...

SourceDataset 대신 InstandardCatalog을 직접 사용합니다.

함수 삭제
localizedEquipmentName
localizedConverterLabel
optionTemplate
optionBindings
localizedDisplayName
localizedInstandardOpenOptionRow
candidateValues
tierCandidateValues
rangeLabel

InstandardModeTabs
InstandardTierViewer
InstandardOpenViewer

FilterGroup
Chip
selectedTagLabel
TagFilterChips
Context
ResultsHead
SectionHead
Modal

Empty도 공통 컴포넌트에서 import하면 삭제합니다.

삭제할 import

현재 main.tsx에서 다음 import는 Viewer 이동 후 필요하지 않습니다.

useMemo
useRef

SelectedTagChips
TagFilterPanel

equipmentIconId

matchesSelectedTags
tagSearchText
tagText
toggleSelectedTag

renderTemplate
titleTemplate

InstandardEquipment
InstandardOption
InstandardTier

다음 i18n 함수들도 Viewer로 이동하므로 main.tsx에서 제거합니다.

formatActiveTierSummary
formatAppliedEquipmentCount
formatCandidateCount
formatEquipmentOpenTitle
formatEquipmentOptionTitle
formatIncompleteWarning
formatIncompleteWarningTitle
formatOpenSlot
formatPossibleValueCount
formatRangeSubtitle
formatResultCount
formatTierOptionsTitle
formatTierValuesTitle

main.tsx에는 다음만 남으면 됩니다.

import {
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  loadLanguage,
  saveLanguage,
  uiText,
  type Language,
  type UiMessageKey,
} from "./i18n";
11. 변경 후 main.tsx의 핵심 형태
import { useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";

import { Icon } from "./components/Icon";
import { OpenViewer } from "./components/OpenViewer";
import { PageHeader } from "./components/PageHeader";
import { Empty } from "./components/common/ExplorerPrimitives";
import { InstandardTierViewer } from "./components/instandard/InstandardTierViewer";
import { InstandardOptionOpenViewer } from "./components/instandard/InstandardOptionOpenViewer";
import {
  instandardModes,
  type InstandardMode,
} from "./components/instandard/modes";

import { prepareGeneralOpenRows } from "./data/generalOpenOptions";
import {
  prepareInstandardOpenRows,
  type InstandardCatalog,
  type InstandardOpenOptionRow,
} from "./data/instandardOptions";

function App() {
  // URL 판별
  // 테마·언어 상태
  // 데이터 로딩
  // 오류·로딩 처리

  if (view === "home") {
    return <Home language={language} controls={headerControls} />;
  }

  if (view === "open") {
    return (
      <OpenViewer
        rows={resources.openRows}
        language={language}
        optionLocales={resources.optionLocales}
        openEquipmentBuckets={resources.openEquipmentBuckets}
        openMetadata={resources.openMetadata}
        optionTags={resources.optionTags}
        themeButton={headerControls}
      />
    );
  }

  if (view === "instandard" && instandardMode === "tier") {
    return (
      <InstandardTierViewer
        source={resources.source}
        language={language}
        optionLocales={resources.optionLocales}
        equipmentGroups={resources.equipmentGroups}
        optionTags={resources.optionTags}
        controls={headerControls}
      />
    );
  }

  if (
    view === "instandard"
    && (instandardMode === "option" || instandardMode === "open")
  ) {
    return (
      <InstandardOptionOpenViewer
        mode={instandardMode}
        source={resources.source}
        openRows={resources.instandardOpenRows}
        language={language}
        optionLocales={resources.optionLocales}
        equipmentGroups={resources.equipmentGroups}
        openMetadata={resources.openMetadata}
        optionTags={resources.optionTags}
        controls={headerControls}
      />
    );
  }

  return null;
}

createRoot(document.getElementById("root")!).render(<App />);

main.tsx의 화면 선택 자체는 현재와 동일하게 유지합니다. 현재도 URL에 따라 세 Viewer를 선택하는 구조는 이미 올바릅니다.

12. 이번 작업에서 변경하면 안 되는 것
변경 금지
├─ CSV 및 JSON 스키마
├─ fetch 경로
├─ option_id 처리
├─ locale 템플릿 처리 결과
├─ value_bindings 처리
├─ 필터 기본값
├─ 정렬 순서
├─ 확률 이상 경고 기준 0.06
├─ CSS 클래스 이름
├─ URL query 구조
└─ 화면 문구

즉 이번 작업은 파일 이동과 import 재연결만 하는 구조 리팩터링이어야 합니다.

13. Codex에 전달할 최종 지시문
현재 web/src/main.tsx에 포함된 비규격 프론트엔드 책임을 별도
모듈로 분리하라. UI, CSS, 데이터 스키마, 정렬, 필터 기본값,
렌더링 결과에는 어떠한 동작 변경도 하지 않는다.

1. web/src/domain/openOptions/instandardRendering.ts를 생성한다.

main.tsx에서 다음 순수 함수를 이동한다.
- localizedEquipmentName
- localizedConverterLabel
- optionTemplate
- optionBindings
- localizedDisplayName
- localizedInstandardOpenOptionRow
- candidateValues
- tierCandidateValues
- rangeLabel

localizedDisplayName은 localizedInstandardOptionTitle로 이름을 변경한다.
formatProbability도 이 파일에 순수 함수로 추가한다.

2. web/src/components/instandard/modes.ts를 생성한다.

다음을 이동하고 export한다.
- InstandardMode 타입
- instandardModes 상수

3. web/src/components/common/ExplorerPrimitives.tsx를 생성한다.

다음을 main.tsx에서 이동하고 export한다.
- FilterGroup
- Chip
- selectedTagLabel
- TagFilterChips
- Context
- ResultsHead
- SectionHead
- Empty

기존 JSX와 CSS class를 변경하지 않는다.

4. web/src/components/common/Modal.tsx를 생성하고
main.tsx의 Modal 컴포넌트를 그대로 이동한다.

5. web/src/components/PageHeader.tsx를 생성하고 main.tsx의 Header를
이동한다. themeButton prop은 실제 의미에 맞게 controls로 변경한다.

6. web/src/components/instandard/InstandardModeTabs.tsx를 생성하고
main.tsx의 InstandardModeTabs를 이동한다.

7. web/src/components/instandard/InstandardTierViewer.tsx를 생성하고
main.tsx의 InstandardTierViewer 전체를 이동한다.

비규격 표시 계산은 직접 구현하지 말고
domain/openOptions/instandardRendering.ts에서 import한다.

8. web/src/components/instandard/InstandardOptionOpenViewer.tsx를 생성한다.

현재 main.tsx의 InstandardOpenViewer 전체를 이동하고 이름을
InstandardOptionOpenViewer로 변경한다. mode="option" | "open" 구조는
이번 작업에서 유지한다.

prop 이름을 다음처럼 정리한다.
- japaneseEquipmentGroups → equipmentGroups
- japaneseOpenMetadata → openMetadata
- themeButton → controls

기존 상태, 필터, 정렬, 장비 선택 팝업, 태그 필터, 모달,
확률 경고 및 JSX 구조는 그대로 유지한다.

9. main.tsx에서는 다음만 담당하게 한다.
- 앱 시작
- URL view/mode 판별
- 언어와 테마 상태
- 리소스 fetch
- 로딩 및 오류 처리
- Home/OpenViewer/Instandard Viewer 라우팅

main.tsx에서 이동 완료된 타입, 함수, 컴포넌트 및 미사용 import를
모두 삭제한다.

10. 변경하지 말아야 할 항목:
- data/open_options fetch 경로
- CSV/JSON 구조
- locale와 placeholder 처리 결과
- value_bindings
- 필터 초기값
- 정렬 순서
- 확률 이상 판정 tolerance
- CSS 클래스
- URL query
- UI 문구

11. 완료 후 다음을 확인한다.
- main.tsx에 InstandardTierViewer 함수 정의가 없어야 한다.
- main.tsx에 InstandardOpenViewer 함수 정의가 없어야 한다.
- main.tsx에 candidateValues/rangeLabel 등의 비규격 렌더링 함수가
  없어야 한다.
- npm run build가 성공해야 한다.
- npm run build:all이 성공해야 한다.
- 기존 화면의 한국어/일본어 표시와 필터 동작이 동일해야 한다.
- git diff --check가 통과해야 한다.