"""Aplicacao de terminal para comparar compra e aluguel de uma frota."""

from calculos import (
    calcular_valor_presente,
    comparar_alternativas,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
)


def ler_numero(mensagem, minimo=0):
    while True:
        try:
            valor = float(input(mensagem).replace(",", "."))
            if valor < minimo:
                print(f"Informe um valor maior ou igual a {minimo}.")
                continue
            return valor
        except ValueError:
            print("Entrada invalida. Digite um numero.")


def ler_inteiro(mensagem, minimo=1):
    while True:
        try:
            valor = int(input(mensagem))
            if valor < minimo:
                print(f"Informe um numero inteiro maior ou igual a {minimo}.")
                continue
            return valor
        except ValueError:
            print("Entrada invalida. Digite um numero inteiro.")


def formatar_reais(valor):
    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",")
    return valor_formatado.replace("X", ".")


def main():
    print("Comparacao do valor presente dos custos da frota")
    quantidade = ler_inteiro("Quantidade de veiculos: ")
    preco = ler_numero("Preco de compra por veiculo (R$): ")
    manutencao = ler_numero("Manutencao anual por veiculo (R$): ")
    seguro = ler_numero("Seguro anual por veiculo (R$): ")
    revenda = ler_numero("Valor de revenda por veiculo ao final (R$): ")
    aluguel_mensal = ler_numero("Aluguel mensal por veiculo (R$): ")
    anos = ler_inteiro("Periodo de analise em anos: ")
    taxa_percentual = ler_numero("Taxa de desconto anual (%): ")
    taxa_anual = taxa_percentual / 100

    fluxo_compra = gerar_fluxo_compra(
        quantidade, preco, manutencao, seguro, revenda, anos
    )
    fluxo_aluguel = gerar_fluxo_aluguel(quantidade, aluguel_mensal, anos)
    custo_compra = calcular_valor_presente(fluxo_compra, taxa_anual)
    custo_aluguel = calcular_valor_presente(fluxo_aluguel, taxa_anual)
    alternativa, diferenca = comparar_alternativas(custo_compra, custo_aluguel)

    print("\nValor presente dos custos/desembolsos:")
    print(f"Compra:  R$ {formatar_reais(custo_compra)}")
    print(f"Aluguel: R$ {formatar_reais(custo_aluguel)}")
    if alternativa == "empate":
        print("As alternativas apresentam o mesmo custo presente.")
    else:
        print(
            f"A alternativa mais vantajosa e {alternativa}, "
            f"com custo presente R$ {formatar_reais(diferenca)} menor."
        )


if __name__ == "__main__":
    main()