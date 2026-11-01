import csv
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from mba_processar_silver import (
    avaliar_registro,
    carregar_clientes,
    carregar_produtos,
    preparar_silver_registro,
    processar_pedidos,
    publicar_quarentena_s3,
)


@pytest.fixture
def base_dados():
    clientes = {
        505: {"cliente_id": 505, "nome": "Larissa Santos", "cidade": "São José", "estado": "SC"},
        506: {"cliente_id": 506, "nome": "Beatriz Duarte", "cidade": "Salvador", "estado": "BA"},
    }
    produtos = {
        9001: {"produto_id": 9001, "nome": "Smartphone", "categoria": "Eletronicos", "preco": 1000.0},
        9002: {"produto_id": 9002, "nome": "Notebook", "categoria": "Informatica", "preco": 2500.0},
    }
    return clientes, produtos


@pytest.mark.parametrize(
    "registro, esperado",
    [
        (
            {
                "pedido_id": 1001,
                "cliente_id": 505,
                "produto_id": 9001,
                "quantidade": 0,
                "valor": 10.0,
                "data_pedido": "2026-08-31",
            },
            ["quantidade_invalida"],
        ),
        (
            {
                "pedido_id": 1002,
                "cliente_id": 9999,
                "produto_id": 9001,
                "quantidade": 2,
                "valor": 10.0,
                "data_pedido": "2026-08-31",
            },
            ["cliente_inexistente"],
        ),
        (
            {
                "pedido_id": 1003,
                "cliente_id": 505,
                "produto_id": 9999,
                "quantidade": 2,
                "valor": 10.0,
                "data_pedido": "2026-08-31",
            },
            ["produto_inexistente"],
        ),
        (
            {
                "pedido_id": 1004,
                "cliente_id": 505,
                "produto_id": 9001,
                "quantidade": 2,
                "valor": 10.0,
                "data_pedido": "2026-08-31",
            },
            [],
        ),
    ],
)
def test_avaliar_registro(base_dados, registro, esperado):
    clientes, produtos = base_dados
    motivos, valido = avaliar_registro(registro, clientes, produtos)

    if esperado:
        assert valido is False
        assert set(motivos) == set(esperado)
    else:
        assert valido is True
        assert motivos == []


def test_preparar_silver_registro(base_dados):
    clientes, produtos = base_dados
    registro = {
        "pedido_id": 1001,
        "cliente_id": 505,
        "produto_id": 9001,
        "quantidade": 3,
        "valor": 3000.0,
        "data_pedido": "2026-08-31",
    }

    silver = preparar_silver_registro(registro, clientes, produtos)

    assert silver["pedido_id"] == 1001
    assert silver["nome_cliente"] == "Larissa Santos"
    assert silver["cidade"] == "São José"
    assert silver["uf"] == "SC"
    assert silver["nome_produto"] == "Smartphone"
    assert silver["categoria"] == "Eletronicos"
    assert silver["valor_total"] == 3000.0


def test_processar_pedidos_grava_valido_e_rejeitado(tmp_path, base_dados):
    clientes, produtos = base_dados

    pedidos = [
        {"pedido_id": 1, "cliente_id": 505, "produto_id": 9001, "quantidade": 2, "valor": 2000.0, "data_pedido": "2026-08-31"},
        {"pedido_id": 2, "cliente_id": 9999, "produto_id": 9001, "quantidade": 2, "valor": 2000.0, "data_pedido": "2026-08-31"},
    ]

    pedidos_csv = tmp_path / "pedidos.csv"
    clientes_json = tmp_path / "clientes.json"
    produtos_csv = tmp_path / "produtos.csv"
    silver_csv = tmp_path / "silver" / "fato_vendas.csv"
    quarantine_csv = tmp_path / "quarantine" / "rejeitados.csv"

    with clientes_json.open("w", encoding="utf-8") as fh:
        for cliente in clientes.values():
            fh.write(json.dumps(cliente) + "\n")

    with produtos_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["produto_id", "nome", "categoria", "preco"])
        writer.writeheader()
        for produto in produtos.values():
            writer.writerow(produto)

    with pedidos_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["pedido_id", "cliente_id", "produto_id", "quantidade", "valor", "data_pedido"])
        writer.writeheader()
        writer.writerows(pedidos)

    resultado = processar_pedidos(pedidos_csv, clientes_json, produtos_csv, silver_csv, quarantine_csv)

    assert resultado == {"validos": 1, "rejeitados": 1}
    assert silver_csv.exists()
    assert quarantine_csv.exists()

    with silver_csv.open("r", encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
        assert len(linhas) == 1
        assert linhas[0]["valor_total"] == "2000.0"

    with quarantine_csv.open("r", encoding="utf-8") as fh:
        linhas = list(csv.DictReader(fh))
        assert len(linhas) == 1
        assert linhas[0]["motivos_rejeicao"] == "cliente_inexistente"


def test_carregar_clientes_e_produtos(base_dados):
    clientes, produtos = base_dados
    assert len(clientes) == 2
    assert len(produtos) == 2
    assert clientes[505]["cidade"] == "São José"
    assert produtos[9001]["categoria"] == "Eletronicos"


def test_publicar_quarentena_s3():
    class FakeS3Client:
        def __init__(self):
            self.calls = []

        def put_object(self, **kwargs):
            self.calls.append(kwargs)
            return {"ETag": "fake-etag"}

    registros = [{
        "pedido_id": 99,
        "cliente_id": 505,
        "produto_id": 9001,
        "quantidade": 0,
        "valor": 0.0,
        "motivos_rejeicao": ["quantidade_invalida"],
        "data_pedido": "2026-08-31",
        "data_processamento": "2026-08-31",
        "arquivo_origem": "pedidos.csv",
        "ingest_date": "2026-08-31",
    }]
    fake_s3 = FakeS3Client()

    key = publicar_quarentena_s3(
        bucket="bucket-teste",
        registros=registros,
        ingest_date="2026-08-31",
        batch_id="batch-01",
        s3_client=fake_s3,
    )

    assert key == (
        "quarantine/pedidos_rejeitados/ingest_date=2026-08-31/"
        "batch_id=batch-01/rejeitados.json"
    )
    assert len(fake_s3.calls) == 1
    body = json.loads(fake_s3.calls[0]["Body"].decode("utf-8"))
    assert body[0]["motivos_rejeicao"] == ["quantidade_invalida"]
    assert fake_s3.calls[0]["Bucket"] == "bucket-teste"


def test_publicar_quarentena_propagates_s3_failure():
    class FailedS3Client:
        def put_object(self, **kwargs):
            raise RuntimeError("upload failed")

    with pytest.raises(RuntimeError, match="upload failed"):
        publicar_quarentena_s3(
            bucket="bucket-teste",
            registros=[],
            ingest_date="2026-08-31",
            batch_id="batch-01",
            s3_client=FailedS3Client(),
        )
