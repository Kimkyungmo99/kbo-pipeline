# 팀 분석 결과물

`team_season_report.py`는 DuckDB의 팀 시즌 마트를 읽어 2024·2025 정규시즌 비교 자료를 만든다.

```powershell
py analysis/team_season_report.py
```

생성 파일은 `analysis/outputs/`에 저장된다.

- CSV: 재사용 가능한 팀별 지표
- SVG: 2025년 핵심 지표 순위 차트
- SVG: 승률과 경기당 득실차·타격 삼진율의 관계 차트
- Markdown: 주요 결과와 해석 범위

## 오프라인 대시보드

```powershell
py analysis/build_dashboard.py
```

생성된 `analysis/outputs/kbo_team_dashboard.html`을 브라우저로 열면 된다. 차트 라이브러리와 20개 팀-시즌 데이터가 파일 안에 들어 있어 네트워크 연결이 필요 없다. 로컬 DuckDB가 갱신된 뒤 같은 명령으로 다시 생성한다. 일일 수집이 이 화면을 자동 갱신하지는 않는다.

- 2024·2025 정규시즌 선택, 팀 강조, 8개 지표 순위, 7개 지표와 승률의 관계
- 정렬 가능한 10팀 비교표와 현재 시즌 CSV 저장
- 승률은 무승부 제외, 리그 구속은 측정 투구 수로 가중
- 2025년 현재 수록 범위는 714경기로 표시하며 전체 시즌 기록과 구분

`node analysis/check_dashboard.cjs`는 DOM 모의 환경에서 필터·정렬·카드 계산·CSV 로직을 확인한다. 이 검사는 Chart.js 렌더링과 실제 브라우저 배치를 검증하지 않는다. 실제 화면 배치 검토는 후속 확인이 필요하다.

Chart.js 4.5.1은 `analysis/vendor/`에 MIT 라이선스와 함께 보관했다. 패키지 원본: `https://cdn.jsdelivr.net/npm/chart.js@4.5.1/dist/chart.umd.min.js`.
