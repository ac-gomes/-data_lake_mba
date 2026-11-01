import argparse
import os
import re

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

ENTITIES = {
    "clientes": "clientes.json",
    "pedidos": "pedidos.csv",
    "produtos": "produtos.csv",
}


def client():
    return boto3.client(
        "s3",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def migrate_raw_to_bronze(bucket, s3_client=None):
    s3 = s3_client or client()
    copied = 0
    skipped = 0

    for entity, filename in ENTITIES.items():
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=f"raw/{entity}/"):
            for item in page.get("Contents", []):
                source_key = item["Key"]
                if source_key.rsplit("/", 1)[-1] != filename:
                    continue

                match = re.search(r"/ingest_date=(\d{4}-\d{2}-\d{2})/", source_key)
                if not match:
                    skipped += 1
                    continue

                ingest_date = match.group(1)
                bronze_key = (
                    f"bronze/{entity}/ingest_date={ingest_date}/batch_id=legacy/{filename}"
                )
                try:
                    existing = s3.head_object(Bucket=bucket, Key=bronze_key)
                except ClientError as error:
                    code = error.response.get("Error", {}).get("Code")
                    if code not in {"404", "NoSuchKey", "NotFound"}:
                        raise
                else:
                    if existing["ContentLength"] != item["Size"]:
                        raise RuntimeError(f"Tamanho divergente no destino existente: {bronze_key}")
                    skipped += 1
                    continue

                s3.copy_object(
                    Bucket=bucket,
                    Key=bronze_key,
                    CopySource={"Bucket": bucket, "Key": source_key},
                    MetadataDirective="COPY",
                )
                migrated = s3.head_object(Bucket=bucket, Key=bronze_key)
                if migrated["ContentLength"] != item["Size"]:
                    raise RuntimeError(f"Tamanho divergente após cópia: {bronze_key}")
                copied += 1

    print(f"Migração Raw para Bronze: {copied} copiados; {skipped} ignorados")
    return {"copied": copied, "skipped": skipped}


def main():
    parser = argparse.ArgumentParser(description="Copia dados Raw legados para Bronze sem removê-los")
    parser.add_argument("bucket")
    args = parser.parse_args()
    migrate_raw_to_bronze(args.bucket)


if __name__ == "__main__":
    main()