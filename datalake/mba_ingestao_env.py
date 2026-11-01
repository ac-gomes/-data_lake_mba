import argparse
import os
import re
from datetime import datetime
from pathlib import Path

import boto3
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "datalake" / "Dados"
load_dotenv(PROJECT_ROOT / ".env")

FILES = (
    ("clientes.json", "clientes"),
    ("pedidos.csv", "pedidos"),
    ("produtos.csv", "produtos"),
)


def client():
    return boto3.client(
        "s3",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def ingest_data_files(bucket, ingest_date=None, batch_id=None, s3_client=None):
    ingest_date = ingest_date or datetime.now().strftime("%Y-%m-%d")
    batch_id = batch_id or datetime.now().strftime("%Y%m%dT%H%M%S%f")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", ingest_date):
        raise ValueError("ingest_date deve usar o formato YYYY-MM-DD")
    datetime.strptime(ingest_date, "%Y-%m-%d")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", batch_id):
        raise ValueError("batch_id contém caracteres inválidos")
    s3 = s3_client or client()

    for filename, entity in FILES:
        source = DATA_DIR / filename
        if not source.exists():
            raise FileNotFoundError(f"Arquivo local ausente: {source}")

        object_name = f"{Path(filename).stem}_{batch_id}{Path(filename).suffix}"
        partition = f"ingest_date={ingest_date}/batch_id={batch_id}/{object_name}"
        transient_key = f"transient/{entity}/{partition}"
        bronze_key = f"bronze/{entity}/{partition}"

        s3.upload_file(str(source), bucket, transient_key)
        transient = s3.head_object(Bucket=bucket, Key=transient_key)
        expected_size = source.stat().st_size
        if transient["ContentLength"] != expected_size:
            raise RuntimeError(f"Tamanho divergente no staging: s3://{bucket}/{transient_key}")

        s3.copy_object(
            Bucket=bucket,
            Key=bronze_key,
            CopySource={"Bucket": bucket, "Key": transient_key},
            MetadataDirective="COPY",
        )
        bronze = s3.head_object(Bucket=bucket, Key=bronze_key)
        if bronze["ContentLength"] != expected_size:
            raise RuntimeError(f"Tamanho divergente na Bronze: s3://{bucket}/{bronze_key}")

        print(f"Transient: s3://{bucket}/{transient_key}")
        print(f"Bronze: s3://{bucket}/{bronze_key}")

    return ingest_date, batch_id


def replace_data_files(bucket):
    """Compatibilidade com chamadas antigas; a ingestão agora preserva lotes."""
    return ingest_data_files(bucket)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    parser.add_argument("--ingest-date")
    parser.add_argument("--batch-id")
    args = parser.parse_args()
    ingest_data_files(args.bucket, args.ingest_date, args.batch_id)


if __name__ == "__main__":
    main()
