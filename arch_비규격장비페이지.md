비규격은 먼저 두 종류의 데이터를 분리해서 전환해야 합니다.

비규격 데이터
├─ InstandardEquip.dat
│  └─ 장비군별 옵션 배정·티어·10개 수치 후보·태그
│
└─ item_option_open.dat의 section_type=11
   └─ 일반·개량·모조·불타는 변환기의 개방 후보·확률

현재는 collect_instandard_equipment.py 한 번으로 JSON, 티어 CSV, 렌더링 CSV, Markdown까지 만들고 있으며, 별도의 export_instandard_open_options.py가 다시 비규격 개방옵션 CSV를 만듭니다.
또한 instandard_open_options.py가 일반 개방옵션 모듈의 parse_blocks()와 option_display()에 의존하면서 option_name, option_display까지 CSV에 저장하고 있습니다.

비규격 전환 계획: 10단계
1. 기존 데이터의 기준값만 기록

기존 CSV를 삭제하기 전에 비교용 보고서 하나만 만듭니다.

migration_baseline.json
├─ 장비 그룹 수
├─ 옵션 정의 수
├─ 선택 가능한 option_id 목록
├─ 장비군별 option_id 목록
├─ 티어별 행 수
├─ 활성·비활성 티어 수
├─ 변환기별 행 수
├─ open_slot별 확률 합계
└─ 보완 배정 option_id 목록

이유: 기존 CSV를 보존하지 않아도 새 파이프라인에서 누락되거나 변경된 데이터를 확인할 수 있습니다.

2. 비규격 공통 스키마 정의
장비군
InstandardEquipmentGroup
├─ item_group_id
├─ item_group_name
└─ bucket_signature_index
옵션 배정
InstandardOptionAssignment
├─ item_group_id
├─ option_id
├─ option_order
├─ assignment_source
│  ├─ raw
│  └─ supplemental
└─ evidence_id
티어 수치
InstandardTierRoll
├─ option_id
├─ raw_tier_index
├─ option_level_raw
├─ enabled
├─ roll_index
├─ value_0
├─ value_1
└─ value_2
변환기 개방 후보
InstandardOpenOptionRow
├─ converter_type
├─ item_group_id
├─ bucket_signature_index
├─ bucket_group_ids
├─ section_type
├─ section_group
├─ open_slot
├─ candidate_index
├─ option_id
├─ value_0
├─ value_1
├─ probability
├─ probability_source
├─ tier
├─ mapping_status
├─ source_block_index
└─ source_file_offset

제외되는 필드:

├─ option_name
├─ short_text
├─ option_template
├─ option_display
├─ display_min / display_max
└─ roll별 렌더링 문자열

이유: 수치 데이터와 언어별 표시 문구를 분리하기 위해서입니다.

3. InstandardEquip.dat 파서를 순수 파서로 분리
InstandardEquip.dat
        │
        ▼
parse_instandard_equip()
├─ OptionsByItemType
├─ OptionData
├─ TierData
├─ PrefixTagName
├─ MaterialData
└─ DisJointData

이 단계에서는 다음을 하지 않습니다.

하지 않음
├─ capa.dat 조인
├─ 장비 그룹명 조인
├─ 보완 옵션 추가
├─ 옵션 문구 렌더링
└─ CSV·JSON 출력

현재 모듈은 MessagePack 해석부터 capa.dat, simpleGameText.dat, 보완 배정, 티어 계산과 출력까지 한 파일에서 처리하고 있습니다.

이유: 원본 바이너리 해석과 업무 규칙을 분리해야 원본 구조가 바뀌었는지, 전처리 규칙이 바뀌었는지 구분할 수 있습니다.

4. 장비군·옵션 배정·티어 수치로 정규화
파싱된 InstandardEquip 데이터
        │
        ├─ OptionsByItemType
        │      ↓
        │  InstandardOptionAssignment
        │
        ├─ OptionData
        │      ↓
        │  옵션 메타데이터
        │
        └─ TierData
               ↓
           InstandardTierRoll

simpleGameText.dat는 장비 그룹명만 제공합니다.

item_group_id
        +
simpleGameText.dat
        ↓
item_group_name

이 단계에서 비활성 센티널도 명시적으로 표시합니다.

OptionLevel = 99999
→ enabled = false

이유: 중첩된 MessagePack 구조를 행 단위 데이터로 바꿔야 검증과 비교가 쉬워집니다.

5. 보완 배정을 별도 설정으로 분리

현재 922와 1045는 코드 내부 상수로 목걸이에 추가되고 있습니다.

이를 파서에서 제거하고 별도 설정 파일로 옮깁니다.

