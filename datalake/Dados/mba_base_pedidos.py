import csv
import random
import sys
from datetime import date, timedelta


def gerar_pedidos(quantidade, arquivo="pedidos.csv"):

    data_inicial = date(2026, 1, 1)

    with open(
        arquivo,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        escritor = csv.writer(f)

        # Cabeçalho
        escritor.writerow([
            "pedido_id",
            "cliente_id",
            "produto_id",
            "quantidade",
            "valor",
            "data_pedido"
        ])

        for i in range(quantidade):

            pedido_id = 1001 + i

            if i == 0:
                cliente_id = 505
                produto_id = 9001
            else:
                cliente_id = random.randint(501, 1500)
                produto_id = random.randint(9001, 10000)

            # Quantidade comprada
            quantidade_produto = random.randint(1, 10)

            # Preço unitário fictício
            preco_unitario = round(
                random.uniform(10.0, 5000.0),
                2
            )

            # Valor total do pedido
            valor = round(
                quantidade_produto * preco_unitario,
                2
            )

            # Data aleatória em 2026
            data_pedido = data_inicial + timedelta(
                days=random.randint(0, 364)
            )

            escritor.writerow([
                pedido_id,
                cliente_id,
                produto_id,
                quantidade_produto,
                valor,
                data_pedido.isoformat()
            ])

    print("======================================")
    print("      GERADOR DE PEDIDOS")
    print("======================================")
    print(f"Registros gerados: {quantidade}")
    print(f"Arquivo: {arquivo}")
    print(f"ID inicial: 1001")
    print(f"ID final: {1000 + quantidade}")
    print("======================================")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python gerar_pedidos.py <quantidade>")
        print()
        print("Exemplos:")
        print("  python gerar_pedidos.py 100")
        print("  python gerar_pedidos.py 1000")
        print("  python gerar_pedidos.py 100000 pedidos.csv")
        sys.exit(1)

    quantidade = int(sys.argv[1])

    arquivo = "pedidos.csv"

    if len(sys.argv) >= 3:
        arquivo = sys.argv[2]

    gerar_pedidos(quantidade, arquivo)
