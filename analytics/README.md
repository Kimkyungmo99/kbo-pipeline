# KBO dbt 분석 레이어

DuckDB와 dbt를 사용해 `data/bronze`의 Parquet 이벤트를 분석용 테이블로 변환한다.

## 실행

```powershell
cd analytics
py -m dbt.cli.main debug --profiles-dir .
py -m dbt.cli.main run --profiles-dir .
py -m dbt.cli.main test --profiles-dir .
```

로컬 결과는 `analytics/kbo_analytics.duckdb`에 생성되며 Git에는 포함하지 않는다.

## 현재 모델

- `stg_pitch_events`: 원본의 투구 후 상태를 이용해 이벤트 직전 볼·스트라이크 상태와 경기 내 타석 번호를 계산한다. 피치클락 이벤트도 순서 계산에 포함한다.
- `int_plate_appearances`: 타석당 한 행으로 집계하고 종료 문구로 안타·아웃·볼넷·HBP 등 12개 결과를 분류한다.
- `fct_pitches`: 실제 투구당 한 행인 분석용 fact. 투구 직전 카운트, 타석 결과, 정규·시범·포스트시즌 구분 컬럼을 제공한다. 피치클락 페널티 이벤트는 제외한다.
- `dim_players`: 투수·타자 ID를 통합한 선수 차원. 최초·최종 관측일, 역할별 경기 수와 투구 수를 제공한다.
- `agg_pitch_type_count`: 시즌·경기 종류·구종·투구 전 카운트별 투구 수, 평균 구속, 볼·루킹·헛스윙·파울·인플레이 수와 비율을 제공한다. 구종 결측도 `미분류`로 보존한다.
- `agg_pitcher_season`: 시즌·경기 종류·투수별 투구 수, 평균 구속, 투구 결과, 상대 타석 결과와 삼진·볼넷·헛스윙 비율을 제공한다.
- `agg_batter_season`: 시즌·경기 종류·타자별 상대 투구 수, 스윙 결과, 안타 종류와 삼진·볼넷·헛스윙 비율을 제공한다.

종료 문구가 원본에 없는 8개 타석은 `known_incomplete_plate_appearances` seed로 관리한다. 이 목록에 없는 새 미분류 결과가 생기면 dbt 검사가 실패한다.
알려진 볼카운트 전이 위반 13건은 `known_count_transition_violations` seed로 관리하며, 새 위반과 기존 위반의 소실을 모두 검사한다.
집계 모델은 grain 중복 검사와 fact 투구 수 합계 대조를 통과해야 한다.
선수별 집계의 타석 지표는 `is_terminal_pitch`인 행에서만 계산해 같은 타석 결과가 투구 수만큼 중복되지 않게 한다.