config/instandard/supplemental_assignments.json
{
  "922": {
    "item_group_id": 8,
    "basis": "item_option_open.dat equipment target list"
  },
  "1045": {
    "item_group_id": 8,
    "basis": "item.dat fixed-effect references",
    "item_ids": [1390, 5238, 7145, 7432, 7433]
  }
}

처리 흐름:

원본 OptionsByItemType 배정
        +
supplemental_assignments.json
        ↓
최종 InstandardOptionAssignment

출력에서는 반드시 구분합니다.

assignment_source
├─ raw
└─ supplemental

이유: 추론·교차검증으로 추가한 데이터를 원본 데이터처럼 보이게 만들지 않기 위해서입니다.

6. 비규격 기본 데이터 중간 산출물 생성
data/intermediate/instandard/
├─ equipment_groups.csv
├─ option_assignments.csv
├─ tier_rolls.csv
└─ option_metadata.json
equipment_groups.csv
item_group_id,item_group_name,bucket_signature_index
8,목걸이,4
option_assignments.csv
item_group_id,option_id,option_order,assignment_source,evidence_id
8,922,15,supplemental,inst-922-necklace
tier_rolls.csv
option_id,raw_tier_index,option_level_raw,enabled,roll_index,value_0,value_1,value_2
922,0,100,true,0,10,0,0

이유: 장비 배정 오류와 수치 해석 오류를 각각 독립적으로 검사할 수 있습니다.

7. UI용 비규격 카탈로그 생성

중간 산출물을 다시 UI가 사용하기 좋은 JSON으로 조립합니다.

equipment_groups.csv
option_assignments.csv
tier_rolls.csv
option_metadata.json
        │
        ▼
data/processed/instandard/catalog.json

예시:

{
  "schema_version": 1,
  "equipment": [
    {
      "item_group_id": 8,
      "item_group_name": "목걸이",
      "option_ids": [922, 1045]
    }
  ],
  "options": [
    {
      "option_id": 922,
      "source_tags": ["피해"],
      "canonical_tags": ["damage"],
      "tiers": [
        {
          "tier": 0,
          "option_level_raw": 100,
          "rolls": [
            [10, 0, 0],
            [12, 0, 0]
          ]
        }
      ]
    }
  ]
}

포함하지 않는 것:

catalog.json에 없음
├─ 한국어 옵션 문구
├─ 일본어 옵션 문구
├─ option_name
└─ 미리 렌더링한 display 문자열

이유: 비규격의 티어와 10개 수치 후보는 중첩 구조이므로 UI 최종 데이터는 CSV 여러 개보다 JSON 하나가 적합합니다.

8. 비규격 변환기 CSV를 각각 생성

item_option_open.dat의 section_type=11 블록을 사용합니다.

item_option_open.dat
        │
        ▼
section_type = 11 블록 탐색
        │
        ├─ section_group 0 + float_a
        │  └─ normal
        │
        ├─ section_group 0 + float_b
        │  └─ improved
        │
        ├─ section_group 1 + float_a
        │  └─ fake
        │
        └─ section_group 3 + float_a
           └─ burning

현재도 이 네 개의 뷰를 사용하지만 한 번에 하나의 CSV로 출력하고 있습니다.

새 출력:

data/intermediate/instandard/open_options/
├─ normal_open_options.csv
├─ improved_open_options.csv
├─ fake_open_options.csv
└─ burning_open_options.csv

각 CSV는 동일한 InstandardOpenOptionRow 스키마를 사용합니다.

이유: 일반 개방옵션과 마찬가지로 변환기별 파싱 결과와 확률을 따로 검증하기 위해서입니다.

9. 변환기 CSV 병합 및 통합 검증
normal_open_options.csv
improved_open_options.csv
fake_open_options.csv
burning_open_options.csv
        │
        ▼
merge_instandard_open_options()
        │
        ▼
data/processed/instandard/open_option_rows.csv

검증 항목:

├─ 장비 그룹 전체 포함 여부
├─ bucket signature 중복·누락
├─ section_type = 11
├─ section_group 규칙
├─ option_id 유효성
├─ open_slot 범위
├─ 슬롯별 확률 합계
├─ 화면에서 확인한 기준 행
└─ 알려진 확률 이상값

현재 코드는 34개 장비 그룹, 10개 signature, 특정 화면 확인 행과 알려진 확률 이상값을 직접 코드 안에서 검사하고 있습니다.

이 기준은 다음으로 옮깁니다.

tests/fixtures/instandard/
├─ expected_structure.json
├─ screen_confirmed_rows.json
└─ known_probability_anomalies.json

