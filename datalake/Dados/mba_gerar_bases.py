import argparse
import subprocess
import sys
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent
PROGRAMAS = (
    "mba_base_clientes.py",
    "mba_base_order.py",
    "mba_base_produtos.py",
    "mba_base_pedidos.py",
)


def gerar_dados(quantidade):
    for programa in PROGRAMAS:
        resultado = subprocess.run([sys.executable, programa, str(quantidade)], cwd=DATA_DIR)
        if resultado.returncode != 0:
            raise RuntimeError(f"Falha ao gerar dados com {programa}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("quantidade", type=int)
    args = parser.parse_args()
    if args.quantidade <= 0:
        parser.error("a quantidade deve ser maior que zero")
    gerar_dados(args.quantidade)


if __name__ == "__main__":
    main()
