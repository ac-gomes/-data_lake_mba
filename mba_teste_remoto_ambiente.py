import argparse
import os
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")


def clients():
    credentials = {
        "region_name": os.environ["AWS_REGION"],
        "aws_access_key_id": os.environ["AWS_ACCESS_KEY_ID"],
        "aws_secret_access_key": os.environ["AWS_SECRET_ACCESS_KEY"],
        "aws_session_token": os.getenv("AWS_SESSION_TOKEN"),
    }
    return (boto3.client("s3", **credentials),
            boto3.client("athena", **credentials),
            boto3.client("glue", **credentials))


def run_check(label, function):
    try:
        details = function()
        print(f"PASS {label}")
        for detail in details or ():
            print(f"     {detail}")
        return True
    except (ClientError, BotoCoreError) as error:
        code = error.response.get("Error", {}).get("Code", "AWS_ERROR")
        print(f"BLOCKED {label}: {code}")
    except AssertionError as error:
        print(f"FAIL {label}: {error}")
    return False


def test_environment(bucket):
    s3, athena, glue = clients()
    checks = []

    def bucket_check():
        s3.head_bucket(Bucket=bucket)
        location = s3.get_bucket_location(Bucket=bucket).get("LocationConstraint") or "us-east-1"
        return [f"bucket: {bucket}", f"região: {location}"]

    def folders_check():
        folders = (
            "transient/", "transient/clientes/", "transient/pedidos/", "transient/produtos/",
            "bronze/", "bronze/clientes/", "bronze/pedidos/", "bronze/produtos/",
            "silver/fato_vendas/", "gold/analises_vendas/", "quarantine/", "logs/",
        )
        for folder in folders:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=folder, MaxKeys=1)
            assert response.get("KeyCount", 0), f"pasta ausente ou vazia: {folder}"
        return [f"pasta: {folder}" for folder in folders]

    def files_check():
        expected = (("bronze/clientes/", "clientes.json"), ("bronze/pedidos/", "pedidos.csv"),
                    ("bronze/produtos/", "produtos.csv"))
        found = []
        for folder, filename in expected:
            response = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
            stem = filename.rsplit(".", 1)[0]
            matches = [
                item for item in response.get("Contents", [])
                if item["Key"].rsplit("/", 1)[-1] == filename
                or item["Key"].rsplit("/", 1)[-1].startswith(stem + "_")
            ]
            assert matches, f"arquivo ausente: {folder}{filename}"
            found.extend(f"arquivo: s3://{bucket}/{item['Key']} ({item['Size']} bytes)" for item in matches)
        return found

    output = f"s3://{bucket}/athena-results/"

    def athena_check():
        workgroup = athena.get_work_group(WorkGroup="primary")["WorkGroup"]
        actual = workgroup.get("Configuration", {}).get("ResultConfiguration", {}).get("OutputLocation")
        assert actual == output, f"OutputLocation={actual!r}, esperado={output!r}"
        return [f"workgroup: {workgroup['Name']}", f"OutputLocation: {actual}"]

    def results_check():
        response = s3.list_objects_v2(Bucket=bucket, Prefix="athena-results/", MaxKeys=10)
        assert response.get("KeyCount", 0), "athena-results/ ausente ou vazio"
        return [f"resultado: s3://{bucket}/{item['Key']} ({item['Size']} bytes)" for item in response.get("Contents", [])]

    database = f"catalog_db_athena_{bucket.replace('datalake-', '').replace('-', '_')}"

    def catalog_check():
        glue.get_database(Name=database)
        expected_tables = {"bronze_clientes", "bronze_pedidos", "bronze_produtos"}
        tables = set()
        for page in glue.get_paginator("get_tables").paginate(DatabaseName=database):
            tables.update(table["Name"] for table in page.get("TableList", []))
        missing = expected_tables - tables
        assert not missing, f"tabelas ausentes: {sorted(missing)}"
        return [f"catálogo: {database}", f"tabelas: {', '.join(sorted(expected_tables))}"]

    checks.extend((("R01 bucket existe", bucket_check), ("R02 pastas existem", folders_check),
                   ("R03 arquivos existem", files_check), ("R04 Athena configurado", athena_check),
                   ("R05 catálogo e tabelas Athena", catalog_check),
                   ("R06 path de resultados do Athena existe", results_check)))
    results = [run_check(label, function) for label, function in checks]
    print(f"Resultado: {sum(results)}/{len(results)} verificações aprovadas")
    return 0 if all(results) else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    args = parser.parse_args()
    try:
        return test_environment(args.bucket)
    except (KeyError, RuntimeError) as error:
        print(f"BLOCKED R01: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