이유: 실제 변환 로직과 특정 데이터 리비전의 기대값을 분리하기 위해서입니다.

10. 공통 언어 처리·UI 전환 후 기존 파일 삭제
비규격 기본 옵션 표시
catalog.json의 option_id
        +
선택 locale의 base_options.json
        │
        ▼
공통 normalizeTemplate()
        │
        ▼
공통 placeholder 분석
        │
        ▼
renderTemplate(template, values)

비규격 TierValue는 값이 세 개이므로 공통 렌더러는 고정된 두 인수가 아니라 배열을 받아야 합니다.

일반 개방옵션
values = [value_0, value_1]

비규격
values = [value_0, value_1, value_2]
[0] → values[0]
[1] → values[1]
[2] → values[2]

현재 비규격 렌더러도 [0], [1], [2]를 처리하고 있습니다.

922·1045 값 연결 예외

현재는 렌더링 직전에 문자열의 [1]을 [0]으로 직접 치환합니다.

이를 별도 설정으로 옮깁니다.

config/instandard/value_bindings.json
{
  "922": {
    "1": 0
  },
  "1045": {
    "1": 0
  }
}

렌더러:

template placeholder [1]
        │
        ▼
option_id별 value binding 확인
        │
        ▼
values[0] 사용

이유: 특정 옵션의 예외를 문자열 치환 코드 안에 숨기지 않기 위해서입니다.

