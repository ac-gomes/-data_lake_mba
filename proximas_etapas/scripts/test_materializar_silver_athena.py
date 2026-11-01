import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mba_materializar_silver_athena import build_silver_sql, build_silver_table_sql


def test_build_silver_sql_contains_required_rules():
    sql = build_silver_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
        ingest_date="2026-08-31",
    )

    assert "UNLOAD (" in sql
    assert "format = 'PARQUET'" in sql
    assert "compression = 'SNAPPY'" in sql
    assert "silver/fato_vendas/ingest_date=2026-08-31/batch_id=manual/" in sql
    assert "p.quantidade > 0" in sql
    assert "CAST(p.quantidade AS DOUBLE) * pr.preco AS valor_total" in sql
    assert "FROM catalog_db_athena_bucket_turma_c_trabalho_mba.bronze_pedidos p" in sql
    assert "JOIN catalog_db_athena_bucket_turma_c_trabalho_mba.bronze_clientes c" in sql
    assert "JOIN catalog_db_athena_bucket_turma_c_trabalho_mba.bronze_produtos pr" in sql


def test_build_silver_sql_uses_ingest_date_filter():
    sql = build_silver_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
        ingest_date="2026-08-31",
    )

    assert "p.ingest_date = '2026-08-31'" in sql
    assert "p.batch_id = 'manual'" in sql
    assert "c.ingest_date = '2026-08-31' AND c.batch_id = 'manual'" in sql
    assert "pr.ingest_date = '2026-08-31' AND pr.batch_id = 'manual'" in sql


def test_silver_table_uses_medallion_location_and_partitions():
    sql = build_silver_table_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
    )

    assert "PARTITIONED BY (ingest_date STRING, batch_id STRING)" in sql
    assert "s3://datalake-bucket-turma-c-trabalho-mba/silver/fato_vendas/" in sql


def test_build_silver_sql_has_expected_columns():
    sql = build_silver_sql(
        database="catalog_db_athena_bucket_turma_c_trabalho_mba",
        bucket="datalake-bucket-turma-c-trabalho-mba",
        ingest_date="2026-08-31",
    )

    for column in [
        "pedido_id",
        "cliente_id",
        "produto_id",
        "quantidade",
        "preco",
        "valor_total",
        "data_pedido",
        "nome_cliente",
        "cidade",
        "uf",
        "nome_produto",
        "categoria",
    ]:
        assert column in sql
