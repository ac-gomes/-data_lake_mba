import os
import re
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def require_env(name):
    value = os.getenv(name)
    if value is None or value == "":
        raise RuntimeError(f"Variável de ambiente '{name}' não foi encontrada no arquivo .env.")
    return value


AWS_ACCESS_KEY_ID = require_env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = require_env("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")
AWS_REGION = require_env("AWS_REGION")


if len(sys.argv) < 2:
    print()
    print("Uso:")
    print("    python mba_auditar_athena.py NOME_DO_BUCKET")
    print()
    print("Exemplo:")
    print("    python mba_auditar_athena.py datalake-bucket-turma-c-trabalho-mba")
    print()
    sys.exit(1)

BUCKET_NAME = sys.argv[1]
if len(sys.argv) not in (2, 4):
    raise SystemExit("Uso: mba_auditar_athena.py BUCKET [INGEST_DATE BATCH_ID]")
INGEST_DATE = sys.argv[2] if len(sys.argv) == 4 else None
BATCH_ID = sys.argv[3] if len(sys.argv) == 4 else None
if INGEST_DATE and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", INGEST_DATE):
    raise SystemExit("INGEST_DATE deve usar o formato YYYY-MM-DD")
if BATCH_ID and not re.fullmatch(r"[A-Za-z0-9_-]+", BATCH_ID):
    raise SystemExit("BATCH_ID contém caracteres inválidos")
PARTITION_FILTER = (
    f"ingest_date = '{INGEST_DATE}' AND batch_id = '{BATCH_ID}'"
    if INGEST_DATE and BATCH_ID else "TRUE"
)
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
        "A01 - Existência de tabelas",
        f"""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = '{DATABASE_NAME}'
        ORDER BY table_name;
        """,
    ),
    (
        "A02 - Contagens por camada",
        f"""
        SELECT
            'bronze_pedidos' AS tabela,
            (SELECT COUNT(*) FROM {DATABASE_NAME}.bronze_pedidos WHERE {PARTITION_FILTER}) AS registros
        UNION ALL
        SELECT 'bronze_clientes',
            (SELECT COUNT(*) FROM {DATABASE_NAME}.bronze_clientes WHERE {PARTITION_FILTER})
        UNION ALL
        SELECT 'bronze_produtos',
            (SELECT COUNT(*) FROM {DATABASE_NAME}.bronze_produtos WHERE {PARTITION_FILTER})
        UNION ALL
        SELECT 'silver_fato_vendas',
            (SELECT COUNT(*) FROM {DATABASE_NAME}.silver_fato_vendas WHERE {PARTITION_FILTER})
        UNION ALL
        SELECT 'gold_analises_vendas',
            (SELECT COUNT(*) FROM {DATABASE_NAME}.gold_analises_vendas WHERE {PARTITION_FILTER})
        ORDER BY tabela;
        """,
    ),
    (
        "A03 - Equivalência de faturamento",
        f"""
        SELECT
            (SELECT ROUND(SUM(valor), 2) FROM {DATABASE_NAME}.bronze_pedidos WHERE {PARTITION_FILTER}) AS faturamento_bronze,
            (SELECT ROUND(SUM(valor_total), 2) FROM {DATABASE_NAME}.silver_fato_vendas WHERE {PARTITION_FILTER}) AS faturamento_silver,
            (SELECT ROUND(SUM(faturamento_total), 2) FROM {DATABASE_NAME}.gold_analises_vendas WHERE {PARTITION_FILTER}) AS faturamento_gold;
        """,
    ),
    (
        "A04 - Arquivos Parquet da Silver (usando $path)",
        f"""
        SELECT DISTINCT "$path" AS arquivo_s3, COUNT(*) AS registros
        FROM {DATABASE_NAME}.silver_fato_vendas
        WHERE {PARTITION_FILTER}
        GROUP BY "$path"
        ORDER BY arquivo_s3;
        """,
    ),
    (
        "A05 - Arquivos Parquet da Gold (usando $path)",
        f"""
        SELECT DISTINCT "$path" AS arquivo_s3, COUNT(*) AS registros
        FROM {DATABASE_NAME}.gold_analises_vendas
        WHERE {PARTITION_FILTER}
        GROUP BY "$path"
        ORDER BY arquivo_s3;
        """,
    ),
    (
        "A06 - Agregação Gold por UF",
        f"""
        SELECT uf, COUNT(*) AS categorias, SUM(total_pedidos) AS total_pedidos,
               ROUND(SUM(faturamento_total), 2) AS faturamento_total
        FROM {DATABASE_NAME}.gold_analises_vendas
        WHERE {PARTITION_FILTER}
        GROUP BY uf
        ORDER BY faturamento_total DESC;
        """,
    ),
]


def main():
    print("=" * 90)
    print("      AUDITORIA DO DATA LAKE NO ATHENA")
    print("=" * 90)
    print(f"Bucket   : {BUCKET_NAME}")
    print(f"Database : {DATABASE_NAME}")
    print(f"Output   : {OUTPUT_LOCATION}")
    if INGEST_DATE and BATCH_ID:
        print(f"Lote     : {INGEST_DATE} / {BATCH_ID}")

    queries_success = 0
    queries_total = len(QUERIES)

    for descricao, query in QUERIES:
        qid = executar_query(query, DATABASE_NAME, descricao)
        if not qid:
            print(f"\nInterrompendo por falha na consulta: {descricao}")
            continue

        queries_success += 1
        resultados = obter_resultados(qid)
        print_tabela(descricao, resultados)

    print()
    print("=" * 90)
    print("RESULTADO FINAL")
    print("=" * 90)
    if queries_success == queries_total:
        print("✅ APROVADO - Auditoria concluída com sucesso!")
        print(f"   Total de auditorias: {queries_success}/{queries_total}")
    else:
        print(f"⚠️  PARCIALMENTE APROVADO")
        print(f"   Total de auditorias bem-sucedidas: {queries_success}/{queries_total}")
    print("=" * 90)


if __name__ == "__main__":
    main()