최종 폴더 구조 (일반개방의 전반적인 처리도 포함되어있음)
지금은 RS_DEV-JAPANESE-UI = rs_dev 이라 가정한다. 
rs_dev/
├─ pyproject.toml
├─ README.md
│
├─ config/
│  └─ open_options/
│     └─ instandard/
│        ├─ supplemental_assignments.json
│        └─ value_bindings.json
│
├─ src/
│  └─ rs_dev/
│     ├─ models/
│     │  ├─ __init__.py
│     │  │
│     │  ├─ open_option_raw.py
│     │  │  ├─ OpenOptionParsedRow
│     │  │  └─ OpenOptionBlock
│     │  │
│     │  ├─ general_open_option.py
│     │  │  └─ GeneralOpenOptionRow
│     │  │
│     │  ├─ instandard_equipment.py
│     │  │  ├─ InstandardEquipmentGroup
│     │  │  ├─ InstandardOptionAssignment
│     │  │  ├─ InstandardTierRoll
│     │  │  └─ InstandardCatalog
│     │  │
│     │  ├─ instandard_open_option.py
│     │  │  └─ InstandardOpenOptionRow
│     │  │
│     │  └─ option_template.py
│     │     └─ LocalizedOptionTemplate
│     │
│     ├─ parsers/
│     │  ├─ __init__.py
│     │  ├─ binary.py
│     │  │
│     │  ├─ item_option_open.py
│     │  │  └─ 일반·비규격이 함께 사용하는 공통 DAT 파서
│     │  │
│     │  ├─ simple_game_text.py
│     │  │  └─ group_id → 장비 그룹명
│     │  │
│     │  ├─ capa.py
│     │  │  └─ 한국어 옵션 템플릿 원본
│     │  │
│     │  ├─ japanese_llt.py
│     │  │  └─ 일본어 옵션 템플릿 원본
│     │  │
│     │  └─ instandard_equip.py
│     │     └─ InstandardEquip.dat 전용 파서
│     │
│     └─ open_options/
│        ├─ __init__.py
│        │
│        ├─ common/
│        │  ├─ __init__.py
│        │  ├─ value_unpacking.py
│        │  │  └─ packed_value → value_0/value_1
│        │  │
│        │  ├─ group_mapping.py
│        │  │  └─ group_ids → group_names
│        │  │
│        │  ├─ csv_io.py
│        │  │  └─ 공통 CSV 읽기·쓰기
│        │  │
│        │  └─ validation.py
│        │     ├─ 자료형 검증
│        │     ├─ 확률 검증
│        │     └─ 중복 검증
│        │
│        ├─ converters/
│        │  ├─ __init__.py
│        │  ├─ specs.py
│        │  │  ├─ normal
│        │  │  ├─ improved
│        │  │  ├─ fake
│        │  │  └─ burning
│        │  │
│        │  └─ classify.py
│        │     └─ section_group·확률 필드 판별
│        │
│        ├─ general/
│        │  ├─ __init__.py
│        │  ├─ transform.py
│        │  │  └─ OpenOptionBlock
│        │  │     → GeneralOpenOptionRow
│        │  │
│        │  ├─ export_converters.py
│        │  │  ├─ normal_open_options.csv
│        │  │  ├─ improved_open_options.csv
│        │  │  ├─ fake_open_options.csv
│        │  │  └─ burning_open_options.csv
│        │  │
│        │  ├─ merge.py
│        │  │  └─ general/open_option_rows.csv
│        │  │
│        │  ├─ validation.py
│        │  └─ pipeline.py
│        │
│        ├─ instandard/
│        │  ├─ __init__.py
│        │  │
│        │  ├─ equipment/
│        │  │  ├─ normalize.py
│        │  │  ├─ assignments.py
│        │  │  ├─ supplemental.py
│        │  │  ├─ tiers.py
│        │  │  ├─ catalog.py
│        │  │  └─ validation.py
│        │  │
│        │  ├─ open_options/
│        │  │  ├─ transform.py
│        │  │  │  └─ section_type=11
│        │  │  │     → InstandardOpenOptionRow
│        │  │  │
│        │  │  ├─ export_converters.py
│        │  │  │  ├─ normal_open_options.csv
│        │  │  │  ├─ improved_open_options.csv
│        │  │  │  ├─ fake_open_options.csv
│        │  │  │  └─ burning_open_options.csv
│        │  │  │
│        │  │  ├─ merge.py
│        │  │  │  └─ instandard/open_option_rows.csv
│        │  │  │
│        │  │  └─ validation.py
│        │  │
│        │  └─ pipeline.py
│        │
│        ├─ templates/
│        │  ├─ __init__.py
│        │  ├─ normalize.py
│        │  ├─ placeholders.py
│        │  ├─ bindings.py
│        │  ├─ render.py
│        │  └─ audit.py
│        │
│        ├─ locales/
│        │  ├─ __init__.py
│        │  ├─ korean.py
│        │  │  └─ capa short_text/description
│        │  │     → ko/base_options.json
│        │  │
│        │  └─ japanese.py
│        │     └─ japanese.llt section 22
│        │        → ja/base_options.json
│        │
│        └─ pipeline.py
│           ├─ 일반 파이프라인 실행
│           ├─ 비규격 파이프라인 실행
│           ├─ locale 생성
│           └─ 전체 감사 실행
│
├─ scripts/
│  ├─ build_open_options.py
│  │  └─ 일반·비규격·locale 전체 생성
│  │
│  ├─ build_general_open_options.py
│  ├─ build_instandard.py
│  └─ audit_open_options.py
│
├─ data/
│  ├─ intermediate/
│  │  └─ open_options/
│  │     ├─ general/
│  │     │  ├─ normal_open_options.csv
│  │     │  ├─ improved_open_options.csv
│  │     │  ├─ fake_open_options.csv
│  │     │  └─ burning_open_options.csv
│  │     │
│  │     └─ instandard/
│  │        ├─ equipment_groups.csv
│  │        ├─ option_assignments.csv
│  │        ├─ tier_rolls.csv
│  │        ├─ option_metadata.json
│  │        │
│  │        └─ open_options/
│  │           ├─ normal_open_options.csv
│  │           ├─ improved_open_options.csv
│  │           ├─ fake_open_options.csv
│  │           └─ burning_open_options.csv
│  │
│  ├─ processed/
│  │  └─ open_options/
│  │     ├─ general/
│  │     │  └─ open_option_rows.csv
│  │     │
│  │     ├─ instandard/
│  │     │  ├─ catalog.json
│  │     │  └─ open_option_rows.csv
│  │     │
│  │     └─ i18n/
│  │        ├─ ko/
│  │        │  └─ base_options.json
│  │        └─ ja/
│  │           └─ base_options.json
│  │
│  └─ reports/
│     └─ open_options/
│        ├─ general/
│        │  ├─ migration_baseline.json
│        │  └─ converter_validation.json
│        │
│        ├─ instandard/
│        │  ├─ migration_baseline.json
│        │  ├─ assignment_audit.json
│        │  ├─ tier_audit.json
│        │  └─ converter_validation.json
│        │
│        └─ locale_audit.json
│
├─ tests/
│  ├─ fixtures/
│  │  └─ open_options/
│  │     ├─ general/
│  │     └─ instandard/
│  │
│  └─ open_options/
│     ├─ common/
│     │  ├─ test_value_unpacking.py
│     │  └─ test_validation.py
│     │
│     ├─ general/
│     │  ├─ test_transform.py
│     │  ├─ test_converter_exports.py
│     │  ├─ test_merge.py
│     │  └─ test_pipeline.py
│     │
│     ├─ instandard/
│     │  ├─ test_parser.py
│     │  ├─ test_assignments.py
│     │  ├─ test_tiers.py
│     │  ├─ test_catalog.py
│     │  ├─ test_converter_exports.py
│     │  └─ test_pipeline.py
│     │
│     └─ templates/
│        ├─ test_placeholders.py
│        ├─ test_bindings.py
│        ├─ test_render.py
│        └─ test_locale_audit.py
│
└─ web/
   ├─ scripts/
   │  └─ build.mjs
   │
   ├─ public/
   │  └─ data/
   │     └─ open_options/
   │        ├─ general/
   │        │  └─ open_option_rows.csv
   │        │
   │        ├─ instandard/
   │        │  ├─ catalog.json
   │        │  └─ open_option_rows.csv
   │        │
   │        └─ i18n/
   │           ├─ ko/
   │           │  └─ base_options.json
   │           └─ ja/
   │              └─ base_options.json
   │
   └─ src/
      ├─ data/
      │  ├─ generalOpenOptions.ts
      │  ├─ instandardOptions.ts
      │  └─ optionLocales.ts
      │
      ├─ domain/
      │  └─ openOptions/
      │     ├─ types.ts
      │     ├─ normalizeTemplate.ts
      │     ├─ placeholders.ts
      │     ├─ renderTemplate.ts
      │     └─ localeCatalog.ts
      │
      └─ components/
         ├─ OpenViewer.tsx
         └─ InstandardViewer.tsx
