"""Calculos de valor presente para comparar custos de compra e aluguel."""

import math


def _validar_inflacao(inflacao_anual):
    if (
        not isinstance(inflacao_anual, (int, float))
        or not math.isfinite(inflacao_anual)
        or inflacao_anual < 0
    ):
        raise ValueError("A taxa de inflação anual deve ser finita e não negativa.")


def gerar_fluxo_compra(
    quantidade_veiculos,
    preco_por_veiculo,
    manutencao_anual_por_veiculo,
    seguro_anual_por_veiculo,
    revenda_por_veiculo,
    anos,
    inflacao_anual=0,
):
    """Retorna os custos de compra nos periodos 0 a anos."""
    _validar_inflacao(inflacao_anual)
    fluxo = [quantidade_veiculos * preco_por_veiculo]

    for ano in range(1, anos + 1):
        custo_anual = quantidade_veiculos * (
            manutencao_anual_por_veiculo + seguro_anual_por_veiculo
        ) * (1 + inflacao_anual) ** (ano - 1)
        if ano == anos:
            # A revenda reduz o desembolso liquido no ultimo periodo.
            custo_anual -= quantidade_veiculos * revenda_por_veiculo
        fluxo.append(custo_anual)

    return fluxo


def gerar_fluxo_aluguel(
    quantidade_veiculos,
    aluguel_mensal_por_veiculo,
    anos,
    inflacao_anual=0,
):
    """Anualiza o aluguel mensal e registra cada pagamento no fim do ano."""
    _validar_inflacao(inflacao_anual)
    pagamento_anual = quantidade_veiculos * aluguel_mensal_por_veiculo * 12
    return [0] + [
        pagamento_anual * (1 + inflacao_anual) ** (ano - 1)
        for ano in range(1, anos + 1)
    ]


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
    inflacao_anual=0,
):
    fluxo_compra = gerar_fluxo_compra(
        quantidade_veiculos,
        preco_por_veiculo,
        manutencao_anual_por_veiculo,
        seguro_anual_por_veiculo,
        revenda_por_veiculo,
        anos,
        inflacao_anual,
    )
    fluxo_aluguel = gerar_fluxo_aluguel(
        quantidade_veiculos,
        aluguel_mensal_por_veiculo,
        anos,
        inflacao_anual,
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
    if parametro in ("taxa", "inflacao"):
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
    inflacao_anual=0,
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
            inflacao_anual,
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
    inflacao_anual=0,
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
                inflacao_anual,
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
        inflacao_anual=inflacao_anual,
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


def gerar_dados_sensibilidade(parametro, parametros, valores):
    """Calcula os custos presentes ao variar um parâmetro por vez."""
    parametros_analisaveis = {
        "preco",
        "aluguel",
        "manutencao",
        "seguro",
        "revenda",
        "taxa",
        "anos",
        "inflacao",
    }
    if parametro not in parametros_analisaveis:
        raise ValueError(f"Parâmetro de sensibilidade desconhecido: {parametro}.")

    valores = list(valores)
    if not valores:
        raise ValueError("Informe pelo menos um valor para analisar.")
    if parametro == "anos":
        if any(
            not isinstance(valor, int) or isinstance(valor, bool) or valor < 1
            for valor in valores
        ):
            raise ValueError("Os anos devem ser números inteiros positivos.")
    elif any(
        not isinstance(valor, (int, float))
        or not math.isfinite(valor)
        or valor < 0
        for valor in valores
    ):
        raise ValueError("Os valores analisados devem ser finitos e não negativos.")

    dados = {
        "quantidade": parametros["quantidade"],
        "preco": parametros["preco"],
        "manutencao": parametros["manutencao"],
        "seguro": parametros["seguro"],
        "revenda": parametros["revenda"],
        "aluguel": parametros["aluguel"],
        "anos": parametros["anos"],
        "taxa": parametros["taxa"],
        "inflacao": parametros.get("inflacao", 0),
    }

    custos_compra = []
    custos_aluguel = []
    for valor in valores:
        dados_ponto = dados.copy()
        dados_ponto[parametro] = valor
        fluxo_compra = gerar_fluxo_compra(
            dados_ponto["quantidade"],
            dados_ponto["preco"],
            dados_ponto["manutencao"],
            dados_ponto["seguro"],
            dados_ponto["revenda"],
            dados_ponto["anos"],
            dados_ponto["inflacao"],
        )
        fluxo_aluguel = gerar_fluxo_aluguel(
            dados_ponto["quantidade"],
            dados_ponto["aluguel"],
            dados_ponto["anos"],
            dados_ponto["inflacao"],
        )
        custos_compra.append(
            calcular_valor_presente(fluxo_compra, dados_ponto["taxa"])
        )
        custos_aluguel.append(
            calcular_valor_presente(fluxo_aluguel, dados_ponto["taxa"])
        )

    if parametro == "anos":
        transicao = _buscar_inflexao_anos(
            dados["quantidade"],
            dados["preco"],
            dados["manutencao"],
            dados["seguro"],
            dados["revenda"],
            dados["aluguel"],
            dados["taxa"],
            dados["anos"],
            inflacao_anual=dados["inflacao"],
        )
        ponto_inflexao = transicao["ponto"] if transicao is not None else None
    else:
        def diferenca_com_valor(valor):
            dados_ponto = dados.copy()
            dados_ponto[parametro] = valor
            return _diferenca_de_custos(
                dados_ponto["quantidade"],
                dados_ponto["preco"],
                dados_ponto["manutencao"],
                dados_ponto["seguro"],
                dados_ponto["revenda"],
                dados_ponto["aluguel"],
                dados_ponto["anos"],
                dados_ponto["taxa"],
                dados_ponto["inflacao"],
            )

        limite_superior = (
            max(10.0, dados[parametro] * 2)
            if parametro == "taxa"
            else max(1.0, dados[parametro] * 2)
            if parametro == "inflacao"
            else max(1_000_000.0, dados[parametro] * 10)
        )
        ponto = _buscar_inflexao_continua(
            parametro,
            dados[parametro],
            diferenca_com_valor,
            limite_superior,
        )
        ponto_inflexao = ponto["ponto"] if ponto is not None else None

    return {
        "parametro": parametro,
        "valores": valores,
        "custos_compra": custos_compra,
        "custos_aluguel": custos_aluguel,
        "ponto_inflexao": ponto_inflexao,
    }


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
    inflacao_anual=0,
):
    """Mantém compatibilidade com a análise anterior de aluguel mensal."""
    resultado = gerar_dados_sensibilidade(
        "aluguel",
        {
            "quantidade": quantidade_veiculos,
            "preco": preco_por_veiculo,
            "manutencao": manutencao_anual_por_veiculo,
            "seguro": seguro_anual_por_veiculo,
            "revenda": revenda_por_veiculo,
            "aluguel": aluguel_mensal_por_veiculo,
            "anos": anos,
            "taxa": taxa_anual,
            "inflacao": inflacao_anual,
        },
        valores_aluguel,
    )
    return {
        "valores_aluguel": resultado["valores"],
        "custos_compra": resultado["custos_compra"],
        "custos_aluguel": resultado["custos_aluguel"],
        "ponto_inflexao": resultado["ponto_inflexao"],
    }