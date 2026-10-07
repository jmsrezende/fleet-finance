"""Calculos de valor presente para comparar custos de compra e aluguel."""

import math


def gerar_fluxo_compra(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    anos,
):
    """Retorna os custos de compra nos periodos 0 a anos."""
    fluxo = [quantidade_veiculos * preco_por_veiculo]

    for ano in range(1, anos + 1):
        custo_anual = quantidade_veiculos * (
            manutencao_anual_por_veiculo + seguro_anual_por_veiculo
        )
        if ano == anos:
            # A revenda reduz o desembolso liquido no ultimo periodo.
            custo_anual -= quantidade_veiculos * revenda_por_veiculo
        fluxo.append(custo_anual)

    return fluxo


def gerar_fluxo_aluguel(quantidade_veiculos, aluguel_mensal_por_veiculo, anos):
    """Anualiza o aluguel mensal e registra cada pagamento no fim do ano."""
    pagamento_anual = quantidade_veiculos * aluguel_mensal_por_veiculo * 12
    return [0] + [pagamento_anual] * anos


def calcular_valor_presente(fluxo, taxa_anual):
    """Desconta cada custo pelo numero do periodo anual em que ocorre."""
    return sum(valor / (1 + taxa_anual) ** periodo for periodo, valor in enumerate(fluxo))


def comparar_alternativas(custo_compra, custo_aluguel):
    """Compara os valores presentes dos custos e retorna decisao e diferenca."""
    if custo_compra < custo_aluguel:
        return "compra", custo_aluguel - custo_compra
    if custo_aluguel < custo_compra:
        return "aluguel", custo_compra - custo_aluguel
    return "empate", 0


def _diferenca_de_custos(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    aluguel_mensal_por_veiculo,
    anos,
    taxa_anual,
):
    fluxo_compra = gerar_fluxo_compra(
        quantidade_veiculos,
        preco_por_veiculo,
        manutencao_anual_por_veiculo,
        seguro_anual_por_veiculo,
        revenda_por_veiculo,
        anos,
    )
    fluxo_aluguel = gerar_fluxo_aluguel(
        quantidade_veiculos, aluguel_mensal_por_veiculo, anos
    )
    custo_compra = calcular_valor_presente(fluxo_compra, taxa_anual)
    custo_aluguel = calcular_valor_presente(fluxo_aluguel, taxa_anual)
    return custo_compra - custo_aluguel


def _encontrar_raiz_bissecao(funcao, esquerda, direita):
    valor_esquerda = funcao(esquerda)
    valor_direita = funcao(direita)
    if valor_esquerda * valor_direita >= 0:
        return None

    for _ in range(100):
        meio = (esquerda + direita) / 2
        valor_meio = funcao(meio)
        if abs(valor_meio) <= 1e-8 or meio in (esquerda, direita):
            return meio
        if valor_esquerda * valor_meio < 0:
            direita = meio
            valor_direita = valor_meio
        else:
            esquerda = meio
            valor_esquerda = valor_meio
    return (esquerda + direita) / 2


