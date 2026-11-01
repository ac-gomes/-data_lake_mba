import argparse
import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import boto3
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

RAW_DIR = PROJECT_ROOT / "datalake" / "Dados"
QUARANTINE_DIR = Path(__file__).resolve().parent / "quarantine"


def carregar_clientes(caminho: Path) -> Dict[int, Dict[str, object]]:
    clientes: Dict[int, Dict[str, object]] = {}
    with caminho.open("r", encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            registro = json.loads(linha)
            cliente_id = int(registro["cliente_id"])
            clientes[cliente_id] = registro
    return clientes


def carregar_produtos(caminho: Path) -> Dict[int, Dict[str, object]]:
    produtos: Dict[int, Dict[str, object]] = {}
    with caminho.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            produto_id = int(linha["produto_id"])
            produtos[produto_id] = {
                "nome": linha["nome"],
                "categoria": linha["categoria"],
                "preco": float(linha["preco"]),
            }
    return produtos


def avaliar_registro(
    registro: Dict[str, object],
    clientes: Dict[int, Dict[str, object]],
    produtos: Dict[int, Dict[str, object]],
) -> Tuple[List[str], bool]:
    motivos: List[str] = []

    try:
        quantidade = int(registro.get("quantidade", 0))
    except (TypeError, ValueError):
        quantidade = 0

    try:
        cliente_id = int(registro.get("cliente_id", -1))
    except (TypeError, ValueError):
        cliente_id = -1

    try:
        produto_id = int(registro.get("produto_id", -1))
    except (TypeError, ValueError):
        produto_id = -1

    if quantidade <= 0:
        motivos.append("quantidade_invalida")

    if cliente_id not in clientes:
        motivos.append("cliente_inexistente")

    if produto_id not in produtos:
        motivos.append("produto_inexistente")

    return motivos, not motivos


def preparar_silver_registro(
    registro: Dict[str, object],
    clientes: Dict[int, Dict[str, object]],
    produtos: Dict[int, Dict[str, object]],
) -> Dict[str, object]:
    cliente_id = int(registro["cliente_id"])
    produto_id = int(registro["produto_id"])
    quantidade = int(registro["quantidade"])
    produto = produtos[produto_id]
    cliente = clientes[cliente_id]

    valor_total = round(quantidade * float(produto["preco"]), 2)

    return {
        "pedido_id": int(registro["pedido_id"]),
        "cliente_id": cliente_id,
        "produto_id": produto_id,
        "quantidade": quantidade,
        "preco": float(produto["preco"]),
        "valor_total": valor_total,
        "data_pedido": registro.get("data_pedido"),
        "nome_cliente": cliente.get("nome"),
        "cidade": cliente.get("cidade"),
        "uf": cliente.get("estado"),
        "nome_produto": produto.get("nome"),
        "categoria": produto.get("categoria"),
    }


def publicar_quarentena_s3(
    bucket: str,
    registros: List[Dict[str, object]],
    ingest_date: str,
    batch_id: str = "manual",
    s3_client=None,
) -> str:
    key = (
        f"quarantine/pedidos_rejeitados/ingest_date={ingest_date}/"
        f"batch_id={batch_id}/rejeitados.json"
    )
    if s3_client is None:
        s3_client = boto3.client(
            "s3",
            region_name=os.environ["AWS_REGION"],
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        )

    payload = json.dumps(registros, ensure_ascii=False)
    s3_client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload.encode("utf-8"),
        ContentType="application/json",
    )

    return key


def processar_pedidos(
    pedidos_csv: Path,
    clientes_json: Path,
    produtos_csv: Path,
    output_silver: Path,
    output_quarantine: Path,
    bucket: str = None,
    ingest_date: str = None,
    batch_id: str = "manual",
    s3_client=None,
) -> Dict[str, int]:
    ingest_date = ingest_date or datetime.now().strftime("%Y-%m-%d")
    clientes = carregar_clientes(clientes_json)
    produtos = carregar_produtos(produtos_csv)

    silver_registros: List[Dict[str, object]] = []
    registros_rejeitados: List[Dict[str, object]] = []

    with pedidos_csv.open("r", encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        for linha in leitor:
            motivos, valido = avaliar_registro(linha, clientes, produtos)

            if valido:
                silver_registros.append(preparar_silver_registro(linha, clientes, produtos))
            else:
                rejeitado = {
                    "pedido_id": linha.get("pedido_id"),
                    "cliente_id": linha.get("cliente_id"),
                    "produto_id": linha.get("produto_id"),
                    "quantidade": linha.get("quantidade"),
                    "valor": linha.get("valor"),
                    "data_pedido": linha.get("data_pedido"),
                    "motivos_rejeicao": motivos,
                    "data_processamento": ingest_date,
                    "arquivo_origem": str(pedidos_csv.name),
                    "ingest_date": ingest_date,
                }
                registros_rejeitados.append(rejeitado)

    output_silver.parent.mkdir(parents=True, exist_ok=True)
    output_quarantine.parent.mkdir(parents=True, exist_ok=True)

    with output_silver.open("w", encoding="utf-8", newline="") as arquivo:
        campos = [
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
        ]
        escritor = csv.DictWriter(arquivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(silver_registros)

    with output_quarantine.open("w", encoding="utf-8", newline="") as arquivo:
        campos_quarentena = [
            "pedido_id",
            "cliente_id",
            "produto_id",
            "quantidade",
            "valor",
            "data_pedido",
            "motivos_rejeicao",
            "data_processamento",
            "arquivo_origem",
            "ingest_date",
        ]
        escritor = csv.DictWriter(arquivo, fieldnames=campos_quarentena)
        escritor.writeheader()
        for item in registros_rejeitados:
            item["motivos_rejeicao"] = ";".join(item["motivos_rejeicao"])
            escritor.writerow(item)

    if bucket:
        publicar_quarentena_s3(
            bucket=bucket,
            registros=registros_rejeitados,
            ingest_date=ingest_date,
            batch_id=batch_id,
            s3_client=s3_client,
        )

    return {
        "validos": len(silver_registros),
        "rejeitados": len(registros_rejeitados),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida pedidos e publica a quarentena")
    parser.add_argument("--bucket")
    parser.add_argument("--ingest-date", default=datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--batch-id", default="manual")
    args = parser.parse_args()

    pedidos_raw = RAW_DIR / "pedidos.csv"
    clientes_raw = RAW_DIR / "clientes.json"
    produtos_raw = RAW_DIR / "produtos.csv"

    silver_path = Path(__file__).resolve().parent / "silver" / "fato_vendas" / "silver_fato_vendas.csv"
    quarantine_path = QUARANTINE_DIR / "pedidos_rejeitados" / "rejeitados.csv"

    resultado = processar_pedidos(
        pedidos_csv=pedidos_raw,
        clientes_json=clientes_raw,
        produtos_csv=produtos_raw,
        output_silver=silver_path,
        output_quarantine=quarantine_path,
        bucket=args.bucket,
        ingest_date=args.ingest_date,
        batch_id=args.batch_id,
    )

    print("Processamento da camada Silver")
    print(f"Registros válidos: {resultado['validos']}")
    print(f"Registros rejeitados: {resultado['rejeitados']}")
    print(f"Silver: {silver_path}")
    print(f"Quarentena: {quarantine_path}")


if __name__ == "__main__":
    main()
