# 0단계 출력 회귀 기준

`baselines/output_baseline.json`은 리팩터링 직전 커밋
`682594c104f8989bd164d95aeec4cca9e71cbb34`의 추적 중인 CSV·JSON·HTML
출력을 기록한다.

다음 명령으로 기준 파일의 바이트 단위 동일성, CSV 행·열 수, 주요 데이터
건수를 함께 검사한다.

```bash
python3 -m unittest discover -s tests -v
```

의도한 출력 변경이 아닌 경우 baseline을 갱신하지 않는다. 출력 변경을 승인한
뒤에만 현재 파일의 SHA-256·크기·건수를 다시 측정해 manifest를 수정한다.
