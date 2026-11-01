import unittest

from mba_processar_silver import avaliar_registro


class TestDataQuality(unittest.TestCase):
    def test_quantidade_invalida(self):
        registro = {
            "pedido_id": 1,
            "cliente_id": 505,
            "produto_id": 9001,
            "quantidade": 0,
            "valor": 10.0,
            "data_pedido": "2026-08-31",
        }
        clientes = {505: {"nome": "Cliente A", "cidade": "São Paulo", "estado": "SP"}}
        produtos = {9001: {"nome": "Produto A", "categoria": "Eletronicos", "preco": 100.0}}

        motivos, valido = avaliar_registro(registro, clientes, produtos)

        self.assertFalse(valido)
        self.assertIn("quantidade_invalida", motivos)

    def test_cliente_inexistente(self):
        registro = {
            "pedido_id": 2,
            "cliente_id": 99999,
            "produto_id": 9001,
            "quantidade": 2,
            "valor": 10.0,
            "data_pedido": "2026-08-31",
        }
        clientes = {505: {"nome": "Cliente A", "cidade": "São Paulo", "estado": "SP"}}
        produtos = {9001: {"nome": "Produto A", "categoria": "Eletronicos", "preco": 100.0}}

        motivos, valido = avaliar_registro(registro, clientes, produtos)

        self.assertFalse(valido)
        self.assertIn("cliente_inexistente", motivos)

    def test_registro_valido(self):
        registro = {
            "pedido_id": 3,
            "cliente_id": 505,
            "produto_id": 9001,
            "quantidade": 2,
            "valor": 10.0,
            "data_pedido": "2026-08-31",
        }
        clientes = {505: {"nome": "Cliente A", "cidade": "São Paulo", "estado": "SP"}}
        produtos = {9001: {"nome": "Produto A", "categoria": "Eletronicos", "preco": 100.0}}

        motivos, valido = avaliar_registro(registro, clientes, produtos)

        self.assertTrue(valido)
        self.assertEqual(motivos, [])


if __name__ == "__main__":
    unittest.main()
