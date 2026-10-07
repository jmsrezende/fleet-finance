import unittest

from calculos import (
    calcular_valor_presente,
    comparar_alternativas,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
)


class TestCalculosFinanceiros(unittest.TestCase):
    def test_valor_presente_com_periodo_zero_e_um(self):
        self.assertAlmostEqual(calcular_valor_presente([100, 110], 0.10), 200)

    def test_fluxo_de_compra_inclui_compra_custos_e_revenda(self):
        fluxo = gerar_fluxo_compra(2, 100, 10, 5, 30, 2)
        self.assertEqual(fluxo, [200, 30, -30])

    def test_fluxo_de_aluguel_anualiza_o_valor_mensal(self):
        self.assertEqual(gerar_fluxo_aluguel(2, 10, 2), [0, 240, 240])

    def test_comparacao_indica_menor_custo_presente(self):
        self.assertEqual(comparar_alternativas(90, 100), ("compra", 10))
        self.assertEqual(comparar_alternativas(100, 90), ("aluguel", 10))
        self.assertEqual(comparar_alternativas(100, 100), ("empate", 0))


if __name__ == "__main__":
    unittest.main()