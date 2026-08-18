# kbo-pipeline

KBO 투구 단위(pitch-level) 데이터를 수집·검증·변환하는 개인 파이프라인 프로젝트 (진행 중, 1주차 완료).

- 현재: 날짜 하나로 그날 전 경기의 투구 이벤트를 수집해 Parquet으로 적재 (`python -m ingestion.run --date 2026-08-16` → 3경기 827투구)
- 검증: DuckDB 쿼리 + pytest (seq 연속성 어서션, 볼카운트 파싱 테스트)
- 다음: 소스 어댑터 인터페이스 → Dagster 오케스트레이션 → dbt 변환 레이어

## 데이터 정책

기록의 권리는 KBO에 있습니다. 비상업적 학습 목적이며, 원본 데이터를 재배포하지 않습니다 (`data/`는 커밋 제외).

## 설계 결정

- [ADR 000 — 소스 선택](docs/adr/000-source-selection.md)
