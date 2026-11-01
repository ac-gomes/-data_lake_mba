import argparse
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

FOLDERS = (
    "transient/",
    "transient/clientes/",
    "transient/pedidos/",
    "transient/produtos/",
    "bronze/",
    "bronze/clientes/",
    "bronze/pedidos/",
    "bronze/produtos/",
    "silver/",
    "silver/fato_vendas/",
    "gold/",
    "gold/analises_vendas/",
    "quarantine/",
    "logs/",
)


def client():
    return boto3.client(
        "s3",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def ensure_environment(bucket):
    s3 = client()
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"Bucket preservado: {bucket}")
    except ClientError as error:
        code = error.response.get("Error", {}).get("Code")
        if code not in ("404", "NoSuchBucket", "NotFound"):
            raise
        params = {"Bucket": bucket}
        if os.environ["AWS_REGION"] != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": os.environ["AWS_REGION"]}
        s3.create_bucket(**params)
        print(f"Bucket criado: {bucket}")

    for folder in FOLDERS:
        response = s3.list_objects_v2(Bucket=bucket, Prefix=folder, MaxKeys=1)
        if response.get("KeyCount", 0):
            print(f"Pasta preservada: {folder}")
            continue
        s3.put_object(Bucket=bucket, Key=folder)
        print(f"Pasta criada: {folder}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    args = parser.parse_args()
    ensure_environment(args.bucket)


if __name__ == "__main__":
    main()
