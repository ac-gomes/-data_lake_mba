import argparse
import os

import boto3
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


def ensure_output(bucket):
    expected = f"s3://{bucket}/athena-results/"
    athena = client()
    workgroup = athena.get_work_group(WorkGroup="primary")["WorkGroup"]
    actual = workgroup.get("Configuration", {}).get("ResultConfiguration", {}).get("OutputLocation")
    if actual == expected:
        print(f"OutputLocation preservado: {actual}")
        return
    athena.update_work_group(
        WorkGroup="primary",
        ConfigurationUpdates={"ResultConfigurationUpdates": {"OutputLocation": expected}},
    )
    print(f"OutputLocation configurado: {expected}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bucket")
    args = parser.parse_args()
    ensure_output(args.bucket)


if __name__ == "__main__":
    main()
