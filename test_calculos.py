import unittest

from calculos import (
    _buscar_inflexao_continua,
    analisar_pontos_inflexao,
    calcular_valor_presente,
    comparar_alternativas,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
    gerar_dados_sensibilidade_aluguel,
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

    def analisar_caso_padrao(self):
        return analisar_pontos_inflexao(
            10, 80000, 5000, 3000, 30000, 2000, 5, 0.10
        )

    def diferenca_de_custos(
        self,
        preco=80000,
        aluguel=2000,
        manutencao=5000,
        seguro=3000,
        revenda=30000,
        anos=5,
        taxa=0.10,
    ):
        fluxo_compra = gerar_fluxo_compra(
            10, preco, manutencao, seguro, revenda, anos
        )
        fluxo_aluguel = gerar_fluxo_aluguel(10, aluguel, anos)
        return (
            calcular_valor_presente(fluxo_compra, taxa)
            - calcular_valor_presente(fluxo_aluguel, taxa)
        )

    def test_ponto_de_compra_iguala_custos_e_muda_a_decisao(self):
        resultado = next(
            item for item in self.analisar_caso_padrao()
            if item["parametro"] == "preco"
        )
        ponto = resultado["ponto"]["ponto"]

        self.assertAlmostEqual(self.diferenca_de_custos(preco=ponto), 0, places=5)
        self.assertEqual(resultado["ponto"]["abaixo"], "compra")
        self.assertEqual(resultado["ponto"]["acima"], "aluguel")
        self.assertEqual(comparar_alternativas(
            self.diferenca_de_custos(preco=ponto - 1), 0
        )[0], "compra")
        self.assertEqual(comparar_alternativas(
            self.diferenca_de_custos(preco=ponto + 1), 0
        )[0], "aluguel")

    def test_ponto_de_aluguel_iguala_custos_e_muda_a_decisao(self):
        resultado = next(
            item for item in self.analisar_caso_padrao()
            if item["parametro"] == "aluguel"
        )
        ponto = resultado["ponto"]["ponto"]

        self.assertAlmostEqual(
            self.diferenca_de_custos(aluguel=ponto), 0, places=5
        )
        self.assertEqual(resultado["ponto"]["abaixo"], "aluguel")
        self.assertEqual(resultado["ponto"]["acima"], "compra")
        self.assertEqual(comparar_alternativas(
            self.diferenca_de_custos(aluguel=ponto - 1), 0
        )[0], "aluguel")
        self.assertEqual(comparar_alternativas(
            self.diferenca_de_custos(aluguel=ponto + 1), 0
        )[0], "compra")

    def test_ponto_de_taxa_iguala_custos_e_muda_a_decisao(self):
        resultado = next(
            item for item in self.analisar_caso_padrao()
            if item["parametro"] == "taxa"
        )
        ponto = resultado["ponto"]["ponto"]

        self.assertAlmostEqual(
            self.diferenca_de_custos(taxa=ponto), 0, places=5
        )
        self.assertEqual(resultado["ponto"]["abaixo"], "compra")
        self.assertEqual(resultado["ponto"]["acima"], "aluguel")

    def test_pontos_continuos_sao_encontrados_para_todos_os_parametros(self):
        argumentos = {
            "preco": "preco",
            "aluguel": "aluguel",
            "manutencao": "manutencao",
            "seguro": "seguro",
            "revenda": "revenda",
            "taxa": "taxa",
        }
        for item in self.analisar_caso_padrao():
            parametro = item["parametro"]
            if parametro == "anos":
                continue
            with self.subTest(parametro=parametro):
                self.assertIsNotNone(item["ponto"])
                ponto = item["ponto"]["ponto"]
                chave_argumento = argumentos[parametro]
                self.assertAlmostEqual(
                    self.diferenca_de_custos(
                        **{chave_argumento: ponto}
                    ),
                    0,
                    places=5,
                )
                epsilon = 1e-6 if parametro == "taxa" else 0.01
                decisao_abaixo = comparar_alternativas(
                    self.diferenca_de_custos(
                        **{chave_argumento: ponto - epsilon}
                    ),
                    0,
                )[0]
                decisao_acima = comparar_alternativas(
                    self.diferenca_de_custos(
                        **{chave_argumento: ponto + epsilon}
                    ),
                    0,
                )[0]
                self.assertEqual(decisao_abaixo, item["ponto"]["abaixo"])
                self.assertEqual(decisao_acima, item["ponto"]["acima"])
                self.assertNotEqual(decisao_abaixo, decisao_acima)

    def test_taxa_sem_mudanca_retorna_ausencia_de_ponto(self):
        resultados = analisar_pontos_inflexao(
            1, 100_000_000, 0, 0, 0, 0, 5, 0.10
        )
        resultado_taxa = next(
            item for item in resultados if item["parametro"] == "taxa"
        )

        self.assertIsNone(resultado_taxa["ponto"])
        self.assertEqual(resultado_taxa["intervalo"], (0.0, 10.0))

    def test_busca_de_taxa_nao_presume_uma_unica_raiz(self):
        resultado = _buscar_inflexao_continua(
            "taxa", 3.6, lambda taxa: (taxa - 2) * (taxa - 4), 6, amostras=100
        )

        self.assertAlmostEqual(resultado["ponto"], 4)
        self.assertEqual(resultado["abaixo"], "compra")
        self.assertEqual(resultado["acima"], "aluguel")

    def test_anos_reporta_transicao_discreta_e_alternativa_de_cada_lado(self):
        resultado = next(
            item for item in self.analisar_caso_padrao()
            if item["parametro"] == "anos"
        )
        transicao = resultado["ponto"]
        antes, depois = transicao["entre"]

        self.assertIsNone(transicao["ponto"])
        self.assertEqual(depois, antes + 1)
        self.assertEqual(
            transicao["antes"],
            comparar_alternativas(self.diferenca_de_custos(anos=antes), 0)[0],
        )
        self.assertEqual(
            transicao["depois"],
            comparar_alternativas(self.diferenca_de_custos(anos=depois), 0)[0],
        )
        self.assertNotEqual(transicao["antes"], transicao["depois"])

    def test_sensibilidade_de_aluguel_recalcula_custos_e_preserva_demais_dados(self):
        dados = gerar_dados_sensibilidade_aluguel(
            10, 80000, 5000, 3000, 30000, 2000, 5, 0.10, [1000, 2000, 3000]
        )

        self.assertEqual(dados["valores_aluguel"], [1000, 2000, 3000])
        custo_compra_esperado = calcular_valor_presente(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5), 0.10
        )
        self.assertEqual(dados["custos_compra"], [custo_compra_esperado] * 3)
        for indice, aluguel in enumerate((1000, 2000, 3000)):
            custo_aluguel_esperado = calcular_valor_presente(
                gerar_fluxo_aluguel(10, aluguel, 5), 0.10
            )
            self.assertAlmostEqual(
                dados["custos_aluguel"][indice], custo_aluguel_esperado
            )
        self.assertAlmostEqual(dados["ponto_inflexao"], 2015.8228366447543)

    def test_sensibilidade_rejeita_valores_de_aluguel_invalidos(self):
        for valores in ([], [-1], [float("nan")], [float("inf")]):
            with self.subTest(valores=valores):
                with self.assertRaises(ValueError):
                    gerar_dados_sensibilidade_aluguel(
                        10, 80000, 5000, 3000, 30000, 2000, 5, 0.10, valores
                    )

    def test_sensibilidade_sem_ponto_de_inflexao_retorna_none(self):
        dados = gerar_dados_sensibilidade_aluguel(
            1, 1_000_000_000_000, 0, 0, 0, 0, 5, 0.10, [0, 1]
        )

        self.assertIsNone(dados["ponto_inflexao"])
        self.assertEqual(
            dados["custos_aluguel"],
            [
                calcular_valor_presente(gerar_fluxo_aluguel(1, aluguel, 5), 0.10)
                for aluguel in (0, 1)
            ],
        )


if __name__ == "__main__":
    unittest.main()