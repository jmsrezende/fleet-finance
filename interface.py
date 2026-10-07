"""Interface grafica para comparar compra e aluguel de uma frota."""

import math
import tkinter as tk
from tkinter import messagebox, ttk

from calculos import (
    analisar_pontos_inflexao,
    calcular_valor_presente,
    comparar_alternativas,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
)


def formatar_reais(valor):
    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",")
    return valor_formatado.replace("X", ".")


def criar_interface(root):
    root.title("Comparação de custos da frota")
    root.resizable(False, True)

    campos = {}
    secoes = (
        (
            "Compra",
            (
                ("quantidade", "Quantidade de veículos", "veículos"),
                ("preco", "Preço de compra por veículo", "R$"),
                ("manutencao", "Manutenção anual por veículo", "R$"),
                ("seguro", "Seguro anual por veículo", "R$"),
                ("revenda", "Valor de revenda por veículo", "R$"),
            ),
        ),
        (
            "Aluguel",
            (("aluguel", "Aluguel mensal por veículo", "R$"),),
        ),
        (
            "Análise",
            (
                ("anos", "Período de análise", "anos"),
                ("taxa", "Taxa de desconto anual", "%"),
            ),
        ),
    )

    for linha_secao, (titulo, campos_secao) in enumerate(secoes):
        secao = ttk.LabelFrame(root, text=titulo, padding=10)
        secao.grid(
            row=linha_secao,
            column=0,
            padx=12,
            pady=(10 if linha_secao == 0 else 4, 4),
            sticky="ew",
        )

        for linha, (chave, rotulo, unidade) in enumerate(campos_secao):
            ttk.Label(secao, text=f"{rotulo} ({unidade}):").grid(
                row=linha, column=0, padx=(0, 10), pady=3, sticky="w"
            )
            campo = ttk.Entry(secao, width=18)
            campo.grid(row=linha, column=1, pady=3, sticky="e")
            campos[chave] = campo

    resultado = ttk.Label(
        root,
        text="Informe os dados e clique em Calcular.",
        justify="left",
        padding=10,
    )
    resultado.grid(row=len(secoes), column=0, padx=12, pady=4, sticky="w")

    def ler_dados():
        try:
            return {
                "quantidade": obter_numero(
                    "quantidade", "Quantidade de veículos", True
                ),
                "preco": obter_numero("preco", "Preço de compra por veículo"),
                "manutencao": obter_numero(
                    "manutencao", "Manutenção anual por veículo"
                ),
                "seguro": obter_numero("seguro", "Seguro anual por veículo"),
                "revenda": obter_numero("revenda", "Valor de revenda por veículo"),
                "aluguel": obter_numero(
                    "aluguel", "Aluguel mensal por veículo"
                ),
                "anos": obter_numero("anos", "Período de análise", True),
                "taxa": obter_numero("taxa", "Taxa de desconto anual") / 100,
            }
        except ValueError as erro:
            messagebox.showerror("Dados inválidos", str(erro), parent=root)
            return None

    def obter_numero(chave, rotulo, inteiro=False):
        texto = campos[chave].get().strip()
        if not texto:
            raise ValueError(f"Preencha o campo '{rotulo}'.")

        try:
            valor = int(texto) if inteiro else float(texto.replace(",", "."))
        except ValueError:
            tipo = "um número inteiro" if inteiro else "um número"
            raise ValueError(f"Informe {tipo} válido no campo '{rotulo}'.") from None

        if not inteiro and not math.isfinite(valor):
            raise ValueError(f"Informe um número finito no campo '{rotulo}'.")

        if valor < (1 if inteiro else 0):
            minimo = "1" if inteiro else "0"
            raise ValueError(
                f"O campo '{rotulo}' deve ser maior ou igual a {minimo}."
            )
        return valor

    def calcular():
        dados = ler_dados()
        if dados is None:
            return

        fluxo_compra = gerar_fluxo_compra(
            dados["quantidade"],
            dados["preco"],
            dados["manutencao"],
            dados["seguro"],
            dados["revenda"],
            dados["anos"],
        )
        fluxo_aluguel = gerar_fluxo_aluguel(
            dados["quantidade"], dados["aluguel"], dados["anos"]
        )
        custo_compra = calcular_valor_presente(fluxo_compra, dados["taxa"])
        custo_aluguel = calcular_valor_presente(fluxo_aluguel, dados["taxa"])
        alternativa, diferenca = comparar_alternativas(custo_compra, custo_aluguel)

        nome_alternativa = {
            "compra": "COMPRAR",
            "aluguel": "ALUGAR",
            "empate": "EMPATE",
        }[alternativa]
        resultado.config(
            text=(
                "CUSTO PRESENTE\n\n"
                f"Compra:   R$ {formatar_reais(custo_compra)}\n"
                f"Aluguel:  R$ {formatar_reais(custo_aluguel)}\n\n"
                f"Diferença: R$ {formatar_reais(diferenca)}\n\n"
                "ALTERNATIVA MAIS VANTAJOSA:\n"
                f"{nome_alternativa}"
            )
        )

    ttk.Button(root, text="Calcular", command=calcular).grid(
        row=len(secoes) + 1, column=0, padx=12, pady=(4, 12), sticky="ew"
    )

    secao_inflexao = ttk.LabelFrame(
        root, text="Análise de pontos de inflexão", padding=10
    )
    secao_inflexao.grid(
        row=len(secoes) + 2, column=0, padx=12, pady=(4, 12), sticky="ew"
    )
    texto_inflexao = tk.Text(
        secao_inflexao, width=75, height=10, wrap="word", state="disabled"
    )
    texto_inflexao.grid(row=0, column=0, sticky="ew")
    rolagem_inflexao = ttk.Scrollbar(
        secao_inflexao, orient="vertical", command=texto_inflexao.yview
    )
    rolagem_inflexao.grid(row=0, column=1, sticky="ns")
    texto_inflexao.configure(yscrollcommand=rolagem_inflexao.set)

    def analisar():
        dados = ler_dados()
        if dados is None:
            return

        resultados = analisar_pontos_inflexao(
            dados["quantidade"],
            dados["preco"],
            dados["manutencao"],
            dados["seguro"],
            dados["revenda"],
            dados["aluguel"],
            dados["anos"],
            dados["taxa"],
        )
        rotulos = {
            "preco": ("Preço de compra por veículo", "R$"),
            "aluguel": ("Aluguel mensal por veículo", "R$"),
            "manutencao": ("Manutenção anual por veículo", "R$"),
            "seguro": ("Seguro anual por veículo", "R$"),
            "revenda": ("Valor de revenda por veículo", "R$"),
            "taxa": ("Taxa de desconto anual", "%"),
            "anos": ("Número de anos", "anos"),
        }

        def formatar_valor_parametro(valor, unidade):
            if unidade == "R$":
                return f"R$ {formatar_reais(valor)}"
            return f"{valor:g} {unidade}"

        linhas = ["ANÁLISE DE PONTOS DE INFLEXÃO"]
        for item in resultados:
            chave = item["parametro"]
            rotulo, unidade = rotulos[chave]
            atual = item["atual"] * 100 if chave == "taxa" else item["atual"]
            linhas.append(
                f"\n{rotulo} — valor atual: "
                f"{formatar_valor_parametro(atual, unidade)}"
            )

            ponto = item["ponto"]
            if ponto is None:
                inicio, fim = item["intervalo"]
                if chave == "taxa":
                    inicio, fim = inicio * 100, fim * 100
                linhas.append(
                    "  Não foi encontrada mudança de decisão no intervalo "
                    f"{formatar_valor_parametro(inicio, unidade)} a "
                    f"{formatar_valor_parametro(fim, unidade)}."
                )
            elif chave == "anos":
                antes, depois = ponto["entre"]
                if ponto["ponto"] is not None:
                    linhas.append(
                        f"  Igualdade em {ponto['ponto']} anos; antes favorece "
                        f"{ponto['antes']} e depois favorece {ponto['depois']}."
                    )
                else:
                    linhas.append(
                        f"  Decisão muda entre {antes} e {depois} anos "
                        "(não há igualdade exata em anos inteiros): "
                        f"{ponto['antes']} → {ponto['depois']}."
                    )
            else:
                valor_ponto = ponto["ponto"] * 100 if chave == "taxa" else ponto["ponto"]
                linhas.append(
                    "  Ponto de igualdade: "
                    f"{formatar_valor_parametro(valor_ponto, unidade)}; "
                    f"abaixo favorece {ponto['abaixo']} e acima favorece "
                    f"{ponto['acima']}."
                )

        texto_inflexao.configure(state="normal")
        texto_inflexao.delete("1.0", tk.END)
        texto_inflexao.insert("1.0", "\n".join(linhas))
        texto_inflexao.configure(state="disabled")

    ttk.Button(
        secao_inflexao, text="Analisar pontos de inflexão", command=analisar
    ).grid(row=1, column=0, columnspan=2, pady=(8, 0), sticky="ew")


def main():
    root = tk.Tk()
    criar_interface(root)
    root.mainloop()


if __name__ == "__main__":
    main()
