import csv
import random
import sys


produtos = [
    ("Notebook", "Informatica", 2500.00, 8500.00),
    ("Teclado", "Informatica", 50.00, 450.00),
    ("Mouse", "Informatica", 30.00, 300.00),
    ("Monitor", "Informatica", 500.00, 3500.00),
    ("Webcam", "Informatica", 100.00, 800.00),
    ("Headset", "Informatica", 80.00, 600.00),
    ("Impressora", "Informatica", 500.00, 2500.00),
    ("Tablet", "Eletronicos", 500.00, 4000.00),
    ("Smartphone", "Eletronicos", 800.00, 8000.00),
    ("Smartwatch", "Eletronicos", 300.00, 2500.00),
    ("Fone de Ouvido", "Eletronicos", 50.00, 1500.00),
    ("Camera", "Eletronicos", 800.00, 6000.00),
    ("Televisao", "Eletronicos", 1500.00, 10000.00),
    ("Caixa de Som", "Eletronicos", 100.00, 2000.00),
    ("Geladeira", "Eletrodomesticos", 2500.00, 9000.00),
    ("Fogao", "Eletrodomesticos", 800.00, 4000.00),
    ("Microondas", "Eletrodomesticos", 400.00, 2500.00),
    ("Air Fryer", "Eletrodomesticos", 300.00, 1200.00),
    ("Liquidificador", "Eletrodomesticos", 100.00, 700.00),
    ("Aspirador de Po", "Eletrodomesticos", 200.00, 1800.00),
    ("Sofa", "Moveis", 800.00, 6000.00),
    ("Mesa", "Moveis", 300.00, 3000.00),
    ("Cadeira", "Moveis", 150.00, 1500.00),
    ("Estante", "Moveis", 300.00, 2500.00),
    ("Guarda Roupa", "Moveis", 800.00, 5000.00),
    ("Cama", "Moveis", 500.00, 5000.00),
    ("Colchao", "Moveis", 600.00, 4000.00),
    ("Armario", "Moveis", 400.00, 3500.00),
    ("Camisa", "Vestuario", 50.00, 300.00),
    ("Calca Jeans", "Vestuario", 100.00, 500.00),
    ("Tenis", "Vestuario", 150.00, 1200.00),
    ("Jaqueta", "Vestuario", 150.00, 1000.00),
    ("Vestido", "Vestuario", 100.00, 800.00),
    ("Mochila", "Acessorios", 80.00, 600.00),
    ("Carteira", "Acessorios", 30.00, 300.00),
    ("Oculos de Sol", "Acessorios", 50.00, 1000.00),
    ("Relogio", "Acessorios", 100.00, 3000.00),
    ("Livro", "Livros", 20.00, 200.00),
    ("Caderno", "Papelaria", 10.00, 100.00),
    ("Caneta", "Papelaria", 2.00, 30.00),
    ("Mochila Escolar", "Papelaria", 50.00, 400.00),
    ("Cafeteira", "Cozinha", 100.00, 1500.00),
    ("Panela", "Cozinha", 50.00, 800.00),
    ("Jogo de Pratos", "Cozinha", 80.00, 600.00),
    ("Liquidificador", "Cozinha", 100.00, 700.00),
]


def gerar_produtos(quantidade, arquivo="produtos.csv"):

    with open(
        arquivo,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        escritor = csv.writer(f)

        # Cabeçalho
        escritor.writerow([
            "produto_id",
            "nome",
            "categoria",
            "preco"
        ])

        for i in range(quantidade):

            nome, categoria, preco_min, preco_max = random.choice(produtos)

            preco = round(
                random.uniform(preco_min, preco_max),
                2
            )

            produto_id = 9001 + i

            escritor.writerow([
                produto_id,
                nome,
                categoria,
                preco
            ])

    print(f"{quantidade} produtos gerados com sucesso!")
    print(f"Arquivo: {arquivo}")


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Uso:")
        print("python gerar_produtos.py <quantidade>")
        print()
        print("Exemplo:")
        print("python gerar_produtos.py 1000")

        sys.exit(1)

    quantidade = int(sys.argv[1])

    arquivo = "produtos.csv"

    if len(sys.argv) >= 3:
        arquivo = sys.argv[2]

    gerar_produtos(quantidade, arquivo)
