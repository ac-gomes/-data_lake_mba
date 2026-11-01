import argparse
import os
import time
from pathlib import Path

import boto3
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def client():
    return boto3.client(
        "athena",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def build_gold_table_sql(database: str, bucket: str) -> str:
    return f"""
CREATE EXTERNAL TABLE IF NOT EXISTS {database}.gold_analises_vendas (
    uf STRING,
    categoria STRING,
    total_pedidos BIGINT,
    total_itens DOUBLE,
    faturamento_total DOUBLE,
    ticket_medio DOUBLE,
    data_referencia DATE
)
PARTITIONED BY (ingest_date STRING, batch_id STRING)
STORED AS PARQUET
LOCATION 's3://{bucket}/gold/analises_vendas/'
TBLPROPERTIES ('parquet.compression'='SNAPPY')
"""


def build_gold_sql(
    database: str,
    bucket: str,
    ingest_date: str,
    batch_id: str = "manual",
) -> str:
    return f"""
UNLOAD (
SELECT
    uf,
    categoria,
    COUNT(DISTINCT pedido_id) AS total_pedidos,
    SUM(quantidade) AS total_itens,
    SUM(valor_total) AS faturamento_total,
    ROUND(SUM(valor_total) / COUNT(DISTINCT pedido_id), 2) AS ticket_medio,
    CAST(MAX(data_pedido) AS DATE) AS data_referencia
FROM {database}.silver_fato_vendas
WHERE ingest_date = '{ingest_date}' AND batch_id = '{batch_id}'
GROUP BY uf, categoria
)
TO 's3://{bucket}/gold/analises_vendas/ingest_date={ingest_date}/batch_id={batch_id}/'
WITH (format = 'PARQUET', compression = 'SNAPPY')
"""


def build_gold_partition_sql(database: str, bucket: str, ingest_date: str, batch_id: str) -> str:
    location = f"s3://{bucket}/gold/analises_vendas/ingest_date={ingest_date}/batch_id={batch_id}/"
    return (
        f"ALTER TABLE {database}.gold_analises_vendas ADD IF NOT EXISTS "
        f"PARTITION (ingest_date='{ingest_date}', batch_id='{batch_id}') LOCATION '{location}'"
    )


def execute_sql(sql: str, database: str, bucket: str) -> str:
    athena = client()
    output = f"s3://{bucket}/athena-results/"
    result = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        ResultConfiguration={"OutputLocation": output},
    )
    query_id = result["QueryExecutionId"]
    while True:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            return query_id
        if state in {"FAILED", "CANCELLED"}:
            reason = execution["Status"].get("StateChangeReason", "unknown")
            raise RuntimeError(f"Athena falhou: {reason}")
        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description="Materializa a camada Gold no Athena")
    parser.add_argument("bucket", help="Bucket do projeto")
    parser.add_argument("--database", default="catalog_db_athena_bucket_turma_c_trabalho_mba")
    parser.add_argument("--ingest-date", required=True)
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    execute_sql(build_gold_table_sql(args.database, args.bucket), args.database, args.bucket)
    sql = build_gold_sql(args.database, args.bucket, args.ingest_date, args.batch_id)
    execute_sql(sql, args.database, args.bucket)
    query_id = execute_sql(
        build_gold_partition_sql(args.database, args.bucket, args.ingest_date, args.batch_id),
        args.database,
        args.bucket,
    )
    print(f"Gold materializada no Athena: {query_id}")


if __name__ == "__main__":
    main()
