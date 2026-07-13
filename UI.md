각페이지의 옵션 데이터 렌더링부분에 권장하는 공통 순서는 다음입니다.

무슨 옵션인가
    ↓
실제로 얼마가 적용되는가
    ↓
어떤 종류의 옵션인가
    ↓
어느 단계·티어인가
    ↓
확률 또는 상세 정보

즉 공통 UI 문법은:

옵션명 → 효과/수치 → 분류 → 단계·티어 → 확률·상세
권장 최종 테이블 구조
화면	1열	2열	3열	4열	5열
일반 장비 개방옵션	옵션명	효과	분류	단계	변환 확률
비규격 개방옵션	옵션명	효과	분류	내부 티어	확률
비규격 옵션	옵션명	효과 범위	분류	티어 상세	없음

핵심은 첫 3개 열을 모든 화면에서 통일하는 것입니다.

1. 옵션명
2. 효과
3. 분류

단계와 내부 티어는 의미가 다르므로 같은 이름으로 바꾸지 말고, 같은 네 번째 위치에만 배치합니다.

1. 일반 장비 개방옵션

현재:

옵션 효과 → 옵션명/태그 → 단계 → 확률

권장:

옵션명 → 효과 → 분류 → 단계 → 변환 확률

예시:

옵션명	효과	분류	단계	변환 확률
힘 +[n]	힘 +120	스테이터스	1단계	7%
지식 +[n]	지식 +144	스테이터스	2단계	5%

현재는 태그가 옵션명 아래 작은 글자로 들어가 있는데, 넓은 화면에서는 분류를 별도 열로 빼는 편이 더 명확합니다.

2. 비규격 개방옵션

현재:

옵션명 → 수치 → 확률 → 내부 티어

권장:

옵션명 → 효과 → 분류 → 내부 티어 → 확률

예시:

옵션명	효과	분류	내부 티어	확률
힘 +[n]	힘 +232	스테이터스	1	10%
민첩 +[n]	민첩 +446	스테이터스	2	2.5%

여기에서 수치보다는 일반 개방옵션과 동일하게 효과라고 부르는 것을 권장합니다.

일반 개방옵션: 힘 +120
비규격 개방옵션: 힘 +232

둘 다 “옵션이 실제로 적용하는 결과”이므로 같은 의미입니다.

3. 비규격 옵션

현재:

옵션 → 분류 → 수치 범위 → 티어 상세

권장:

옵션명 → 효과 범위 → 분류 → 티어 상세

예시:

옵션명	효과 범위	분류	티어 상세
무기 최소 공격력 +[n]	+1 ~ +30	피해 · 물리	티어별 값 보기
물리 공격력 증가 [n%]	53% ~ 600%	피해 · 물리	티어별 값 보기

비규격 옵션은 하나의 확정된 효과가 아니라 여러 티어와 후보값을 가지므로, 두 번째 열만 효과가 아니라 효과 범위로 표시합니다.

비규격 개방옵션에 태그 추가

비규격 개방옵션도 option_id가 있으므로 일반 개방옵션과 같은 방식으로 태그를 연결하면 됩니다.

현재 일반 개방옵션은 대략 다음 구조입니다.

CSV option_id
    +
option_tags.json
    ↓
canonical_tags

비규격도 동일하게 변경합니다.

타입 변경

web/src/data/instandardOptions.ts

export type InstandardOpenOptionRow = {
  converter_type: "normal" | "improved" | "fake" | "burning";
  item_group_id: string;
  option_id: string;
  value_0: string;
  value_1: string;
  probability: string;
  tier: string;

  tags: string[];
};
준비 함수 변경

현재:

prepareInstandardOpenRows(csv)

변경:

prepareInstandardOpenRows(csv, optionTags)

예시:

import type { OptionTagData } from "../domain/openOptions/types";

export function prepareInstandardOpenRows(
  csv: string,
  optionTags: OptionTagData,
): InstandardOpenOptionRow[] {
  const rows = parseCsv(csv).map((raw) => ({
    ...raw,
    tags: optionTags.options[raw.option_id]?.canonical_tags ?? [],
  })) as InstandardOpenOptionRow[];

  const required = [
    "converter_type",
    "item_group_id",
    "open_slot",
    "option_id",
    "value_0",
    "value_1",
    "probability",
    "tier",
  ] as const;

  if (
    !rows.length ||
    rows.some((row) => required.some((field) => !row[field]?.trim()))
  ) {
    throw new Error("error.instandardOpenCsv");
  }

  return rows;
}

main.tsx도 다음처럼 변경합니다.

