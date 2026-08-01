# adsense — 4블로그 애드센스 수익 프로젝트

기간: 2026-08-01 ~ 2026-08-31 (31일)
자산: 애드센스 승인 완료 계정 1개 (티스토리)
목표(사용자 설정): 월 1,000만원

## 먼저 읽을 것

- **[docs/00-현실점검.md](docs/00-현실점검.md)** — 목표 수치의 역산. 왜 31일 안에 신규 4블로그로 월 1,000만원이 불가능한지, 그리고 무엇이 가능한지.
- [docs/01-알파남-채널분석.md](docs/01-알파남-채널분석.md) — 지정 채널 조사 결과와 실제로 쓸 수 있는 것 / 없는 것
- [docs/02-31일-실행계획.md](docs/02-31일-실행계획.md) — 8월 1~31일 일자별 실행안
- [docs/03-키워드-수익구조.md](docs/03-키워드-수익구조.md) — 키워드 선정, 광고 배치, 수익 다각화
- [docs/04-계정보호-금지사항.md](docs/04-계정보호-금지사항.md) — 이것만 어겨도 프로젝트 전체가 0원이 되는 항목
- [docs/05-단기달성-대안경로.md](docs/05-단기달성-대안경로.md) — 31일 안에 월 1,000만원에 실제로 도달할 수 있는 유일한 경로들

## 도구

```bash
python3 tools/revenue_model.py                     # 목표 역산 / 시나리오 비교
python3 tools/revenue_model.py --scenario aggressive
python3 tools/keyword_score.py keywords/seed.csv   # 키워드 우선순위 스코어링
python3 tools/tracker.py init                      # 일일 실적 로그 생성
python3 tools/tracker.py report                    # run-rate 집계
```

## 현재 상태

| 항목 | 값 |
|---|---|
| 운영 블로그 | 0 / 4 |
| 누적 발행 글 | 0 |
| 예상 월 run-rate | ₩0 |
