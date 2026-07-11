# 근거 데이터 형식

`data/evidence/`의 각 행 또는 문서는 하나의 관찰 가능한 사실만 기록한다.
파생 계산값과 가설은 이 폴더에 넣지 않는다.

## 필수 필드

| 필드 | 설명 |
|---|---|
| `evidence_id` | 근거를 식별하는 저장소 내 고유 ID |
| `evidence_level` | `confirmed`, `inferred`, `unknown` 중 하나 |
| `subject_type` | 예: `capa`, `item`, `skill`, `memory`, `experiment` |
| `subject_id` | Capa ID 등 대상 식별자. 없는 경우 `none` |
| `source_path` | 읽기 전용 원본 또는 관찰 기록의 경로 |
| `source_version` | 클라이언트·데이터·덤프 버전 또는 `unknown` |
| `source_locator` | 오프셋, 레코드 번호, 주소, 행 번호 등 재현 위치 |
| `raw_value` | 원문 값 또는 원문에서 추출한 최소 단위 값 |
| `claim` | 이 근거만으로 말할 수 있는 제한된 주장 |
| `collected_at` | `YYYY-MM-DD` 형식의 관찰일 |

## 조건부 필드

`inferred` 행에는 다음 필드를 추가한다.

| 필드 | 설명 |
|---|---|
| `basis_evidence_ids` | 추론에 사용한 `confirmed` 근거 ID 목록 |
| `alternatives` | 가능한 다른 해석 또는 반증 조건 |

`unknown` 행에는 다음 필드를 추가한다.

| 필드 | 설명 |
|---|---|
| `missing_evidence` | 판정에 필요한 직접 근거 |

## 기록 규칙

- `confirmed`는 원문 사실만 기록하며 계산 순서·인과 관계를 덧붙이지 않는다.
- `inferred`는 반드시 근거 ID와 대안 해석을 연결한다.
- `unknown`은 빈 값이 아니라 무엇이 부족한지 기록한다.
- 원본 파일 전체나 개인정보는 복사하지 않고, 재현에 필요한 위치와 최소 인용만 보관한다.
