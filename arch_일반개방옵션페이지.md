전환 계획: 총 8단계
1. 기존 결과의 기준값만 기록

기존 CSV 자체는 최종적으로 모두 삭제하되, 삭제 전에 다음 정보만 JSON으로 남깁니다.

migration_baseline.json
├─ 변환기별 행 수
├─ 변환기별 option_id 개수
├─ 고유 option_id 목록
├─ 장비 그룹별 행 수
├─ grade_code별 행 수
├─ open_slot별 확률 합계
└─ option_id/value/probability 조합 해시

이유: 새 파이프라인에서 행이 빠지거나 수치가 달라졌는지 확인할 최소한의 비교 기준이 필요하기 때문입니다. 기존 CSV를 보존할 필요는 없습니다.

현재 코드에는 일반·개량·모조·불타는 외에 협회 변환기도 정의되어 있으므로, 이번 개편에서 제외할지 별도 처리할지도 이 단계에서 확정해야 합니다.

2. 공통 스키마부터 정의

먼저 변환기별 CSV가 반드시 따라야 할 모델을 만듭니다.

OpenOptionRow
├─ converter_type
├─ equipment_bucket
├─ group_ids
├─ group_names
├─ grade_code
├─ section_group
├─ open_slot
├─ candidate_index
├─ option_id
├─ value_0
├─ value_1
├─ probability
├─ probability_source
├─ tier
├─ source_block_index
└─ source_file_offset

제외되는 필드:

제외
├─ option_name
├─ option_display
├─ 한국어 문구
└─ 일본어 문구

이유: 모든 변환기 파서가 같은 출력 계약을 따라야 나중에 CSV 병합이 단순 결합이 됩니다.

3. 원본 DAT 파서를 표시 로직과 분리
item_option_open.dat
        │
        ▼
parse_item_option_open()
├─ 블록 경계 파싱
├─ section_type
├─ section_group
├─ group_ids
├─ row_index
├─ option_id
├─ packed_value
├─ float_a
├─ float_b
└─ tier

별도로:

simpleGameText.dat
        │
        ▼
parse_item_groups()
└─ group_id → 장비 그룹명

이 단계에서는 다음을 하지 않습니다.

하지 않음
├─ capa.dat 조인
├─ 일본어 조인
├─ 옵션 문구 생성
├─ [n] 변환
└─ 실제 효과 렌더링

이유: 바이너리 해석과 사용자 표시 로직이 섞이면 옵션 표시를 수정할 때 DAT 파싱까지 영향을 받기 때문입니다.

4. 변환기별 어댑터 작성

파싱한 블록을 변환기별 규칙으로 공통 스키마에 넣습니다.

파싱된 OpenOptionBlock
        │
        ├─ NormalConverterAdapter
        ├─ ImprovedConverterAdapter
        ├─ FakeConverterAdapter
        └─ BurningConverterAdapter
                │
                ▼
            OpenOptionRow

각 어댑터가 담당하는 것:

├─ 해당 section_group 선택
├─ 허용 grade_code 선택
├─ float_a / float_b 중 확률 필드 선택
├─ packed_value → value_0/value_1
├─ open_slot 계산
├─ group_ids → group_names 조인
└─ converter_type 부여

이유: 새 변환기가 추가될 때 해당 어댑터만 추가하고 나머지 처리에는 손대지 않도록 하기 위해서입니다.

5. 변환기별 CSV 생성 및 검증
data/intermediate/open_options/
├─ normal_open_options.csv
├─ improved_open_options.csv
├─ fake_open_options.csv
└─ burning_open_options.csv

네 CSV는 모두 같은 컬럼을 가집니다.

converter_type,equipment_bucket,group_ids,group_names,grade_code,section_group,open_slot,candidate_index,option_id,value_0,value_1,probability,probability_source,tier,source_block_index,source_file_offset

CSV를 쓰기 전에 검증합니다.

검증
├─ Pydantic 스키마 검증
├─ 변환기 타입 검증
├─ option_id 범위
├─ probability 범위
├─ open_slot 범위
├─ group_id 존재 여부
├─ 중복 행
└─ 슬롯별 확률 합계

이유: 통합한 다음 오류를 찾는 것보다 변환기별 단계에서 문제를 찾는 것이 훨씬 쉽기 때문입니다.

6. 변환기 CSV 병합과 언어 카탈로그 생성
변환기 데이터 병합
normal_open_options.csv
improved_open_options.csv
fake_open_options.csv
burning_open_options.csv
        │
        ▼
