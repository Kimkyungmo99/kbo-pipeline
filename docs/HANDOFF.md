# KBO 투구 데이터 파이프라인 — 인수인계 문서

작성: 2026-09-15 · 대상: 이 프로젝트를 이어받는 AI 어시스턴트(및 미래의 나)
이 문서 하나로 "지금 어디까지 왔고, 무엇을 어떻게 하며, 무엇을 조심해야 하는지"를 이어받을 수 있어야 한다.

---

## 0. 한 문단 요약

김경모(데이터 분석가/애널리틱스 엔지니어 이직 포트폴리오)가 만드는 **KBO 투구 단위 데이터 파이프라인**. 네이버 스포츠 비공식 API에서 경기별 문자중계 JSON을 수집해 raw(JSON) → bronze(Parquet)로 적재하고, 도메인 규칙 기반 검증을 거친다. 최종 목표는 "매일 오전 8시 어제 경기가 자동으로 마트 테이블에 반영되고 실패 시 알림" + 표본 크기를 고려한 지표 레이어(dbt). 현재 **2024 시즌 전체 + 2025년 3~10월 백필 완료, 1,585경기 483,396행**. dbt의 투구 직전 상태·타석 결과·`fct_pitches`까지 완료했고, 다음은 분석 지표와 차원 모델이다.

## 1. 작업 방식 (매일의 루틴)

- 사용자는 아침에 "X요일 아침이야"라고 온다 → 어시스턴트는 **그날 30분 조각**(주말은 더 긴 블록)을 PowerShell 명령 묶음으로 제시한다.
- 사용자가 실행하고 **출력을 그대로 붙여넣으면** 어시스턴트가 판독·해석하고, 필요하면 코드를 고치고, 하루 기록을 남긴다.
- 기록 두 곳: ① 옵시디언 vault `외부/개인프로젝트/YYYY-MM-DD 작업기록.md`(그날 무엇을 했고 내일 무엇을 할지, 교훈), ② 프로젝트 진행상황 문서(세션 간 인수인계용 요약).
- 코드는 어시스턴트가 **파일 전체 내용**을 주면 사용자가 로컬 파일에 저장한다(부분 diff보다 전체 파일이 실수가 적다). 커밋은 코드 변경이 있을 때만.
- 톤: 결과를 먼저 해석해주고, 예측이 빗나가면 정직하게 말한다. 추측으로 코드를 쓰지 않고 실측(probe)으로 확정한다.

## 2. 환경

- OS: Windows 11, PowerShell. Python 3.14 (`py` 런처, `py -m pip install …`). 주요 패키지: httpx, polars, pyyaml, boto3, dagster, pytest.
- 작업 폴더: `C:\Users\rud15\Desktop\kbo\kbo-pipeline` (git, GitHub `Kimkyungmo99/kbo-pipeline` public, main).
- vault: `C:\Users\rud15\OneDrive\Obsidian Vault\외부\개인프로젝트\`.
- 스토리지: Cloudflare R2 비공개 버킷 `kbo-pipeline`, 자격증명은 `.env`(**절대 커밋·채팅 붙여넣기 금지**, .gitignore 등재).
- `data/`(raw·bronze)는 **절대 커밋 금지** — KBO 기록 재배포 금지 원칙. R2가 원본 보관소.
- Windows 함정: 파일 IO는 항상 `encoding="utf-8"`. 출력을 파이프(`| Select-Object`)로 넘기면 cp949로 인코딩되므로 print에 em dash(—) 같은 비cp949 문자 금지.

## 3. 소스와 규칙 (실측으로 확정된 것들)

- 목록: `https://api-gw.sports.naver.com/schedule/games?upperCategoryId=kbaseball&fromDate={d}&toDate={d}` → `result.games[]`. 중계: `/schedule/games/{gameId}/relay?inning={n}` (1~12 병합). User-Agent만 필요.
- **수집 예의**: 요청 간 1초 딜레이, **동시 요청 금지**(백필·probe는 순차로만), 5xx·네트워크만 1s→2s→4s 백오프 3회, 4xx 즉시 실패.
- 수집 대상 = `categoryId=="kbo" AND statusCode=="RESULT" AND game_type ∈ 허용 종류`.
- **gameId 앞 4자리 = 경기 종류 코드** (MMDD·팀코드·경기번호·시즌은 그대로):
  날짜(YYYY)=regular / 3333=semi_po / 4444=wildcard / 5555=po / 6666=tiebreaker(순위결정전) / 7777=ks / 9999=allstar(제외).
  **시범경기는 형식이 정규와 완전히 같아서** 시즌 개막일 이전이면 exhibition (`SEASON_OPENING`: 2024-03-23 / 2025-03-22 / 2026-03-28). 미등록 접두·미등록 시즌은 unknown → 제외 + 경고. **새 시즌엔 개막일을 `ingestion/gametype.py`에 등록해야 한다.**
