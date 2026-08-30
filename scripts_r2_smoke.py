"""R2 스모크 테스트: 파일 1개 업로드 → 존재 확인 → 다운로드 비교.

사전 준비: 프로젝트 루트에 .env 파일 (절대 커밋 금지 — .gitignore에 포함됨)
    R2_ACCOUNT_ID=계정ID
    R2_ACCESS_KEY_ID=액세스키
    R2_SECRET_ACCESS_KEY=시크릿키
    R2_BUCKET=kbo-pipeline

실행: py scripts_r2_smoke.py
"""
import os
from pathlib import Path

import boto3

# .env 로드 (python-dotenv 없이 간단히)
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

account_id = os.environ["R2_ACCOUNT_ID"]
bucket = os.environ.get("R2_BUCKET", "kbo-pipeline")

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
    aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
    aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
    region_name="auto",
)

key = "smoke/hello.txt"
body = "kbo-pipeline r2 smoke test"

s3.put_object(Bucket=bucket, Key=key, Body=body.encode())
print(f"1. 업로드 OK: s3://{bucket}/{key}")

s3.head_object(Bucket=bucket, Key=key)
print("2. 존재 확인 OK (head_object) — already_ingested의 원리")

got = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode()
assert got == body
print("3. 다운로드·내용 일치 OK")

s3.delete_object(Bucket=bucket, Key=key)
print("4. 정리 OK — R2 연동 준비 완료!")
