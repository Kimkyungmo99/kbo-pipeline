# 2026-08-17 수직 슬라이스 실행 체크리스트

## 1. 설치 (5분)

```bash
cd kbo-pipeline
uv init 없이 바로:
uv venv && uv pip install -e ".[dev]"     # uv 없으면: pip install -e ".[dev]"
git init && git add -A && git commit -m "scaffold"
```

## 2. 엔드포인트 검증 (핵심, 15~30분)

config/sources.yaml 에 네이버 스포츠 비공식 게이트웨이가 이미 채워져 있다.
브라우저 DevTools 탐색 대신 아래 한 방으로 먼저 확인:

```bash
python -m ingestion.explore 2026-08-16
```

- 경기 목록 + 첫 경기 relay 응답의 키 트리가 출력되면 → 탐색 성공, 3번으로
- 403/HTML이 오면 → DevTools 플랜 B (아래) 로 전환

정상이면 샘플 저장:

```bash
python -m ingestion.explore 2026-08-16 --save
```

출력된 "첫 타석 원본"을 보고 `ingestion/parsers/portal.py` 상단의
필드 후보(`_FIELD_CANDIDATES`, inn/batter/pitcher 키)를 실제 키 이름과 맞춘다.

### 플랜 B: DevTools 수동 탐색 (게이트웨이가 막혔을 때)

1. 네이버 스포츠에서 어제(8/16) 종료 경기의 문자중계 탭 열기
2. F12 → Network → Fetch/XHR → 새로고침
3. 큰 JSON 응답 클릭 → 투구(구종/구속/결과) 배열 찾기
4. Request URL을 config/sources.yaml 의 pitch_url 에 반영
5. curl 재현: `curl -H "User-Agent: Mozilla/5.0" -H "Referer: <페이지URL>" "<URL>" | head -c 2000`

## 3. 경기 1개 → Parquet (30~60분)

```bash
python -m ingestion.run --list 2026-08-16        # gameId 복사
python -m ingestion.run <gameId> 2026-08-16
# → OK: 3XX pitches
```

0행이 나오면 parsers/portal.py 의 키 이름을 raw JSON에 맞게 수정 (이 파일만 고치면 됨).

## 4. 종료 (15분)

```bash
duckdb -c "select count(*), min(velocity), max(velocity) from 'data/bronze/dt=*/pitches.parquet'"
pytest                                            # 샘플 저장했으면 2개 통과
git add -A && git commit -m "vertical slice: one game to parquet"
```

- [ ] data/bronze/ 에 Parquet 존재
- [ ] data/raw/ 에 원본 JSON 보존
- [ ] 커밋 1개
- [ ] Daily 노트에 D1(DuckDB 검증 5쿼리) 조각 등록

## 참고: gameId 형식

`20260816` + 원정팀코드 + 홈팀코드 + `0` + `2026` (예: 20260501NCLG02026)
— 역산하지 말고 --list 로 받은 ID를 그대로 쓸 것 (가이드 함정 표).