- relay는 최신순(`no` 내림차순)으로 오므로 파서에서 오름차순 정렬.
- `currentGameState`는 **투구 직후** 상태 (삼진 순간 strike=3, 볼넷 순간 ball=4). "직전 상태" 변환은 dbt staging 몫.
- HBP는 pitchResult='B'로 기록됨 → 타석 결과는 타석 종료 텍스트("OOO : 몸에 맞는 볼")로 판정해야 한다.
- 더블헤더: 경기번호 자리 1/2 (예 `20240421KTLT12024`), 하루 최대 8경기.
- 서스펜디드 게임(2024 KS 1차전): gameId MMDD는 편성일, 목록·bronze `dt`는 완료일.
- **2025 피치클락 페널티**: 소스가 "1구 피치클락 투수위반 볼"처럼 구 번호를 소비하는 **텍스트 옵션**(pitchNum·pitchResult 없음)으로 기록 → 파서가 `event_type` = pitch_clock_ball/strike 이벤트 행으로 보존(투구로 위장하지 않음, result·pitch_type 비움). 2024는 경고만.

### 알려진 소스 이상 4종 (전이 검증이 잡음)
1. 투구 누락(pitchNum 1,2,5,6처럼 결손 → 카운트 점프) — 수정 불가, 감지·기록
2. 동일 투구 중복(같은 번호·같은 내용) — 파서가 제거
3. 타석 합침(두 타석이 relay 하나에, pitchNum 1부터 재시작) — 파서가 보존 (dedup 규칙: **번호+내용+타자가 모두 같을 때만 중복, 번호 역행 시 새 타석**)
4. 카운트 점프 단독 = 1의 표면 증상

## 4. 파일 지도

- `ingestion/base.py` GameRef·GameSource 인터페이스(Dagster 비의존) / `ingestion/portal.py` 네이버 어댑터(`is_target`) / `ingestion/parsers/portal.py` 파서(순수 함수, dedup·pitch_clock_event) / `ingestion/gametype.py` 종류 분류(접두 사전·개막일) / `ingestion/run.py` CLI + `load_or_fetch_raw`(로컬→R2→소스 3단계 멱등 폴백) + `report_skipped` / `ingestion/storage.py` R2(boto3, 타임아웃 10s/60s, `count_keys` 페이지네이션, CLI upload/exists/ls/rm)
- `dagster_project/definitions.py` 일 파티션 asset 2개 (raw_pitch_events → bronze_pitches). 이 파일엔 `from __future__ import annotations` 금지.
- `scripts_backfill.py <시작일> <종료일>` 순차 백필(멱등, 하루 실패해도 계속) / `scripts_reparse.py` raw→bronze 전체 재생성(소스 요청 0회, ~2분) / `scripts_r2_sync.py` 로컬↔R2 동기화+개수 대조
- 검증: `check_transitions.py [--all]`(볼카운트 전이, 시즌별 요약) / `check_completeness.py <시작> <종료>`(bronze 경기 수 = 목록 RESULT 수) / `check_sanity.py` / `check_d1.py` / `tests/` pytest 33개
- 조사: `probe_game.py <game_id> <date> <seq>…`(위반 seq의 raw 원본 열람) / `probe_list.py <date>`(목록 객체 필드 덤프) / `probe_text.py <키워드> [dt접두]`(raw 텍스트 옵션 검색)
- 문서: `README.md`, `docs/adr/000`(소스 선택), `002`(전이 검증, 개정 1 포함), `003`(game_type). vault: 일일 작업기록, `면접 대비 - 파이프라인 설계 문답.md`(Q1~Q8).
- bronze 스키마(행 = 이벤트): game_id, game_type, event_type, pitch_seq_in_game(이벤트 포함 순번), inning, is_top, pitcher_id, batter_id, balls, strikes, outs, base1~3, score_home/away, pitch_type, velocity, result, text, following_text. `following_text`는 직후의 타석 결과·주자 상황 문구다. 파티션 `data/bronze/dt=YYYY-MM-DD/pitches.parquet`. raw는 `data/raw/source=portal/dt=…/game_{id}.json`.

