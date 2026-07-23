# Red Stone 장비 옵션 탐색기

일본 클라이언트의 일반 장비 개방 옵션과 비규격 장비 옵션을
한국어·일본어로 확인하는 정적 웹사이트다.

Astro가 검색엔진용 정적 HTML을 만들고, React가 검색과 필터 기능을 담당한다.

## 로컬 실행

처음 한 번만 패키지를 설치한다.

```bash
cd web
npm ci
```

개발 화면을 실행한다.

```bash
npm run dev
```

브라우저에서 `http://localhost:4321/rs_dev/`를 연다.

배포용 결과를 확인하려면 다음을 실행한다.

```bash
npm run build
npm run preview
```

## 게임 데이터 업데이트 절차

### 1. 원본 준비

이전 원본은 `before/`, 새 일본 클라이언트 원본은 `after/`에 둔다.

```text
after/
├─ item_option_open.dat
├─ InstandardEquip.dat
├─ capa.dat
├─ simpleGameText.dat
└─ language/japanese.llt
```

`before/`와 `after/`는 로컬 전용이며 Git에 올리지 않는다.

### 2. 로컬 변경 로그 작성

데이터 작업을 시작하기 전에 로컬 `CHANGELOG.md`에 날짜와 변경 내용을 추가한다.

```markdown
## 2026-09-20

### 게임 데이터 변경

- 변경된 옵션 내용을 기록한다.
```

### 3. 원본 차이 확인

프로젝트 최상위 폴더에서 실행한다.

```bash
.venv/bin/python scripts/compare_data.py
```

예상하지 못한 원본 구조 변경이 있으면 먼저 파서와 테스트를 수정한다.
생성된 CSV나 JSON을 직접 고치지 않는다.

### 4. 데이터 전체 재생성

```bash
cd web
npm run build:all
cd ..
```

이 명령은 다음 작업을 수행한다.

```text
게임 원본 파싱
→ 옵션 CSV·JSON 생성
→ 한국어·일본어 데이터 생성
→ web/public 데이터 복사
→ Astro 정적 사이트 빌드
```

### 5. 사이트 갱신일 수정

`web/src/seo/siteMetadata.json`에 CHANGELOG와 같은 날짜를 입력한다.

```json
{
  "last_data_update": "2026-09-20"
}
```

디자인이나 코드만 바뀐 경우에는 이 날짜를 바꾸지 않는다.

### 6. 검증

```bash
PYTHONPATH=src .venv/bin/python -m pytest
cd web
npm run build
cd ..
git diff --check
```

브라우저에서도 다음을 확인한다.

- 일반 장비 개방 옵션 후보와 확률
- 비규격 옵션, 개방 옵션, 티어별 수치
- 한국어·일본어 페이지 이동
- 검색, 필터, 다크·라이트 모드
- footer의 데이터 갱신일

검증이 끝나면 생성 데이터, `web/public` 데이터와
`web/src/seo/siteMetadata.json`을 함께 커밋한다.

## 배포

`main` 브랜치에 푸시하면 GitHub Actions가 `web/dist`를 만들고
GitHub Pages에 자동으로 배포한다.

`README.md`, `CHANGELOG.md`, `SEO_SSG_PLAN.md`는 로컬 운영 문서이므로
GitHub에 올리지 않는다.