merge_open_option_rows()
        │
        ▼
data/processed/open_options/open_option_rows.csv
한국어 카탈로그
capa.dat
├─ short_text 우선
├─ description fallback
└─ name은 표시용에서 제외
        │
        ▼
data/processed/i18n/ko/base_options.json
{
  "260": "CP +[1]",
  "725": "최대 HP +[0]"
}
일본어 카탈로그
japanese.llt
└─ section 22
   ├─ text_id → option_id
   └─ text → template
        │
        ▼
data/processed/i18n/ja/base_options.json
{
  "260": "CP [+1]",
  "725": "最大HP +[0]"
}

이유: 변환기 데이터와 언어 데이터는 변경 원인이 서로 다르므로 독립적으로 생성해야 합니다.

7. 통합 감사와 프론트엔드 전환
통합 감사
open_option_rows.csv의 option_id
        │
        ├─ ko/base_options.json 존재 여부
        ├─ ja/base_options.json 존재 여부
        ├─ placeholder 번호 검사
        ├─ value_0/value_1 대응 검사
        └─ 렌더링 후 미치환 문자열 검사
                │
                ▼
data/reports/open_options/audit.json
프론트엔드
open_option_rows.csv
        +
선택 locale의 base_options.json
        │
        ▼
option_id로 template 조회
        │
        ▼
공통 normalizeTemplate()
        │
        ▼
공통 placeholder 분석·검증
        │
        ├─ 제목: [0]/[1] → [n]
        └─ 효과: value_0/value_1 삽입
        │
        ▼
OpenViewer

이 단계에서 제거할 기존 의존성:

제거
├─ general-open에서 instandard optionMap 조회
├─ CSV option_name fallback
├─ CSV option_display를 최종 표시값으로 사용
└─ 한국어와 일본어의 별도 렌더링 분기

이유: 새 데이터 구조를 만들고도 UI가 기존 CSV 필드를 참조하면 구조 변경의 의미가 없어지기 때문입니다.

8. 빌드 전환 후 기존 CSV 전체 삭제

현재 build:all은 기존 스크립트를 실행하고 equipment_converter_type_options.csv, instandard_open_option_rows.csv 등을 웹 디렉터리로 복사하도록 되어 있습니다. 따라서 CSV를 먼저 삭제하면 현재 빌드가 바로 깨집니다.

최종적으로 web/scripts/build.mjs를 다음 흐름으로 바꿉니다.

npm run build:all
        │
        ▼
python scripts/build_open_options.py
├─ DAT 파싱
├─ 변환기별 CSV 생성
├─ 변환기별 검증
├─ 최종 CSV 병합
├─ 한국어 JSON 생성
├─ 일본어 JSON 생성
└─ 통합 감사
        │
        ▼
웹 public으로 최종 파일만 복사
├─ open_option_rows.csv
├─ ko/base_options.json
└─ ja/base_options.json
        │
        ▼
npm run build

새 빌드가 성공한 다음 삭제합니다.

삭제 대상
├─ 기존 open-option 관련 data/processed/*.csv
├─ 기존 web/public/data의 open-option CSV 복사본
├─ equipment_converter_type_options.csv
├─ instandard_open_option_rows.csv의 general-open 의존
├─ 기존 option_name/option_display 생성 로직
└─ 사용되지 않는 기존 export 스크립트

instandard_open_option_rows.csv가 다른 화면에서도 사용 중이라면 그 사용처를 먼저 분리한 뒤 삭제해야 합니다.

최종 폴더 구조 (비규격 전반적인 처리도 포함되어있음)
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

최종 생성 흐름
1. 공통 스키마 로드
        ↓
2. item_option_open.dat 파싱
        ↓
3. simpleGameText.dat 파싱
        ↓
4. 변환기별 OpenOptionRow 생성
        ↓
5. 변환기별 CSV 출력·검증
        ↓
6. open_option_rows.csv 병합
        ↓
7. ko/base_options.json 생성
        ↓
8. ja/base_options.json 생성
        ↓
9. option_id·placeholder 통합 감사
        ↓
10. 웹 public으로 최종 파일 복사
        ↓
11. React 빌드

핵심은 기존 CSV를 먼저 지우는 것이 아니라, 새 파이프라인으로 빌드 경로를 전환한 뒤 기존 CSV를 한 번에 삭제하는 것입니다.
