# rs_dev

## 설치

```bash
python3 -m pip install "pydantic>=2,<3" "pytest>=8,<9"
cd web && npm install
```

## 데이터 생성·검증·웹 빌드

```bash
cd web && npm run build:all
```

최종 웹 산출물은 `web/dist/`입니다.

## 테스트

```bash
PYTHONPATH=src:scripts python3 -m pytest -q
cd web && npm run build
```
