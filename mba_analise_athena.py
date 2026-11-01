import os
import re
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)


def require_env(name):
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Variável de ambiente '{name}' não foi encontrada no arquivo .env.")
    return value


AWS_ACCESS_KEY_ID = require_env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = require_env("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
AWS_REGION = require_env("AWS_REGION")


if len(sys.argv) != 2:
    print()
    print("Uso:")
    print("    python analise_athena.py NOME_DO_BUCKET")
    print()
    print("Exemplo:")
    print("    python analise_athena.py datalake-bucket-turma-c-trabalho-mba")
    print()
    sys.exit(1)

BUCKET_NAME = sys.argv[1]
DB_SUFFIX = re.sub(r"[^a-zA-Z0-9_]", "_", BUCKET_NAME).lower()
DATABASE_NAME = f"catalog_db_athena_{DB_SUFFIX.replace('datalake_bucket_', 'bucket_')}"
OUTPUT_LOCATION = f"s3://{BUCKET_NAME}/athena-results/"

athena = boto3.client(
    "athena",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN,
)


def executar_query(query, database=None, descricao="Executando consulta"):
    print(f"\n-> {descricao}...")

    params = {
        "QueryString": query,
        "ResultConfiguration": {"OutputLocation": OUTPUT_LOCATION},
    }
    if database:
        params["QueryExecutionContext"] = {"Database": database}

    try:
        response = athena.start_query_execution(**params)
        query_execution_id = response["QueryExecutionId"]

        while True:
            status_response = athena.get_query_execution(QueryExecutionId=query_execution_id)
            status = status_response["QueryExecution"]["Status"]["State"]

            if status == "SUCCEEDED":
                print(f"[OK] Sucesso ({query_execution_id})")
                return query_execution_id

            if status in ["FAILED", "CANCELLED"]:
                motivo = status_response["QueryExecution"]["Status"].get("StateChangeReason", "Erro desconhecido")
                print(f"[ERRO] Falha na query: {motivo}")
                return None

            time.sleep(1)

    except ClientError as e:
        print(f"[ERRO BOTO3]: {e}")
        return None


def obter_resultados(query_execution_id):
    resultados = athena.get_query_results(QueryExecutionId=query_execution_id)
    linhas = resultados["ResultSet"]["Rows"]
    tabela = []
    for linha in linhas:
        tabela.append([item.get("VarCharValue", "") for item in linha["Data"]])
    return tabela


def print_tabela(titulo, tabela):
    print()
    print("=" * 90)
    print(titulo)
    print("=" * 90)
    for idx, linha in enumerate(tabela):
        print(" | ".join(linha))
    print("=" * 90)


QUERIES = [
    (
        "Total de clientes",
        f"SELECT COUNT(*) AS total_clientes FROM {DATABASE_NAME}.bronze_clientes;",
    ),
    (
        "Total de pedidos",
        f"SELECT COUNT(*) AS total_pedidos FROM {DATABASE_NAME}.bronze_pedidos;",
    ),
    (
        "Total faturado",
        f"SELECT ROUND(SUM(valor), 2) AS faturamento_total FROM {DATABASE_NAME}.bronze_pedidos;",
    ),
    (
        "Top 10 produtos por faturamento",
        f"""
        SELECT pr.nome, ROUND(SUM(p.valor), 2) AS faturamento
                FROM {DATABASE_NAME}.bronze_pedidos p
                JOIN {DATABASE_NAME}.bronze_produtos pr
                    ON p.produto_id = pr.produto_id
                 AND p.ingest_date = pr.ingest_date
                 AND p.batch_id = pr.batch_id
        GROUP BY pr.nome
        ORDER BY faturamento DESC
        LIMIT 10;
        """,
    ),
    (
        "Top 10 cidades por clientes",
        f"""
        SELECT cidade, COUNT(*) AS total_clientes
        FROM {DATABASE_NAME}.bronze_clientes
        GROUP BY cidade
        ORDER BY total_clientes DESC
        LIMIT 10;
        """,
    ),
]


def main():
    print("=" * 60)
    print("      ANALISE DO DATA LAKE NO ATHENA")
    print("=" * 60)
    print(f"Bucket : {BUCKET_NAME}")
    print(f"DB     : {DATABASE_NAME}")
    print(f"Output : {OUTPUT_LOCATION}")

    for descricao, query in QUERIES:
        qid = executar_query(query, DATABASE_NAME, descricao)
        if not qid:
            print(f"\nInterrompendo por falha na consulta: {descricao}")
            sys.exit(1)

        resultados = obter_resultados(qid)
        print_tabela(descricao, resultados)

    print()
    print("=" * 60)
    print("ANALISE FINALIZADA")
    print("=" * 60)


if __name__ == "__main__":
    main()