최종 데이터 관계
                    item_option_open.dat
                            │
                     공통 DAT 파서
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
     일반 개방옵션 블록              section_type=11
             │                       비규격 개방 블록
             ▼                             ▼
general/open_option_rows.csv    instandard/open_option_rows.csv
                                           │
InstandardEquip.dat ────────────────────────┘
        │
        ▼
inststandard/catalog.json


capa.dat ────────────────┐
                         ├─ locale catalog
japanese.llt section 22 ─┘
                         │
                         ├─ ko/base_options.json
                         └─ ja/base_options.json
                                  │
             ┌────────────────────┴────────────────────┐
             │                                         │
             ▼                                         ▼
general/open_option_rows.csv                instandard/catalog.json
                                            instandard/open_option_rows.csv
             │                                         │
             └────────────────────┬────────────────────┘
                                  ▼
                     공통 placeholder·렌더링
                                  │
                   ┌──────────────┴──────────────┐
                   ▼                             ▼
             OpenViewer                  InstandardViewer
하나로 합치는 부분과 분리하는 부분
하나로 합침
├─ item_option_open.dat 파서
├─ converter 규칙 정의
├─ value 분해
├─ 장비 그룹명 조인
├─ 한국어·일본어 locale catalog
├─ placeholder 분석
├─ placeholder 검증
├─ 실제 수치 렌더링
└─ 전체 빌드 명령

분리 유지
├─ 일반 GeneralOpenOptionRow 스키마
├─ 비규격 InstandardOpenOptionRow 스키마
├─ 비규격 티어·10개 roll 구조
├─ 비규격 보완 배정
├─ general/open_option_rows.csv
├─ instandard/catalog.json
└─ instandard/open_option_rows.csv

최종적으로 웹에 배포되는 핵심 파일은 다섯 개입니다.

web/public/data/open_options/
├─ general/
│  └─ open_option_rows.csv
│
├─ instandard/
│  ├─ catalog.json
│  └─ open_option_rows.csv
│
└─ i18n/
   ├─ ko/
   │  └─ base_options.json
   └─ ja/
      └─ base_options.json
      

최종 생성 순서
1. 비규격 스키마 로드
        ↓
2. InstandardEquip.dat 순수 파싱
        ↓
3. 장비군·옵션 배정·티어 수치 정규화
        ↓
4. 보완 배정 적용
        ↓
5. 중간 CSV 생성·검증
        ↓
6. catalog.json 생성
        ↓
7. section_type=11 변환기별 CSV 생성
        ↓
8. instandard/open_option_rows.csv 병합
        ↓
9. locale 및 placeholder 통합 감사
        ↓
10. 웹 데이터 전환
        ↓
11. 새 빌드 성공 확인
        ↓
12. 기존 비규격 CSV와 구형 생성 코드 삭제

최종적으로 웹이 직접 사용하는 비규격 데이터는 다음 세 종류만 남습니다.

web/public/data/
├─ instandard/catalog.json
├─ instandard/open_option_rows.csv
└─ i18n/{ko,ja}/base_options.json

현재의 instandard_equipment_tiers.csv, instandard_equipment_render_rows.csv, instandard_open_option_rows.csv는 새 빌드 전환이 끝난 뒤 모두 삭제합니다.