## 5. 명령 치트시트 (완료된 마지막 백필 재검증)

```powershell
cd $HOME\Desktop\kbo\kbo-pipeline
py scripts_backfill.py 2025-10-01 2025-10-31     # ~30분, 켜두고 다른 요청 없이
py check_completeness.py 2025-10-01 2025-10-31   # 날짜당 1요청
py check_transitions.py                           # 로컬만
# 코드 변경 시만:
git add -A; git commit -m "..."; git push
```

파서/분류 규칙을 바꿨을 때: `py -m pytest -q` → `py scripts_reparse.py` → `py check_transitions.py` → 커밋.
백필이 R2 업로드에서 멈추면 Ctrl+C → 같은 명령 재실행(멱등) → `py scripts_r2_sync.py`로 구멍 메우기.

## 6. 출력 판독 기준 (정상값)

- 백필: 날짜별 `N경기 M투구`, 경기당 250~350투구, 0경기일은 월요일·우천·브레이크. **`제외:` 줄이 뜨면** 그 gameId를 보라 — `(allstar)`는 정상, `(unknown)`이면 새 접두/새 시즌 → gametype.py 등록.
- 완전성: 전 날짜 `bronze N / 목록 RESULT N` 일치. 불일치 시 `py -m ingestion.run --date <날짜>` 재실행(멱등).
- 전이 검증: **불법 전이 13건이 기준선**(2024 10건 + 2025 2건 + 2026 1건; 2025의 2건은 몸에 맞는 볼 직전 원본 카운트 특이 기록). dbt에서 새 위반과 기존 위반의 소실을 모두 검사한다.
- 기준선 13건 목록: 20240404LTHH(150·155·212), 20240411WOSK(163), 20240504OBLG(162·213), 20240724WOOB(123·217·229·285), 20250709SSNC(54), 20250902LTLG(2), 20260814OBHT(5).

## 7. 현재 상태 (2026-09-17)

| 시즌 | exhibition | regular | tiebreaker | wildcard | semi_po | po | ks |
|---|---|---|---|---|---|---|---|
| 2024 | 46 | 720 | 1 | 2 | 5 | 4 | 5 |
| 2025 | 42 | 714 | | 2 | 4 | 5 | 5 |
| 2026 | | 30 (8월 일부) | | | | | |

최근 커밋: 17a1230(R2 카운트 페이지네이션) ← 997fc2a·76163f5(exhibition, R2 타임아웃) ← d76f1ba(피치클락 event_type) ← 123a165(game_type) ← a30b1d7(dedup 수정) ← 0c95c04(올스타 제외).

## 8. 남은 계획

