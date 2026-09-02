"""로컬 data/ 전체를 R2로 동기화 — 이미 있는 객체는 스킵 (멱등).

사용: py scripts_r2_sync.py
"""
from pathlib import Path

from ingestion import storage

s3 = storage.get_client()

uploaded = skipped = 0
local_raw = local_bronze = 0
for local in sorted(Path("data").rglob("*")):
    if not local.is_file():
        continue
    key = local.as_posix().removeprefix("data/")
    if key.startswith("raw/"):
        local_raw += 1
    elif key.startswith("bronze/"):
        local_bronze += 1
    else:
        continue  # 예상 밖 경로는 건드리지 않음
    if storage.object_exists(s3, key):
        skipped += 1
    else:
        storage.upload_file(s3, local, key)
        uploaded += 1
        print(f"업로드: {key}")

print(f"\n동기화 완료: 업로드 {uploaded} / 스킵(이미 존재) {skipped}")

print("\n== 개수 대조 (로컬 vs R2) ==")
r2_raw = len(storage.list_keys(s3, "raw/", limit=1000))
r2_bronze = len(storage.list_keys(s3, "bronze/", limit=1000))
print(f"raw:    로컬 {local_raw} / R2 {r2_raw} {'OK' if local_raw == r2_raw else '← 불일치!'}")
print(f"bronze: 로컬 {local_bronze} / R2 {r2_bronze} {'OK' if local_bronze == r2_bronze else '← 불일치!'}")