def _buscar_inflexao_continua(
    parametro,
    valor_atual,
    funcao_diferenca,
    limite_superior,
    amostras=10000,
):
    if parametro == "taxa":
        valores = [
            limite_superior * indice / amostras
            for indice in range(amostras + 1)
        ]
    else:
        # Os outros parâmetros alteram linearmente um dos fluxos de custos.
        valores = (0.0, limite_superior)

    candidatos = []
    valor_anterior = None
    diferenca_anterior = None
    pontos_iguais = []
    for valor in valores:
        diferenca = funcao_diferenca(valor)
        if abs(diferenca) <= 1e-8:
            pontos_iguais.append(valor)
            continue

        decisao = comparar_alternativas(diferenca, 0)[0]
        if diferenca_anterior is not None:
            decisao_anterior = comparar_alternativas(diferenca_anterior, 0)[0]
            if decisao_anterior != decisao:
                if pontos_iguais:
                    raiz = pontos_iguais[len(pontos_iguais) // 2]
                else:
                    raiz = _encontrar_raiz_bissecao(
                        funcao_diferenca, valor_anterior, valor
                    )
                if raiz is not None:
                    candidatos.append(
                        {
                            "ponto": raiz,
                            "abaixo": decisao_anterior,
                            "acima": decisao,
                        }
                    )
        valor_anterior = valor
        diferenca_anterior = diferenca
        pontos_iguais = []

    if not candidatos:
        return None
    return min(candidatos, key=lambda candidato: abs(candidato["ponto"] - valor_atual))


def _buscar_inflexao_anos(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    aluguel_mensal_por_veiculo,
    taxa_anual,
    anos_atuais,
    limite_anos=100,
):
    decisoes = {}
    for anos in range(1, limite_anos + 1):
        diferenca = _diferenca_de_custos(
            quantidade_veiculos,
            preco_por_veiculo,
            manutencao_anual_por_veiculo,
            seguro_anual_por_veiculo,
            revenda_por_veiculo,
            aluguel_mensal_por_veiculo,
            anos,
            taxa_anual,
        )
        escala = max(1, abs(diferenca))
        decisoes[anos] = (
            "empate"
            if abs(diferenca) <= escala * 1e-12
            else comparar_alternativas(diferenca, 0)[0]
        )

    transicoes = []
    ultimo_ano, ultima_decisao = None, None
    anos_empate = []
    for ano in range(1, limite_anos + 1):
        decisao = decisoes[ano]
        if decisao == "empate":
            anos_empate.append(ano)
            continue
        if ultima_decisao is not None and decisao != ultima_decisao:
            antes = anos_empate[0] if anos_empate else ultimo_ano
            depois = anos_empate[0] if anos_empate else ano
            transicoes.append(
                {
                    "ponto": anos_empate[0] if anos_empate else None,
                    "entre": (antes, depois),
                    "antes": ultima_decisao,
                    "depois": decisao,
                }
            )
        ultimo_ano, ultima_decisao = ano, decisao
        anos_empate = []

    if not transicoes:
        return None
    return min(
        transicoes,
        key=lambda transicao: min(
            abs(ano - anos_atuais) for ano in transicao["entre"]
        ),
    )


def analisar_pontos_inflexao(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    aluguel_mensal_por_veiculo,
    anos,
    taxa_anual,
):
    """Busca mudanças de decisão para cada parâmetro, mantendo os demais fixos."""
    parametros = (
        ("preco", preco_por_veiculo),
        ("aluguel", aluguel_mensal_por_veiculo),
        ("manutencao", manutencao_anual_por_veiculo),
        ("seguro", seguro_anual_por_veiculo),
        ("revenda", revenda_por_veiculo),
        ("taxa", taxa_anual),
    )
    resultados = []

    for parametro, valor_atual in parametros:
        def diferenca_com_valor(valor):
            valores = {
                "preco": preco_por_veiculo,
                "aluguel": aluguel_mensal_por_veiculo,
                "manutencao": manutencao_anual_por_veiculo,
                "seguro": seguro_anual_por_veiculo,
                "revenda": revenda_por_veiculo,
                "taxa": taxa_anual,
            }
            valores[parametro] = valor
            return _diferenca_de_custos(
                quantidade_veiculos,
                valores["preco"],
                valores["manutencao"],
                valores["seguro"],
                valores["revenda"],
                valores["aluguel"],
                anos,
                valores["taxa"],
            )

        limite_superior = (
            max(10.0, valor_atual * 2)
            if parametro == "taxa"
            else max(1_000_000.0, valor_atual * 10)
        )
        ponto = _buscar_inflexao_continua(
            parametro, valor_atual, diferenca_com_valor, limite_superior
        )
        resultados.append(
            {
                "parametro": parametro,
                "atual": valor_atual,
                "ponto": ponto,
                "intervalo": (0.0, limite_superior),
            }
        )

    transicao_anos = _buscar_inflexao_anos(
        quantidade_veiculos,
        preco_por_veiculo,
        manutencao_anual_por_veiculo,
        seguro_anual_por_veiculo,
        revenda_por_veiculo,
        aluguel_mensal_por_veiculo,
        taxa_anual,
        anos,
    )
    resultados.append(
        {
            "parametro": "anos",
            "atual": anos,
            "ponto": transicao_anos,
            "intervalo": (1, 100),
        }
    )
    return resultados


def gerar_dados_sensibilidade_aluguel(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    aluguel_mensal_por_veiculo,
    anos,
    taxa_anual,
    valores_aluguel,
):
    """Calcula os custos presentes para cada aluguel mensal fornecido."""
    valores = list(valores_aluguel)
    if not valores:
        raise ValueError("Informe pelo menos um valor de aluguel para analisar.")
    if any(
        not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        or valor < 0
        for valor in valores
    ):
        raise ValueError("Os valores de aluguel devem ser números finitos não negativos.")

    custos_compra = []
    custos_aluguel = []
    for valor_aluguel in valores:
        fluxo_compra = gerar_fluxo_compra(
            quantidade_veiculos,
            preco_por_veiculo,
            manutencao_anual_por_veiculo,
            seguro_anual_por_veiculo,
            revenda_por_veiculo,
            anos,
        )
        fluxo_aluguel = gerar_fluxo_aluguel(
            quantidade_veiculos, valor_aluguel, anos
        )
        custos_compra.append(calcular_valor_presente(fluxo_compra, taxa_anual))
        custos_aluguel.append(calcular_valor_presente(fluxo_aluguel, taxa_anual))

    def diferenca_com_aluguel(valor):
        return _diferenca_de_custos(
            quantidade_veiculos,
            preco_por_veiculo,
            manutencao_anual_por_veiculo,
            seguro_anual_por_veiculo,
            revenda_por_veiculo,
            valor,
            anos,
            taxa_anual,
        )

    limite_superior = max(1_000_000.0, aluguel_mensal_por_veiculo * 10)
    ponto = _buscar_inflexao_continua(
        "aluguel",
        aluguel_mensal_por_veiculo,
        diferenca_com_aluguel,
        limite_superior,
    )
    return {
        "valores_aluguel": valores,
        "custos_compra": custos_compra,
        "custos_aluguel": custos_aluguel,
        "ponto_inflexao": ponto["ponto"] if ponto is not None else None,
    }