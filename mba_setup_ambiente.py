import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "datalake" / "Dados"


def etapa(descricao, comando, cwd=PROJECT_ROOT):
    print(f"\n{descricao}")
    resultado = subprocess.run(comando, cwd=cwd)
    if resultado.returncode != 0:
        raise RuntimeError(f"{descricao} falhou com código {resultado.returncode}")


def setup(bucket, quantidade):
    now = datetime.now()
    ingest_date = now.strftime("%Y-%m-%d")
    batch_id = now.strftime("%Y%m%dT%H%M%S%f")

    # FLUXO BASE (PROTEGIDO)
    etapa("[1/11] Verificando/criando somente o que faltar no S3", [
        sys.executable, "datalake/mba_create_bucket_env.py", bucket])
    etapa("[2/11] Migrando Raw para Bronze sem excluir a origem", [
        sys.executable, "datalake/mba_migrar_raw_para_bronze.py", bucket])
    etapa("[3/11] Recriando dados locais", [
        sys.executable, "mba_gerar_bases.py", str(quantidade)], cwd=DATA_DIR)
    etapa("[4/11] Ingerindo arquivos em Transient e Bronze", [
        sys.executable, "datalake/mba_ingestao_env.py", bucket,
        "--ingest-date", ingest_date, "--batch-id", batch_id])
    etapa("[5/11] Verificando/configurando OutputLocation", [
        sys.executable, "datalake/mba_configurar_output_athena.py", bucket])
    etapa("[6/11] Criando catálogo Bronze e sincronizando partições", [
        sys.executable, "datalake/mba_setup_athena.py", bucket])
    etapa("[7/11] Executando validação remota detalhada", [
        sys.executable, "mba_teste_remoto_ambiente.py", bucket])

    # NOVAS CAMADAS (INTEGRADAS)
    etapa("[8/11] Aplicando DQ e publicando quarentena", [
        sys.executable, "mba_processar_silver.py", "--bucket", bucket,
        "--ingest-date", ingest_date, "--batch-id", batch_id])
    etapa("[9/11] Materializando Silver em Parquet", [
        sys.executable, "mba_materializar_silver_athena.py", bucket,
        "--ingest-date", ingest_date, "--batch-id", batch_id])
    etapa("[10/11] Materializando Gold em Parquet", [
        sys.executable, "mba_processar_gold.py", bucket,
        "--ingest-date", ingest_date, "--batch-id", batch_id])
    etapa("[11/11] Executando auditoria final no Athena", [
        sys.executable, "mba_auditar_athena.py", bucket, ingest_date, batch_id])

    print("\nSETUP MBA CONCLUÍDO COM SUCESSO - TODAS AS CAMADAS INTEGRADAS")


def main():
    parser = argparse.ArgumentParser(description="Recriação segura do ambiente Data Lake")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--quantidade", type=int, default=100)
    args = parser.parse_args()
    if args.bucket != "datalake-bucket-turma-c-trabalho-mba":
        parser.error("este fluxo protege e aceita somente o bucket oficial do projeto")
    if args.quantidade <= 0:
        parser.error("--quantidade deve ser maior que zero")
    try:
        setup(args.bucket, args.quantidade)
    except (OSError, RuntimeError) as error:
        print(f"\nSETUP AMB FALHOU: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