1. **2025-07 완료** — 100경기 29,865행. 7/12 올스타 `99990712EAWE02025 (allstar)` 제외 확인. 21개 경기일 완전성 일치. 7/9 원본 특이 기록 1건 발견.
2. **2025-08 완료** — 127경기 38,860행. 27개 경기일 완전성 일치, 전이 위반은 기존 11건 유지.
3. **2025-09 완료** — 87경기 26,367행. 27개 경기일 완전성 일치. 9/2 원본 카운트 특이 기록 1건 추가.
4. **2025-10 완료** — 23경기 6,915행. 정규 7·와일드카드 2·준PO 4·PO 5·KS 5경기. 기존 접두로 모두 정상 분류, 20개 경기일 완전성 일치, 신규 전이 위반 0건.
5. 다음은 **dbt 분석 모델 구축** — staging에서 투구 직전 상태로 shift하고 HBP 종료 텍스트 판정부터 시작.
   - 2026-09-18: `analytics/` dbt-duckdb 프로젝트와 `stg_pitch_events` 완료. 483,396행·1,585경기·124,367타석, dbt test 7개 통과.
   - 같은 날 `following_text`를 bronze에 추가하고 전체 raw 재파싱. 대타 교체를 같은 타석으로 합쳐 124,340타석 확정. `int_plate_appearances`에서 124,332건 분류, HBP 1,753건 식별. 원본상 미완료 8건은 seed 예외로 관리. dbt build 16개 항목 통과.
6. **`fct_pitches` 완료** — 실제 투구 483,164행. 피치클락 이벤트 232행 제외, 경기 종류 필터와 타석 결과 연결. 알려진 전이 위반 13건을 seed로 이식하고 dbt build 31개 항목 통과.
7. 그 다음: GitHub Actions 일일 스케줄(오전 8시) + 실패 알림, 마트 테이블. 새 시즌마다 `SEASON_OPENING` 등록.
8. 문서 후속: ADR 002 개정 2(시즌 간 규정 변화가 검증 빈도에 나타난 사례), ADR 003에 exhibition·SEASON_OPENING 보강, 면접 문답 Q9(시즌별 변화율 조기 경보)·Q10(규모가 커져야 드러나는 운영 결함 — 1,009번째 파일).

## 9. 함정 목록 (한 번씩 다 겪은 것)

- 플레이스홀더(`<gameId>`)를 그대로 실행하는 실수 → 명령엔 실제 값을 넣어 준다.
- 파서 규칙을 조사 도구에 복제하면 파서 수정 때 어긋난다 → 도구는 파서 함수를 호출한다.
- "검증 통과 = 데이터 온전" 아님. 삭제된 타석은 위반을 만들지 않는다. 위반이 나오면 raw까지 내려간다(probe_game).
- 집계는 항상 시즌 축을 넣는다(시즌 없는 집계값을 시즌값으로 오독한 적 있음).
- 접두·개막일은 추측으로 넣지 않는다(7777을 "미등록 예시"로 썼는데 실제 KS 코드였음).
- R2: 업로드 무한 대기(타임아웃으로 해결), 목록 1,000개 상한(페이지네이션으로 해결).
- 로컬 raw가 있으면 폴백 1단계에서 그냥 쓰고 R2에 안 올린다 → 중단 후 재개했으면 r2_sync.

## 10. 면접 서사 (포트폴리오 핵심)

"노트북 셀 크롤러였던 걸 멱등 수집·원본 보존·오케스트레이터 비의존·도메인 규칙 검증을 갖춘 파이프라인으로 다시 만들었다." 근거 사건들: 전이 검증이 파서의 시간 역순 버그를 잡음(Q5) → 표본이 늘자 결론을 갱신(Q6) → 검증이 통과하는데도 새던 dedup 손실을 raw 조사로 발견·재파싱 복구(Q7) → 포스트시즌 요구에 소스 식별자 체계를 읽어 설계를 단순화, 두 번의 정정(Q8) → 2024에 기각한 피치클락 가설이 2025 규정에서 참이 됨, 시즌별 변화율이 조기 경보(Q9 후보).
