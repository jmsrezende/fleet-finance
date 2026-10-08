"""Testes da geração do relatório financeiro em PDF."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import calculos
from relatorio import gerar_relatorio_pdf


class TestRelatorioPdf(unittest.TestCase):
    def setUp(self):
        self.pasta_temporaria = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta_temporaria.cleanup)
        self.caminho_pdf = Path(self.pasta_temporaria.name) / "relatorio.pdf"
        self.dados = {
            "quantidade": 4,
            "preco": 65_000,
            "manutencao": 4_200,
            "seguro": 2_500,
            "revenda": 22_000,
            "aluguel": 1_850,
            "anos": 4,
            "taxa": 0.08,
            "inflacao": 0.04,
        }

    def gerar(self, inflacao, origem=None, parametro="aluguel"):
        return gerar_relatorio_pdf(
            self.dados,
            considerando_inflacao=inflacao,
            origem_dados=origem,
            parametro_sensibilidade=parametro,
            caminho_saida=self.caminho_pdf,
        )

    def assertPdfContains(self, conteudo, texto):
        self.assertTrue(texto in conteudo, f"PDF não contém {texto!r}.")

    def test_gera_pdf_valido_com_inflacao_desabilitada_e_dados_manualmente(self):
        caminho = self.gerar(
            False,
            {
                "selic": {"fonte": "manual", "fallback": True},
                "ipca": {"fonte": "manual"},
            },
        )

        conteudo = caminho.read_bytes()
        self.assertTrue(caminho.is_file())
        self.assertGreater(caminho.stat().st_size, 5_000)
        self.assertTrue(conteudo.startswith(b"%PDF-"))
        self.assertPdfContains(conteudo, b"Dados de entrada")
        self.assertPdfContains(conteudo, b"Metodologia")
        self.assertPdfContains(conteudo, b"Resultado principal")
        self.assertPdfContains(conteudo, b"pontos")
        self.assertPdfContains(conteudo, b"sensibilidade")
        self.assertPdfContains(conteudo, b"Premissas e limita")
        self.assertPdfContains(conteudo, b"fallback")
        self.assertPdfContains(conteudo, b"/Subtype /Image")

    def test_gera_pdf_com_inflacao_habilitada_e_fontes_do_banco_central(self):
        caminho = self.gerar(
            True,
            {
                "selic": {"fonte": "bcb", "data": "07/10/2026"},
                "ipca": {"fonte": "bcb", "data": "30/09/2026"},
            },
            parametro="inflacao",
        )

        conteudo = caminho.read_bytes()
        self.assertTrue(caminho.is_file())
        self.assertPdfContains(conteudo, b"07/10/2026")
        self.assertPdfContains(conteudo, b"30/09/2026")
        self.assertPdfContains(conteudo, b"API do Banco Central")
        self.assertPdfContains(conteudo, b"Taxa de infla")

    def test_dados_da_tela_sao_passados_aos_calculos_existentes(self):
        with patch("relatorio.analisar_pontos_inflexao", return_value=[]) as pontos:
            self.gerar(True)

        pontos.assert_called_once_with(
            4,
            65_000,
            4_200,
            2_500,
            22_000,
            1_850,
            4,
            0.08,
            0.04,
        )

    def test_inflacao_desabilitada_nao_e_aplicada_aos_fluxos_ou_inflexoes(self):
        with (
            patch("relatorio.analisar_pontos_inflexao", return_value=[]) as pontos,
            patch(
                "relatorio.gerar_fluxo_compra",
                wraps=calculos.gerar_fluxo_compra,
            ) as fluxo_compra,
            patch(
                "relatorio.gerar_fluxo_aluguel",
                wraps=calculos.gerar_fluxo_aluguel,
            ) as fluxo_aluguel,
        ):
            self.gerar(False)

        self.assertEqual(fluxo_compra.call_args.args[-1], 0)
        self.assertEqual(fluxo_aluguel.call_args.args[-1], 0)
        self.assertEqual(pontos.call_args.args[-1], 0)

    def test_ausencia_de_dados_externos_nao_impede_a_geracao(self):
        caminho = self.gerar(True, origem=None)
        conteudo = caminho.read_bytes()

        self.assertTrue(caminho.is_file())
        self.assertPdfContains(conteudo, b"Informado manualmente")
        self.assertPdfContains(conteudo, b"Dados externos e origem")

    def test_rejeita_dados_insuficientes_antes_de_criar_o_pdf(self):
        with self.assertRaisesRegex(ValueError, "Dados insuficientes"):
            gerar_relatorio_pdf(
                {"quantidade": 2},
                considerando_inflacao=False,
                caminho_saida=self.caminho_pdf,
            )

        self.assertFalse(self.caminho_pdf.exists())


if __name__ == "__main__":
    unittest.main()
