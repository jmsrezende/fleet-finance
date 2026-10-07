"""
Captura de indicadores econômicos na API pública SGS do Banco Central.
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
SERIE_SELIC_META = 432  # Meta Selic em % ao ano
SERIE_IPCA_MENSAL = 433  # Variação mensal do IPCA em % ao mês


class ErroDadosExternos(Exception):
    """Falha ao obter dados do Banco Central (rede, servidor ou formato)."""


def _buscar_serie(codigo, n):
    """
    Baixa as últimas n observações de uma série do SGS.
    Formato [{"data": "DD/MM/AAAA", "valor": "0.58"}, ...].
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
        # Converte erros técnicos variados em um único tipo de erro do domínio
        # assim a interface não precisa conhecer detalhes de rede.
        raise ErroDadosExternos(f"Não foi possível acessar o SGS: {erro}") from erro

    if not isinstance(dados, list) or not dados:
        raise ErroDadosExternos(f"A série {codigo} não retornou valores.")
    return dados


def buscar_selic():
    """
    Retorna (taxa Selic em % ao ano, data de referência).
    """
    ultimo = _buscar_serie(SERIE_SELIC_META, 1)[-1]
    try:
        return float(ultimo["valor"]), ultimo["data"]
    except (KeyError, ValueError, TypeError) as erro:
        raise ErroDadosExternos("Resposta da Selic em formato inesperado.") from erro


def buscar_ipca_12_meses():
    """
    Retorna (IPCA acumulado nos últimos 12 meses em %, data do último mês).
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