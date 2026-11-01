import csv
import sys
from pathlib import Path

from botocore.exceptions import ClientError
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datalake import mba_ingestao_env as ingestion
from datalake import mba_migrar_raw_para_bronze as migration
from datalake.Dados.mba_base_clientes import gerar_clientes
from datalake.Dados.mba_base_pedidos import gerar_pedidos
from datalake.Dados.mba_base_produtos import gerar_produtos
import mba_setup_ambiente as pipeline
from mba_processar_silver import avaliar_registro, carregar_clientes, carregar_produtos


class FakeS3Client:
    def __init__(self):
        self.objects = {}

    def upload_file(self, filename, bucket, key):
        self.objects[(bucket, key)] = Path(filename).read_bytes()

    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.objects[(Bucket, Key)])}

    def copy_object(self, Bucket, Key, CopySource, MetadataDirective):
        self.objects[(Bucket, Key)] = self.objects[(CopySource["Bucket"], CopySource["Key"])]


class FakePaginator:
    def __init__(self, client):
        self.client = client

    def paginate(self, Bucket, Prefix):
        contents = [
            {"Key": key, "Size": len(payload)}
            for (bucket, key), payload in self.client.objects.items()
            if bucket == Bucket and key.startswith(Prefix)
        ]
        return [{"Contents": contents}]


class FakeMigrationS3Client(FakeS3Client):
    def get_paginator(self, operation):
        return FakePaginator(self)

    def head_object(self, Bucket, Key):
        try:
            return super().head_object(Bucket, Key)
        except KeyError as error:
            raise ClientError({"Error": {"Code": "404"}}, "HeadObject") from error


def test_generated_orders_include_a_valid_customer_and_product(tmp_path):
    clients_path = tmp_path / "clientes.json"
    products_path = tmp_path / "produtos.csv"
    orders_path = tmp_path / "pedidos.csv"
    gerar_clientes(100, str(clients_path))
    gerar_produtos(100, str(products_path))
    gerar_pedidos(100, str(orders_path))

    clients = carregar_clientes(clients_path)
    products = carregar_produtos(products_path)
    with orders_path.open(encoding="utf-8", newline="") as source:
        valid_count = sum(
            avaliar_registro(row, clients, products)[1]
            for row in csv.DictReader(source)
        )

    assert valid_count >= 1


def test_ingestion_promotes_verified_batches(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_DIR", tmp_path)
    source_files = {
        "clientes.json": b'{"cliente_id": 1}\n',
        "pedidos.csv": b"pedido_id\n1\n",
        "produtos.csv": b"produto_id\n1\n",
    }
    for filename, payload in source_files.items():
        (tmp_path / filename).write_bytes(payload)

    fake_s3 = FakeS3Client()
    date, batch = ingestion.ingest_data_files(
        "bucket-teste", "2026-11-01", "batch-001", fake_s3
    )

    assert (date, batch) == ("2026-11-01", "batch-001")
    for entity, filename in (("clientes", "clientes.json"), ("pedidos", "pedidos.csv"),
                             ("produtos", "produtos.csv")):
        suffix = Path(filename).suffix
        name = f"{entity}_batch-001{suffix}"
        bronze_key = f"bronze/{entity}/ingest_date=2026-11-01/batch_id=batch-001/{name}"
        transient_key = f"transient/{entity}/ingest_date=2026-11-01/batch_id=batch-001/{name}"
        assert fake_s3.objects[("bucket-teste", bronze_key)] == source_files[filename]
        assert fake_s3.objects[("bucket-teste", transient_key)] == source_files[filename]


def test_legacy_migration_is_idempotent_and_preserves_raw():
    fake_s3 = FakeMigrationS3Client()
    for entity, filename in migration.ENTITIES.items():
        source_key = f"raw/{entity}/ingest_date=2026-08-31/{filename}"
        fake_s3.objects[("bucket-teste", source_key)] = b"legacy"

    first = migration.migrate_raw_to_bronze("bucket-teste", fake_s3)
    second = migration.migrate_raw_to_bronze("bucket-teste", fake_s3)

    assert first == {"copied": 3, "skipped": 0}
    assert second == {"copied": 0, "skipped": 3}
    for entity, filename in migration.ENTITIES.items():
        source_key = f"raw/{entity}/ingest_date=2026-08-31/{filename}"
        assert fake_s3.objects[("bucket-teste", source_key)] == b"legacy"


def test_ingestion_rejects_unsafe_partition_values(tmp_path, monkeypatch):
    monkeypatch.setattr(ingestion, "DATA_DIR", tmp_path)
    with pytest.raises(ValueError, match="ingest_date"):
        ingestion.ingest_data_files("bucket-teste", "2026/11/01", "batch-01", FakeS3Client())
    with pytest.raises(ValueError, match="batch_id"):
        ingestion.ingest_data_files("bucket-teste", "2026-11-01", "../batch", FakeS3Client())


def test_pipeline_runs_silver_before_gold(monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "etapa", lambda description, command, cwd=None: calls.append(command))

    pipeline.setup("bucket-teste", 10)

    scripts = [Path(command[1]).name for command in calls]
    assert scripts.index("mba_migrar_raw_para_bronze.py") < scripts.index("mba_ingestao_env.py")
    assert scripts.index("mba_materializar_silver_athena.py") < scripts.index("mba_processar_gold.py")
    assert scripts.index("mba_processar_gold.py") < scripts.index("mba_auditar_athena.py")
    ingest = calls[scripts.index("mba_ingestao_env.py")]
    silver = calls[scripts.index("mba_materializar_silver_athena.py")]
    gold = calls[scripts.index("mba_processar_gold.py")]
    assert ingest[ingest.index("--batch-id") + 1] == silver[silver.index("--batch-id") + 1]
    assert silver[silver.index("--batch-id") + 1] == gold[gold.index("--batch-id") + 1]