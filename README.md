# kbo-pipeline

KBO 투구 단위(pitch-level) 데이터를 수집·검증·변환하는 개인 파이프라인 프로젝트.

- 현재: 2024 전체, 2025년 3~10월, 2026년 일부를 포함한 1,585경기 483,396개 이벤트가 raw(JSON)·bronze(Parquet)로 로컬 + Cloudflare R2에 보관
- 수집: 멱등 3단계 폴백(로컬 → R2 → 소스), 순차 백필 드라이버(요청 간 1초, 동시 요청 없음), Dagster 일 파티션 asset 2개
- 검증: seq 연속성 · 새니티 · **볼카운트 전이(도메인 규칙)** · 완전성(bronze 경기 수 = 목록 API RESULT 수) · dbt 데이터 검사 · pytest
- 경기 종류: gameId 접두로 분류(`game_type` 컬럼) — 정규·포스트시즌 수집, 올스타 제외
- 분석: dbt로 투구 fact, 타석 결과, 선수 차원, 구종·카운트별 지표 마트 생성
- 자동화: 매일 오전 8시(KST) 전날 완료 경기를 수집하고 검증하며, 실패 시 GitHub 이슈 생성

## 실행

```
py -m ingestion.run --list 2024-10-23          # 그날 경기 목록·종류·수집 여부
py -m ingestion.run --date 2024-10-23          # 그날 전 경기 수집 → bronze
py scripts_backfill.py 2025-04-01 2025-04-30   # 월 단위 순차 백필 (멱등)
py scripts_reparse.py                           # 파서 변경 시 raw → bronze 전체 재생성 (소스 요청 0회)
py check_transitions.py                         # 볼카운트 전이 검증
py check_completeness.py 2025-04-01 2025-04-30  # 수집 완전성 (목록 API 대조)
py probe_game.py <game_id> <date> <seq> ...     # 위반 seq의 raw 원본 열람
py scripts_daily.py 2026-09-20                  # 일일 자동화와 같은 경로를 수동 실행
```

## 데이터 정책

기록의 권리는 KBO에 있습니다. 비상업적 학습 목적이며, 원본 데이터를 재배포하지 않습니다 (`data/`는 커밋 제외, R2 버킷 비공개).

## 설계 결정

- [ADR 000 — 소스 선택](docs/adr/000-source-selection.md)
- [ADR 002 — 볼카운트 전이 검증: 도메인 규칙을 품질 게이트로](docs/adr/002-count-transition-validation.md) — 파서의 시간 역순 버그, 소스 이상 4종 분류, 그리고 **검증이 통과하는데도 새고 있던 파서의 데이터 손실**까지 잡았다 (개정 1)
- [ADR 003 — 경기 종류는 gameId 접두로 분류](docs/adr/003-game-type-classification.md) — 포스트시즌 수집·올스타 제외, 미확인 접두는 조용히 빠지지 않게
