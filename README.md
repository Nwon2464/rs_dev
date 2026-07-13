# Red Stone 옵션 탐색기 — 개인 운영 메모

일반 장비 개방옵션과 비규격 장비 옵션을 원본 DAT에서 재생성하고,
한국어/일본어 웹 탐색기로 확인하는 프로젝트다.

## 빠른 실행

### 웹만 실행

```bash
cd web
npm run dev
```

로컬 개발 서버가 표시하는 데이터는 `web/public/data/open_options/` 아래의
생성된 파일이다.

### 웹 빌드만 확인

```bash
cd web
npm run build
```

### 원본 데이터부터 전체 재생성 후 웹 빌드

```bash
cd web
npm run build:all
```

`build:all`은 내부적으로 다음 순서로 동작한다.

```text
scripts/build_open_options.py
├─ 일반 장비 개방옵션 생성
├─ 비규격 장비 / 비규격 개방옵션 생성
├─ 한국어·일본어 옵션 템플릿 생성
├─ 일본어 장비·버킷·메타데이터 audit 및 catalog 생성
├─ canonical 옵션 태그 생성
└─ web/public/data/open_options/로 production 데이터 복사

tsc + Vite production build
```

전체 생성은 기본적으로 다음 게임 원본 경로를 사용한다.

```text
/mnt/c/game/Red Stone/Data
```

필요한 대표 원본은 다음과 같다.

- `item_option_open.dat`
- `InstandardEquip.dat`
- `capa.dat`
- `simpleGameText.dat`
- `language/japanese.llt`

Python 의존성은 `pyproject.toml`에 정의되어 있다. 현재 환경에서 별도 가상환경을
사용한다면 해당 Python이 `pydantic`, `pytest`를 포함해야 한다.

## 검증

```bash
PYTHONPATH=src python -m pytest
cd web && npm run build
cd .. && git diff --check
```

`npm run build:all`은 데이터 migration 검증과 웹 빌드를 함께 수행한다.

## 게임 패치 후 DAT / LLT 업데이트 대응

게임 패치로 원본 데이터가 바뀌면, 기존 처리 결과를 임의로 편집하지 말고
원본부터 전체 파이프라인을 다시 실행한다.

### 1. 원본 위치와 변경 범위 확인

기본 입력 경로의 파일 갱신 여부를 먼저 확인한다.

```text
/mnt/c/game/Red Stone/Data/
├─ item_option_open.dat
├─ InstandardEquip.dat
├─ capa.dat
├─ simpleGameText.dat
└─ language/japanese.llt
```

`item_option_open.dat`, `InstandardEquip.dat`, `capa.dat` 또는
`japanese.llt`가 바뀌었다면 옵션 행·수치·템플릿·일본어 catalog까지
영향을 받을 수 있다.

### 2. 전체 재생성

Python 의존성이 있는 환경에서 실행한다.

```bash
cd web
npm run build:all
```

성공하면 다음이 함께 갱신된다.

- 일반 장비 / 비규격 장비 개방옵션 행
- 비규격 장비 옵션·Tier catalog
- 한국어·일본어 base option 템플릿
- 일본어 장비 그룹·버킷·등급·변환기 catalog
- canonical 옵션 태그와 태그 근거 audit
- `web/public/data/open_options/` 배포용 복사본

### 3. 실패했을 때

파서 경계 오류, migration mismatch, 일본어 audit 실패가 나면 결과 CSV/JSON을
수동으로 맞추지 않는다. 패치로 바뀐 원본 구조 또는 의미가 기존 가정과 달라진 것이다.

다음 순서로 확인한다.

1. 오류 메시지의 DAT·section·option ID를 기록한다.
2. `data/reports/open_options/`의 기존 audit와 새 원본을 비교한다.
3. 파서 또는 converter spec의 가정을 수정하고 회귀 테스트를 추가한다.
4. 전체 재생성을 다시 실행한다.

특히 migration baseline 불일치는 무시하면 안 된다. 게임 데이터가 실제로 바뀐 것인지,
파싱/변환 로직이 깨진 것인지 분리한 뒤 baseline을 갱신한다.

### 4. 재생성 후 확인

```bash
PYTHONPATH=src python -m pytest
cd web && npm run build
cd .. && git diff --check
```

추가로 브라우저에서 다음을 확인한다.

- 일반 장비 개방옵션의 converter·등급·LV별 후보
- 비규격 옵션, 비규격 개방옵션, 티어별 옵션의 행 수와 수치
- 한국어/日本語 전환 시 옵션·장비·태그·변환기 표기
- 태그 audit의 `untagged_count` 및 새 옵션의 근거

로컬 `data/raw/` 사본을 테스트 fixture로 갱신해야 하는 패치라면,
실제 게임 원본과 동일한지 확인한 뒤 별도 변경으로 반영한다.

## 데이터 구조

