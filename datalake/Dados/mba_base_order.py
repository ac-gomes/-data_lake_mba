import csv
import random
import sys
from datetime import datetime, timedelta


# ==========================================
# CONFIGURAÇÕES
# ==========================================

CLIENTE_MIN = 1
CLIENTE_MAX = 50

PRODUTO_MIN = 1000
PRODUTO_MAX = 1050

QUANTIDADE_MIN = 1
QUANTIDADE_MAX = 10

PRECO_MIN = 5.00
PRECO_MAX = 50.00

STATUS = [
    "Shipped",
    "Cancelled",
    "Pending",
    "Delivered"
]


# ==========================================
# GERAR DATA ALEATÓRIA
# ==========================================

def gerar_data():

    inicio = datetime(2023, 1, 1)
    fim = datetime(2023, 12, 31)

    dias = (fim - inicio).days

    data = inicio + timedelta(
        days=random.randint(0, dias)
    )

    return data.strftime("%m/%d/%Y")


# ==========================================
# GERAR PEDIDOS
# ==========================================

def gerar_orders(quantidade, arquivo="orders.csv"):

    with open(
        arquivo,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        escritor = csv.writer(f)

        # Cabeçalho
        escritor.writerow([
            "order_id",
            "data",
            "cliente_id",
            "produto_id",
            "quantidade",
            "preco_unitario",
            "valor_total",
            "status"
        ])

        for i in range(quantidade):

            order_id = i + 1

            data = gerar_data()

            cliente_id = random.randint(
                CLIENTE_MIN,
                CLIENTE_MAX
            )

            produto_id = random.randint(
                PRODUTO_MIN,
                PRODUTO_MAX
            )

            quantidade_produto = random.randint(
                QUANTIDADE_MIN,
                QUANTIDADE_MAX
            )

            preco_unitario = round(
                random.uniform(
                    PRECO_MIN,
                    PRECO_MAX
                ),
                2
            )

            valor_total = round(
                quantidade_produto * preco_unitario,
                2
            )

            status = random.choice(STATUS)

            escritor.writerow([
                order_id,
                data,
                cliente_id,
                produto_id,
                quantidade_produto,
                preco_unitario,
                valor_total,
                status
            ])

    print()
    print("==========================================")
    print("       GERADOR DE ORDERS")
    print("==========================================")
    print(f"Registros gerados : {quantidade}")
    print(f"Arquivo           : {arquivo}")
    print("==========================================")


# ==========================================
# PROGRAMA PRINCIPAL
# ==========================================

if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Uso:")
        print("  python gerar_orders.py <quantidade>")
        print()
        print("Exemplos:")
        print("  python gerar_orders.py 200")
        print("  python gerar_orders.py 1000")
        print("  python gerar_orders.py 100000 orders.csv")

        sys.exit(1)

    quantidade = int(sys.argv[1])

    arquivo = "orders.csv"

    if len(sys.argv) >= 3:
        arquivo = sys.argv[2]

    gerar_orders(
        quantidade,
        arquivo
    )
