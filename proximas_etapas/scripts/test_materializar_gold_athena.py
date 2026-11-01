import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mba_processar_gold import build_gold_sql, build_gold_table_sql


def test_build_gold_sql_contains_required_rules():
    sql = build_gold_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
        ingest_date="2026-08-31",
    )

    assert "UNLOAD (" in sql
    assert "format = 'PARQUET'" in sql
    assert "compression = 'SNAPPY'" in sql
    assert "gold/analises_vendas/ingest_date=2026-08-31/batch_id=manual/" in sql
    assert "COUNT(DISTINCT pedido_id)" in sql
    assert "SUM(quantidade)" in sql
    assert "SUM(valor_total)" in sql
    assert "GROUP BY uf, categoria" in sql
    assert "WHERE ingest_date = '2026-08-31' AND batch_id = 'manual'" in sql


def test_gold_table_uses_medallion_location_and_partitions():
    sql = build_gold_table_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
    )

    assert "PARTITIONED BY (ingest_date STRING, batch_id STRING)" in sql
    assert "s3://datalake-bucket-turma-c-trabalho-mba/gold/analises_vendas/" in sql


def test_build_gold_sql_uses_uf_and_categoria_and_date_filter():
    sql = build_gold_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
        ingest_date="2026-08-31",
    )

    assert "uf" in sql
    assert "categoria" in sql
    assert "COUNT(DISTINCT pedido_id) AS total_pedidos" in sql
    assert "SUM(quantidade) AS total_itens" in sql
    assert "SUM(valor_total) AS faturamento_total" in sql
    assert "ticket_medio" in sql
    assert "GROUP BY uf, categoria" in sql
