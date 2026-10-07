import unittest

from calculos import (
    _buscar_inflexao_continua,
    analisar_pontos_inflexao,
    calcular_valor_presente,
    comparar_alternativas,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
    gerar_dados_sensibilidade,
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

    def test_sensibilidade_recalcula_custos_para_todos_os_parametros(self):
        parametros = {
            "quantidade": 10,
            "preco": 80000,
            "manutencao": 5000,
            "seguro": 3000,
            "revenda": 30000,
            "aluguel": 2000,
            "anos": 5,
            "taxa": 0.10,
        }
        casos = {
            "preco": [40000, 80000, 120000],
            "aluguel": [1000, 2000, 3000],
            "manutencao": [2500, 5000, 7500],
            "seguro": [1500, 3000, 4500],
            "revenda": [15000, 30000, 45000],
            "taxa": [0.05, 0.10, 0.15],
            "anos": [4, 5, 6],
        }

        for parametro, valores in casos.items():
            with self.subTest(parametro=parametro):
                resultado = gerar_dados_sensibilidade(
                    parametro, parametros, valores
                )
                self.assertEqual(resultado["parametro"], parametro)
                self.assertEqual(resultado["valores"], valores)
                self.assertEqual(len(resultado["custos_compra"]), len(valores))
                self.assertEqual(len(resultado["custos_aluguel"]), len(valores))
                for indice, valor in enumerate(valores):
                    dados = parametros.copy()
                    dados[parametro] = valor
                    custo_compra = calcular_valor_presente(
                        gerar_fluxo_compra(
                            dados["quantidade"],
                            dados["preco"],
                            dados["manutencao"],
                            dados["seguro"],
                            dados["revenda"],
                            dados["anos"],
                        ),
                        dados["taxa"],
                    )
                    custo_aluguel = calcular_valor_presente(
                        gerar_fluxo_aluguel(
                            dados["quantidade"],
                            dados["aluguel"],
                            dados["anos"],
                        ),
                        dados["taxa"],
                    )
                    self.assertAlmostEqual(
                        resultado["custos_compra"][indice], custo_compra
                    )
                    self.assertAlmostEqual(
                        resultado["custos_aluguel"][indice], custo_aluguel
                    )

    def test_sensibilidade_generica_valida_parametro_e_anos_inteiros(self):
        parametros = {
            "quantidade": 10,
            "preco": 80000,
            "manutencao": 5000,
            "seguro": 3000,
            "revenda": 30000,
            "aluguel": 2000,
            "anos": 5,
            "taxa": 0.10,
        }
        for parametro, valores in (
            ("nao_existe", [1]),
            ("preco", [-1]),
            ("taxa", [float("nan")]),
            ("anos", [2.5]),
            ("anos", [0]),
        ):
            with self.subTest(parametro=parametro, valores=valores):
                with self.assertRaises(ValueError):
                    gerar_dados_sensibilidade(parametro, parametros, valores)

    def test_cenario_base_sem_inflacao_preserva_custos_atuais(self):
        fluxo_compra = gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5)
        fluxo_aluguel = gerar_fluxo_aluguel(10, 2000, 5)
        custo_compra = calcular_valor_presente(fluxo_compra, 0.10)
        custo_aluguel = calcular_valor_presente(fluxo_aluguel, 0.10)

        self.assertEqual(round(custo_compra, 2), 916986.54)
        self.assertEqual(round(custo_aluguel, 2), 909788.82)

    def test_inflacao_zero_preserva_fluxos_e_custos_sem_inflacao(self):
        compra_sem_inflacao = gerar_fluxo_compra(
            10, 80000, 5000, 3000, 30000, 5
        )
        aluguel_sem_inflacao = gerar_fluxo_aluguel(10, 2000, 5)

        self.assertEqual(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5, 0),
            compra_sem_inflacao,
        )
        self.assertEqual(
            gerar_fluxo_aluguel(10, 2000, 5, 0),
            aluguel_sem_inflacao,
        )
        self.assertEqual(
            calcular_valor_presente(compra_sem_inflacao, 0.10),
            calcular_valor_presente(
                gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5, 0),
                0.10,
            ),
        )

    def test_inflacao_reajusta_aluguel_manutencao_e_seguro_ano_a_ano(self):
        fluxo_aluguel = gerar_fluxo_aluguel(1, 2000, 3, 0.06)
        self.assertEqual(fluxo_aluguel[:3], [0, 24000, 25440])
        self.assertAlmostEqual(fluxo_aluguel[3], 26966.4)
        fluxo_manutencao = gerar_fluxo_compra(1, 0, 5000, 0, 0, 3, 0.06)
        fluxo_seguro = gerar_fluxo_compra(1, 0, 0, 3000, 0, 3, 0.06)
        self.assertEqual(fluxo_manutencao[:3], [0, 5000, 5300])
        self.assertAlmostEqual(fluxo_manutencao[3], 5618)
        self.assertEqual(fluxo_seguro[:3], [0, 3000, 3180])
        self.assertAlmostEqual(fluxo_seguro[3], 3370.8)

    def test_inflacao_nao_altera_preco_inicial_nem_valor_de_revenda(self):
        fluxo = gerar_fluxo_compra(2, 80000, 5000, 3000, 30000, 3, 0.06)
        fluxo_sem_revenda = gerar_fluxo_compra(2, 80000, 5000, 3000, 0, 3, 0.06)

        self.assertEqual(fluxo[0], 160000)
        self.assertEqual(
            fluxo_sem_revenda[-1] - fluxo[-1],
            2 * 30000,
        )

    def test_custos_futuros_aumentam_com_inflacao_positiva(self):
        custo_compra_sem = calcular_valor_presente(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5), 0.10
        )
        custo_compra_com = calcular_valor_presente(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5, 0.06),
            0.10,
        )
        custo_aluguel_sem = calcular_valor_presente(
            gerar_fluxo_aluguel(10, 2000, 5), 0.10
        )
        custo_aluguel_com = calcular_valor_presente(
            gerar_fluxo_aluguel(10, 2000, 5, 0.06), 0.10
        )

        self.assertGreater(custo_compra_com, custo_compra_sem)
        self.assertGreater(custo_aluguel_com, custo_aluguel_sem)

    def test_pontos_de_inflexao_usam_a_taxa_de_inflacao_informada(self):
        resultados = analisar_pontos_inflexao(
            10, 80000, 5000, 3000, 30000, 2000, 5, 0.10, 0.06
        )
        ponto_aluguel = next(
            item["ponto"]["ponto"]
            for item in resultados
            if item["parametro"] == "aluguel"
        )
        custo_compra = calcular_valor_presente(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5, 0.06),
            0.10,
        )
        custo_aluguel = calcular_valor_presente(
            gerar_fluxo_aluguel(10, ponto_aluguel, 5, 0.06),
            0.10,
        )
        self.assertAlmostEqual(custo_compra, custo_aluguel, places=5)

    def test_sensibilidade_preserva_inflacao_ativa_nos_demais_parametros(self):
        parametros = {
            "quantidade": 10,
            "preco": 80000,
            "manutencao": 5000,
            "seguro": 3000,
            "revenda": 30000,
            "aluguel": 2000,
            "anos": 5,
            "taxa": 0.10,
            "inflacao": 0.06,
        }
        dados = gerar_dados_sensibilidade("aluguel", parametros, [1000, 2000])
        esperado = calcular_valor_presente(
            gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5, 0.06),
            0.10,
        )
        self.assertEqual(dados["custos_compra"], [esperado, esperado])
        self.assertEqual(
            dados["custos_aluguel"],
            [
                calcular_valor_presente(
                    gerar_fluxo_aluguel(10, aluguel, 5, 0.06), 0.10
                )
                for aluguel in [1000, 2000]
            ],
        )

    def test_sensibilidade_da_inflacao_recalcula_compra_e_aluguel(self):
        parametros = {
            "quantidade": 10,
            "preco": 80000,
            "manutencao": 5000,
            "seguro": 3000,
            "revenda": 30000,
            "aluguel": 2000,
            "anos": 5,
            "taxa": 0.10,
            "inflacao": 0.06,
        }
        taxas = [0, 0.06, 0.09]
        dados = gerar_dados_sensibilidade("inflacao", parametros, taxas)

        self.assertIsNotNone(dados["ponto_inflexao"])
        for indice, inflacao in enumerate(taxas):
            self.assertAlmostEqual(
                dados["custos_compra"][indice],
                calcular_valor_presente(
                    gerar_fluxo_compra(
                        10, 80000, 5000, 3000, 30000, 5, inflacao
                    ),
                    0.10,
                ),
            )
            self.assertAlmostEqual(
                dados["custos_aluguel"][indice],
                calcular_valor_presente(
                    gerar_fluxo_aluguel(10, 2000, 5, inflacao), 0.10
                ),
            )
        self.assertAlmostEqual(
            dados["custos_compra"][0],
            calcular_valor_presente(
                gerar_fluxo_compra(10, 80000, 5000, 3000, 30000, 5),
                0.10,
            ),
        )
        self.assertAlmostEqual(
            dados["custos_aluguel"][0],
            calcular_valor_presente(gerar_fluxo_aluguel(10, 2000, 5), 0.10),
        )
        custo_compra_no_ponto = calcular_valor_presente(
            gerar_fluxo_compra(
                10, 80000, 5000, 3000, 30000, 5, dados["ponto_inflexao"]
            ),
            0.10,
        )
        custo_aluguel_no_ponto = calcular_valor_presente(
            gerar_fluxo_aluguel(10, 2000, 5, dados["ponto_inflexao"]),
            0.10,
        )
        self.assertAlmostEqual(custo_compra_no_ponto, custo_aluguel_no_ponto, places=5)

    def test_sensibilidade_rejeita_taxas_de_inflacao_negativas(self):
        parametros = {
            "quantidade": 1,
            "preco": 100,
            "manutencao": 1,
            "seguro": 1,
            "revenda": 0,
            "aluguel": 1,
            "anos": 1,
            "taxa": 0.1,
            "inflacao": 0,
        }
        with self.assertRaises(ValueError):
            gerar_dados_sensibilidade("inflacao", parametros, [-0.01])
        with self.assertRaises(ValueError):
            gerar_fluxo_compra(1, 100, 1, 1, 0, 1, -0.01)
        with self.assertRaises(ValueError):
            gerar_fluxo_aluguel(1, 1, 1, -0.01)


if __name__ == "__main__":
    unittest.main()