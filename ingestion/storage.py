"""R2 오브젝트 스토리지 헬퍼 (계획서 3·7장).

순수 함수 + 얇은 CLI. Dagster 비의존. 자격증명은 .env (커밋 금지).

사용:
    py -m ingestion.storage upload <로컬경로> <키>
    py -m ingestion.storage exists <키>
    py -m ingestion.storage ls <프리픽스>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def load_env(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def get_client():
    load_env()
    account_id = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def bucket_name() -> str:
    load_env()
    return os.environ.get("R2_BUCKET", "kbo-pipeline")


def object_exists(s3, key: str) -> bool:
    """head_object 기반 존재 확인 — already_ingested의 실체 (계획서 7장 멱등)."""
    try:
        s3.head_object(Bucket=bucket_name(), Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
            return False
        raise


def upload_file(s3, local_path: str | Path, key: str) -> None:
    s3.upload_file(str(local_path), bucket_name(), key)


def download_file(s3, key: str, local_path: str | Path) -> None:
    Path(local_path).parent.mkdir(parents=True, exist_ok=True)
    s3.download_file(bucket_name(), key, str(local_path))


def list_keys(s3, prefix: str, limit: int = 50) -> list[str]:
    resp = s3.list_objects_v2(Bucket=bucket_name(), Prefix=prefix, MaxKeys=limit)
    return [o["Key"] for o in resp.get("Contents", [])]


def main() -> None:
    s3 = get_client()
    cmd = sys.argv[1]
    if cmd == "upload":
        local, key = sys.argv[2], sys.argv[3]
        upload_file(s3, local, key)
        print(f"업로드 OK: {local} -> s3://{bucket_name()}/{key}")
    elif cmd == "exists":
        key = sys.argv[2]
        print("존재함" if object_exists(s3, key) else "없음", "-", key)
    elif cmd == "ls":
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        keys = list_keys(s3, prefix)
        print(f"'{prefix}' 아래 {len(keys)}개:")
        for k in keys:
            print(" ", k)
    else:
        print("사용법: upload <로컬> <키> | exists <키> | ls <프리픽스>")


if __name__ == "__main__":
    main()
