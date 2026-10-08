"""Consulta indicadores econômicos na API pública SGS do Banco Central.

As funções preservam as datas de referência da Selic e do IPCA para que os
valores externos possam ser identificados nos resultados da aplicação.
"""

import http.client
import json
import urllib.request

# Endereço da API: {codigo} identifica a série; {n} é quantas observações
# recentes buscar (o SGS aceita no máximo 20).
URL_SGS = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}"
    "/dados/ultimos/{n}?formato=json"
)
# A série 432 fornece a Meta Selic anual, utilizada como taxa de desconto.
SERIE_SELIC_META = 432  # Meta Selic em % ao ano
# A série 433 fornece as variações mensais acumuladas para estimar 12 meses.
SERIE_IPCA_MENSAL = 433  # Variação mensal do IPCA em % ao mês


class ErroDadosExternos(Exception):
    """Falha ao obter dados do Banco Central (rede, servidor ou formato)."""


def _buscar_serie(codigo, n):
    """
    Baixa observações da API SGS e preserva cada valor com sua data.

    A resposta contém itens como ``{"data": "DD/MM/AAAA", "valor": "0.58"}``.
    Falhas de conexão, HTTP, decodificação e JSON, assim como respostas vazias,
    são convertidas em ``ErroDadosExternos`` para a interface tratar
    uniformemente sem descartar os valores digitados manualmente.
    """
    url = URL_SGS.format(codigo=codigo, n=n)
    try:
        with urllib.request.urlopen(url, timeout=10) as resposta:
            dados = json.load(resposta)
    except (
        OSError,  # inclui URLError, HTTPError e TimeoutError
        http.client.HTTPException,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as erro:
        # Uniformiza falhas de conexão, HTTP e conteúdo inválido para a interface.
        raise ErroDadosExternos(f"Não foi possível acessar o SGS: {erro}") from erro

    if not isinstance(dados, list) or not dados:
        raise ErroDadosExternos(f"A série {codigo} não retornou valores.")
    return dados


def buscar_selic():
    """
    Retorna (Meta Selic em % ao ano, data de referência da série 432).

    A data fornecida pelo Banco Central acompanha a taxa para registrar a
    observação utilizada no cenário.
    """
    ultimo = _buscar_serie(SERIE_SELIC_META, 1)[-1]
    try:
        return float(ultimo["valor"]), ultimo["data"]
    except (KeyError, ValueError, TypeError) as erro:
        raise ErroDadosExternos("Resposta da Selic em formato inesperado.") from erro


def buscar_ipca_12_meses():
    """
    Retorna (IPCA acumulado em 12 meses, data do último mês disponível).

    As variações mensais da série 433 são compostas multiplicativamente:
    fator = Π(1 + variação_mensal / 100); IPCA_12m = (fator - 1) × 100.
    O acumulado observado serve como estimativa informada para a inflação, não
    como garantia do comportamento futuro dos preços.
    """
    meses = _buscar_serie(SERIE_IPCA_MENSAL, 12)
    if len(meses) < 12:
        raise ErroDadosExternos("Não há 12 meses de dados do IPCA disponíveis.")

    try:
        fator_acumulado = 1.0
        for mes in meses:
            fator_acumulado *= 1 + float(mes["valor"]) / 100
        return (fator_acumulado - 1) * 100, meses[-1]["data"]
    except (KeyError, ValueError, TypeError) as erro:
        raise ErroDadosExternos("Resposta do IPCA em formato inesperado.") from erro