정식 처리 결과는 `data/processed/open_options/`에 생성된다.

```text
data/processed/open_options/
├─ general/open_option_rows.csv
├─ instandard/
│  ├─ catalog.json
│  └─ open_option_rows.csv
├─ i18n/
│  ├─ ko/base_options.json
│  └─ ja/base_options.json
└─ catalogs/
   ├─ option_tags.json
   ├─ equipment_groups.json
   ├─ open_equipment_buckets.json
   └─ open_metadata.json
```

웹은 동일한 구조를 `web/public/data/open_options/`에서 fetch한다.

- 숫자·확률·티어·옵션 ID는 CSV/JSON 원본 처리 결과를 유지한다.
- 언어별 옵션 제목과 실제 수치는 `i18n/*/base_options.json` 템플릿으로 렌더링한다.
- 일본어 장비 그룹·일반 장비 버킷·등급·변환기 표시는 `catalogs/*.json`을 사용한다.
- 옵션 태그는 `catalogs/option_tags.json`의 `canonical_tags`를 모든 화면에서 공통으로 사용한다.

## 최종 폴더 구조

```text
rs_dev-japanese-ui/
├─ config/
│  └─ open_options/             보완 배정·값 binding 같은 pipeline 설정
├─ data/
│  ├─ raw/                      테스트·조사용 로컬 DAT 사본
│  ├─ intermediate/
│  │  └─ open_options/          빌드 중 재생성되는 converter별 중간 CSV
│  ├─ processed/
│  │  └─ open_options/          정식 생성 데이터
│  │     ├─ general/            일반 장비 개방옵션 행
│  │     ├─ instandard/         비규격 장비 catalog·개방옵션 행
│  │     ├─ i18n/               한국어·일본어 옵션 템플릿
│  │     └─ catalogs/           태그·장비명·버킷·메타데이터
│  └─ reports/
│     └─ open_options/          migration baseline, 검증, 태그 근거 audit
├─ scripts/                     전체/부분 build와 독립 audit 실행 진입점
├─ src/
│  └─ rs_dev/
│     ├─ parsers/               DAT·LLT 파서
│     ├─ models/                데이터 모델
│     └─ open_options/          일반·비규격·locale·catalog pipeline
├─ tests/                       정식 pipeline·출력·태그 회귀 테스트
├─ web/
│  ├─ src/                      React UI
│  ├─ public/data/open_options/ 웹에서 fetch하는 배포용 데이터 복사본
│  └─ scripts/build.mjs         Python 생성 → public 복사 → Vite build
└─ damage_experiment/           본 pipeline과 분리된 실험·근거 자료
```

데이터 흐름은 다음 하나만 기억하면 된다.

```text
게임 DAT / japanese.llt
        ↓
data/processed/open_options/
        ↓
web/public/data/open_options/
        ↓
React Viewer
```

`data/intermediate/`는 결과물이 아니라 빌드 과정의 확인용 산출물이고,
`data/reports/`는 UI 입력은 아니지만 검증 근거와 migration 기준이므로 유지한다.

## 옵션 태그

태그 생성 규칙은 `src/rs_dev/open_options/catalogs/option_tags.py`에 있다.

- 원본 `source_tags`는 보존한다.
- UI 필터에는 의미 기반 `canonical_tags`만 사용한다.
- 같은 그룹의 여러 태그는 OR, 서로 다른 그룹의 태그는 AND다.
- `공격력`, `주는 피해`, `받는 피해`를 구분한다.
- `마법`은 단순 단어 포함이 아니라 전투 문맥에서만 부여한다.
- 원본 `출현` 태그는 UI에서 `드롭`으로 표시한다.

각 태그가 부여된 근거는 재생성 결과인 다음 파일에서 확인한다.

```text
data/reports/open_options/catalogs/option_tags_audit.json
```

## 주요 소스 위치

```text
src/rs_dev/open_options/
├─ general/       일반 장비 개방옵션 pipeline
├─ instandard/    비규격 장비 / 개방옵션 pipeline
├─ locales/        한국어·일본어 옵션 템플릿
├─ catalogs/       태그·장비 그룹·버킷·메타데이터 catalog
└─ templates/      placeholder와 수치 템플릿 처리

web/src/
├─ main.tsx        데이터 로드와 화면 라우팅
├─ components/     일반/비규격 Viewer UI
├─ domain/         템플릿·태그 렌더링 helper
└─ i18n/           정적 UI 문구
```

## 주의

- `data/intermediate/open_options/`는 빌드 중 재생성되는 중간 산출물이다.
- `data/reports/open_options/`는 audit와 migration baseline을 포함하므로 테스트 기준으로 유지한다.
- `web/tsconfig.tsbuildinfo`는 TypeScript 캐시라 빌드 후 변경될 수 있다.
- 로컬 작업 중에는 branch, stash, commit을 임의로 조작하지 않는다.
