import argparse
import os
import re
import time

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


def client():
    return boto3.client(
        "athena",
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    )


def execute(athena, sql, database, output, description):
    print(f"{description}...")
    params = {"QueryString": sql, "ResultConfiguration": {"OutputLocation": output}}
    if database:
        params["QueryExecutionContext"] = {"Database": database}
    query_id = athena.start_query_execution(**params)["QueryExecutionId"]
    while True:
        execution = athena.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]
        state = execution["Status"]["State"]
        if state == "SUCCEEDED":
            return
        if state in ("FAILED", "CANCELLED"):
            reason = execution["Status"].get("StateChangeReason", "motivo desconhecido")
            raise RuntimeError(f"{description} falhou: {reason}")
        time.sleep(1)


def setup_catalog(bucket):
    athena = client()
    suffix = re.sub(r"[^a-zA-Z0-9_]", "_", bucket).lower()
    database = f"catalog_db_athena_{suffix.replace('datalake_bucket_', 'bucket_')}"
    output = f"s3://{bucket}/athena-results/"
    statements = (
        (None, f"CREATE DATABASE IF NOT EXISTS {database}", "Criando/verificando catálogo"),
        (database, f"DROP TABLE IF EXISTS {database}.silver_fato_vendas", "Atualizando metadados antigos da Silver"),
        (database, f"DROP TABLE IF EXISTS {database}.gold_analises_vendas", "Atualizando metadados antigos da Gold"),
        (database, f"""
            CREATE EXTERNAL TABLE IF NOT EXISTS {database}.bronze_clientes (
                cliente_id INT, nome STRING, cidade STRING, estado STRING
            ) PARTITIONED BY (ingest_date STRING, batch_id STRING)
            ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
            STORED AS TEXTFILE
            LOCATION 's3://{bucket}/bronze/clientes/'
        """, "Criando schema bronze_clientes"),
        (database, f"""
            CREATE EXTERNAL TABLE IF NOT EXISTS {database}.bronze_pedidos (
                pedido_id INT, cliente_id INT, produto_id INT,
                quantidade INT, valor DOUBLE, data_pedido STRING
            ) PARTITIONED BY (ingest_date STRING, batch_id STRING)
            ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
            STORED AS TEXTFILE
            LOCATION 's3://{bucket}/bronze/pedidos/'
            TBLPROPERTIES ('skip.header.line.count'='1')
        """, "Criando schema bronze_pedidos"),
        (database, f"""
            CREATE EXTERNAL TABLE IF NOT EXISTS {database}.bronze_produtos (
                produto_id INT, nome STRING, categoria STRING, preco DOUBLE
            ) PARTITIONED BY (ingest_date STRING, batch_id STRING)
            ROW FORMAT DELIMITED FIELDS TERMINATED BY ','
            STORED AS TEXTFILE
            LOCATION 's3://{bucket}/bronze/produtos/'
            TBLPROPERTIES ('skip.header.line.count'='1')
        """, "Criando schema bronze_produtos"),
        (database, f"MSCK REPAIR TABLE {database}.bronze_clientes", "Sincronizando partições de clientes"),
        (database, f"MSCK REPAIR TABLE {database}.bronze_pedidos", "Sincronizando partições de pedidos"),
        (database, f"MSCK REPAIR TABLE {database}.bronze_produtos", "Sincronizando partições de produtos"),
    )
    for statement_database, sql, description in statements:
        execute(athena, sql, statement_database, output, description)
    print(f"Catálogo Athena recriado: {database}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    args = parser.parse_args()
    try:
        setup_catalog(args.bucket)
    except ClientError as error:
        raise RuntimeError(error.response.get("Error", {}).get("Code", "AWS_ERROR")) from error


if __name__ == "__main__":
    main()