inststandardOpenRows: prepareInstandardOpenRows(
  instandardOpenCsv,
  optionTags,
),

그러면 비규격 개방옵션에서도:

<div className="option-tag-badges">
  {row.tags.map((tag) => (
    <span key={tag}>
      {tagText(language, tag, optionTags)}
    </span>
  ))}
</div>

를 사용할 수 있습니다.

공통 셀 컴포넌트 권장

세 화면의 JSX가 다시 달라지지 않도록 작은 공통 컴포넌트를 만드는 것이 좋습니다.

web/src/components/common/optionTable/
├─ OptionIdentityCell.tsx
├─ OptionValueCell.tsx
├─ OptionTagsCell.tsx
└─ ProgressBadge.tsx
OptionIdentityCell
type Props = {
  title: string;
};

export function OptionIdentityCell({ title }: Props) {
  return (
    <td className="option-identity-cell">
      <strong>{title}</strong>
    </td>
  );
}
OptionTagsCell
type Props = {
  tags: string[];
  language: Language;
  optionTags: OptionTagData;
};

export function OptionTagsCell({
  tags,
  language,
  optionTags,
}: Props) {
  return (
    <td>
      <div className="option-tag-badges">
        {tags.map((tag) => (
          <span key={tag}>
            {tagText(language, tag, optionTags)}
          </span>
        ))}
      </div>
    </td>
  );
}
OptionValueCell
export function OptionValueCell({
  value,
}: {
  value: string;
}) {
  return (
    <td className="option-value-cell">
      <strong>{value}</strong>
    </td>
  );
}

이렇게 하면 일반 개방옵션과 비규격 개방옵션이 동일한 시각적 구조를 사용하게 됩니다.

화면 폭이 좁을 때

스크린샷 첫 번째처럼 브라우저 폭이 좁으면 5열은 다소 답답할 수 있습니다.

따라서 넓은 화면에서는:

옵션명 | 효과 | 분류 | 단계/티어 | 확률

좁은 화면에서는 분류를 옵션명 아래로 넣습니다.

옵션명
└─ 태그들

효과 | 단계/티어 | 확률

CSS 예시:

@media (max-width: 1100px) {
  .option-category-column {
    display: none;
  }

  .option-inline-tags {
    display: flex;
  }
}

@media (min-width: 1101px) {
  .option-category-column {
    display: table-cell;
  }

  .option-inline-tags {
    display: none;
  }
}

즉 동일 데이터를 두 번 렌더링하되 화면 크기에 따라 하나만 보여주는 방식입니다.

태그 필터도 비규격 개방옵션에 추가

비규격 옵션 화면에는 태그 필터가 있지만 비규격 개방옵션에는 현재 없습니다.

통일하려면 open 모드에도 태그 상태를 추가합니다.

const [selectedOpenTags, setSelectedOpenTags] = useState<string[]>([]);

사용 가능한 태그:

const availableOpenTags = useMemo(
  () =>
    [...new Set(equipmentOpenRows.flatMap((row) => row.tags))]
      .sort((a, b) => a.localeCompare(b, "ko")),
  [equipmentOpenRows],
);

필터:

.filter((row) =>
  matchesSelectedTags(
    row.tags,
    selectedOpenTags,
    optionTags,
  ),
)

UI:

<TagFilterPanel
  availableTags={availableOpenTags}
  selectedTags={selectedOpenTags}
  onChange={setSelectedOpenTags}
  language={language}
  optionTags={optionTags}
/>

그렇게 되면 세 화면 모두 태그 탐색 방식도 같아집니다.

일반 개방옵션       태그 표시 + 태그 필터
비규격 옵션         태그 표시 + 태그 필터
비규격 개방옵션     태그 표시 + 태그 필터
최종 추천안
일반 개방옵션
옵션명 | 효과 | 분류 | 단계 | 확률

비규격 개방옵션
옵션명 | 효과 | 분류 | 내부 티어 | 확률

비규격 옵션
옵션명 | 효과 범위 | 분류 | 티어 상세

시각적 규칙도 통일합니다.

옵션명
└─ 일반 굵기 또는 semibold

효과·효과 범위
└─ 가장 강한 강조

분류
└─ 동일한 태그 badge

단계·내부 티어
└─ 동일한 badge 모양, 문구만 다름

확률
└─ 동일한 파란색 숫자 강조

가장 먼저 진행할 작업은 비규격 개방옵션에 option_tags.json을 연결한 뒤, 두 개방옵션 테이블을 옵션명 → 효과 → 분류 → 단계/티어 → 확률 순서로 맞추는 것입니다.