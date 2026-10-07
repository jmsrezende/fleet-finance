"""Calculos de valor presente para comparar custos de compra e aluguel."""


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