"""Interface grafica para comparar compra e aluguel de uma frota."""

import math
import tkinter as tk
from tkinter import messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from calculos import (
    calcular_valor_presente,
    comparar_alternativas,
    gerar_dados_sensibilidade,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
)


def formatar_reais(valor):
    valor_formatado = f"{valor:,.2f}".replace(",", "X").replace(".", ",")
    return valor_formatado.replace("X", ".")


def criar_interface(root):
    root.title("Comparação de custos da frota")
    root.geometry("1180x800")
    root.minsize(900, 620)
    root.resizable(True, True)

    root.columnconfigure(0, weight=3, uniform="main")
    root.columnconfigure(1, weight=2, uniform="main")
    root.rowconfigure(0, weight=1)

    coluna_esquerda = ttk.Frame(root, padding=(10, 10, 6, 10))
    coluna_esquerda.grid(row=0, column=0, sticky="nsew")
    coluna_esquerda.columnconfigure(0, weight=1)

    coluna_direita = ttk.Frame(root, padding=(6, 10, 10, 10))
    coluna_direita.grid(row=0, column=1, sticky="nsew")
    coluna_direita.columnconfigure(0, weight=1)
    coluna_direita.rowconfigure(1, weight=1)

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
        secao = ttk.LabelFrame(coluna_esquerda, text=titulo, padding=10)
        secao.grid(
            row=linha_secao, column=0, pady=(0 if linha_secao == 0 else 4, 4),
            sticky="ew",
        )

        for linha, (chave, rotulo, unidade) in enumerate(campos_secao):
            ttk.Label(secao, text=f"{rotulo} ({unidade}):").grid(
                row=linha, column=0, padx=(0, 10), pady=3, sticky="w"
            )
            campo = ttk.Entry(secao, width=18)
            campo.grid(row=linha, column=1, pady=3, sticky="e")
            campos[chave] = campo

    secao_inflacao = ttk.LabelFrame(
        coluna_esquerda, text="Inflação", padding=10
    )
    secao_inflacao.grid(
        row=len(secoes), column=0, pady=(4, 4), sticky="ew"
    )
    considerar_inflacao = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        secao_inflacao,
        text="Considerar inflação",
        variable=considerar_inflacao,
        command=lambda: campo_inflacao.configure(
            state="normal" if considerar_inflacao.get() else "disabled"
        ),
    ).grid(row=0, column=0, columnspan=2, sticky="w")
    ttk.Label(secao_inflacao, text="Taxa de inflação anual (%):").grid(
        row=1, column=0, padx=(0, 10), pady=(4, 0), sticky="w"
    )
    campo_inflacao = ttk.Entry(secao_inflacao, width=18)
    campo_inflacao.insert(0, "6,00")
    campo_inflacao.configure(state="disabled")
    campo_inflacao.grid(row=1, column=1, pady=(4, 0), sticky="e")

    resultado = ttk.Label(
        coluna_esquerda,
        text="Informe os dados e clique em Calcular.",
        justify="left",
        padding=(4, 6),
    )
    resultado.grid(row=len(secoes) + 2, column=0, pady=2, sticky="w")

    def ler_dados(inflacao_obrigatoria=False):
        try:
            taxa_inflacao = 0
            if considerar_inflacao.get() or inflacao_obrigatoria:
                texto_inflacao = campo_inflacao.get().strip()
                if not texto_inflacao:
                    raise ValueError(
                        "Preencha o campo 'Taxa de inflação anual'."
                    )
                try:
                    taxa_inflacao = float(texto_inflacao.replace(",", ".")) / 100
                except ValueError:
                    raise ValueError(
                        "Informe um número válido no campo "
                        "'Taxa de inflação anual'."
                    ) from None
                if not math.isfinite(taxa_inflacao) or taxa_inflacao < 0:
                    raise ValueError(
                        "A taxa de inflação anual deve ser finita e não negativa."
                    )
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
                "inflacao": taxa_inflacao,
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
            dados["inflacao"],
        )
        fluxo_aluguel = gerar_fluxo_aluguel(
            dados["quantidade"],
            dados["aluguel"],
            dados["anos"],
            dados["inflacao"],
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

    ttk.Button(coluna_esquerda, text="Calcular", command=calcular).grid(
        row=len(secoes) + 1, column=0, pady=(2, 6), sticky="ew"
    )

    secao_sensibilidade = ttk.LabelFrame(
        coluna_direita, text="Análise de sensibilidade", padding=10
    )
    secao_sensibilidade.grid(
        row=0, column=0, pady=(0, 8), sticky="ew"
    )
    definicoes_sensibilidade = {
        "Preço de compra por veículo": {
            "chave": "preco",
            "titulo": "Sensibilidade do custo presente ao preço de compra",
            "eixo_x": "Preço de compra por veículo (R$)",
            "unidade": "R$",
        },
        "Aluguel mensal por veículo": {
            "chave": "aluguel",
            "titulo": "Sensibilidade do custo presente ao aluguel mensal",
            "eixo_x": "Aluguel mensal por veículo (R$)",
            "unidade": "R$",
        },
        "Manutenção anual por veículo": {
            "chave": "manutencao",
            "titulo": "Sensibilidade do custo presente à manutenção anual",
            "eixo_x": "Manutenção anual por veículo (R$)",
            "unidade": "R$",
        },
        "Seguro anual por veículo": {
            "chave": "seguro",
            "titulo": "Sensibilidade do custo presente ao seguro anual",
            "eixo_x": "Seguro anual por veículo (R$)",
            "unidade": "R$",
        },
        "Valor de revenda por veículo": {
            "chave": "revenda",
            "titulo": "Sensibilidade do custo presente ao valor de revenda",
            "eixo_x": "Valor de revenda por veículo (R$)",
            "unidade": "R$",
        },
        "Taxa de desconto anual": {
            "chave": "taxa",
            "titulo": "Sensibilidade do custo presente à taxa de desconto",
            "eixo_x": "Taxa de desconto anual (%)",
            "unidade": "%",
        },
        "Período de análise em anos": {
            "chave": "anos",
            "titulo": "Sensibilidade do custo presente ao período de análise",
            "eixo_x": "Período de análise (anos)",
            "unidade": "anos",
        },
        "Taxa de inflação anual": {
            "chave": "inflacao",
            "titulo": "Sensibilidade do custo presente à inflação",
            "eixo_x": "Taxa de inflação anual (%)",
            "unidade": "%",
        },
    }
    ttk.Label(secao_sensibilidade, text="Parâmetro:").grid(
        row=0, column=0, padx=(0, 8), sticky="w"
    )
    seletor_parametro = ttk.Combobox(
        secao_sensibilidade,
        state="readonly",
        values=tuple(definicoes_sensibilidade),
        width=32,
    )
    seletor_parametro.current(1)
    seletor_parametro.grid(row=0, column=1, sticky="ew")
    secao_sensibilidade.columnconfigure(1, weight=1)

    def gerar_grafico_sensibilidade():
        definicao = definicoes_sensibilidade[seletor_parametro.get()]
        chave = definicao["chave"]
        dados = ler_dados(inflacao_obrigatoria=chave == "inflacao")
        if dados is None:
            return

        valor_atual = dados[chave]
        if chave == "inflacao" and not considerar_inflacao.get():
            valor_atual = float(campo_inflacao.get().strip().replace(",", ".")) / 100
        if chave == "anos":
            limite_inferior = max(1, math.floor(valor_atual * 0.5))
            limite_superior = max(
                limite_inferior + 1, math.ceil(valor_atual * 1.5)
            )
            valores = list(range(limite_inferior, limite_superior + 1))
        else:
            limite_inferior = max(0, valor_atual * 0.5)
            if chave in ("taxa", "inflacao"):
                limite_superior = valor_atual * 1.5 if valor_atual else 0.1
            else:
                limite_superior = valor_atual * 1.5 if valor_atual else 1
            valores = [
                limite_inferior
                + (limite_superior - limite_inferior) * indice / 40
                for indice in range(41)
            ]

        sensibilidade = gerar_dados_sensibilidade(chave, dados, valores)
        ponto_inflexao = sensibilidade["ponto_inflexao"]
        if (
            ponto_inflexao is not None
            and limite_inferior <= ponto_inflexao <= limite_superior
            and ponto_inflexao not in valores
        ):
            valores.append(ponto_inflexao)
            valores.sort()
            sensibilidade = gerar_dados_sensibilidade(chave, dados, valores)

        figura = estado_grafico["figura"]
        eixo = estado_grafico["eixo"]
        eixo.clear()
        x = sensibilidade["valores"]
        custos_compra = sensibilidade["custos_compra"]
        custos_aluguel = sensibilidade["custos_aluguel"]

        eixo.plot(x, custos_compra, label="Custo presente da compra")
        eixo.plot(x, custos_aluguel, label="Custo presente do aluguel")
        eixo.fill_between(
            x,
            custos_compra,
            custos_aluguel,
            where=[
                compra < aluguel
                for compra, aluguel in zip(custos_compra, custos_aluguel)
            ],
            alpha=0.12,
            label="Compra mais barata",
        )
        eixo.fill_between(
            x,
            custos_compra,
            custos_aluguel,
            where=[
                aluguel < compra
                for compra, aluguel in zip(custos_compra, custos_aluguel)
            ],
            alpha=0.12,
            label="Aluguel mais barato",
        )

        ponto_inflexao = sensibilidade["ponto_inflexao"]
        if ponto_inflexao is not None and x[0] <= ponto_inflexao <= x[-1]:
            indice_ponto = min(
                range(len(x)), key=lambda indice: abs(x[indice] - ponto_inflexao)
            )
            if math.isclose(x[indice_ponto], ponto_inflexao, rel_tol=1e-9, abs_tol=1e-9):
                valor_formatado = {
                    "R$": f"R$ {formatar_reais(ponto_inflexao)}",
                    "%": f"{ponto_inflexao:.2%}",
                    "anos": f"{ponto_inflexao} anos",
                }[definicao["unidade"]]
                custo_no_ponto = custos_compra[indice_ponto]
                eixo.axvline(
                    ponto_inflexao,
                    color="black",
                    linestyle=":",
                    label=f"Ponto de inflexão: {valor_formatado}",
                )
                eixo.scatter(
                    [ponto_inflexao], [custo_no_ponto], color="black", zorder=4
                )

        eixo.set_title(definicao["titulo"], fontsize=10)
        eixo.set_xlabel(definicao["eixo_x"], fontsize=8)
        eixo.set_ylabel("Valor presente dos custos (R$)", fontsize=8)
        eixo.tick_params(axis="both", labelsize=7)
        eixo.tick_params(axis="x", labelrotation=12)
        if definicao["unidade"] == "R$":
            eixo.xaxis.set_major_formatter(
                FuncFormatter(lambda valor, _: f"R$ {formatar_reais(valor)}")
            )
        elif definicao["unidade"] == "%":
            eixo.xaxis.set_major_formatter(
                FuncFormatter(lambda valor, _: f"{valor:.2%}")
            )
        else:
            eixo.xaxis.set_major_formatter(
                FuncFormatter(lambda valor, _: f"{valor:.0f}")
            )
        eixo.yaxis.set_major_formatter(
            FuncFormatter(lambda valor, _: f"R$ {formatar_reais(valor)}")
        )
        if chave == "anos" and len(x) <= 7:
            ticks_x = list(x)
        else:
            ticks_x = [x[0], x[-1]]
        if (
            ponto_inflexao is not None
            and x[0] <= ponto_inflexao <= x[-1]
            and (chave != "anos" or ponto_inflexao in x)
        ):
            ticks_x.append(ponto_inflexao)
        ticks_x.sort()
        ticks_sem_duplicatas = []
        for tick in ticks_x:
            if not ticks_sem_duplicatas or not math.isclose(
                tick, ticks_sem_duplicatas[-1], rel_tol=1e-9, abs_tol=1e-9
            ):
                ticks_sem_duplicatas.append(tick)
        eixo.set_xticks(ticks_sem_duplicatas)
        eixo.grid(True, alpha=0.3)
        eixo.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.22),
            ncol=2,
            fontsize=7,
        )
        figura.tight_layout(rect=(0, 0.18, 1, 0.94))

        canvas = estado_grafico["canvas"]
        if canvas is None:
            estado_grafico["mensagem"].destroy()
            canvas = FigureCanvasTkAgg(figura, master=area_grafico)
            canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")
            estado_grafico["canvas"] = canvas
        canvas.draw_idle()

    ttk.Button(
        secao_sensibilidade,
        text="Gerar gráfico",
        command=gerar_grafico_sensibilidade,
    ).grid(row=1, column=0, columnspan=2, pady=(8, 0), sticky="w")

    area_grafico = ttk.Frame(coluna_direita, relief="sunken", borderwidth=1)
    area_grafico.grid(row=1, column=0, sticky="nsew")
    area_grafico.columnconfigure(0, weight=1)
    area_grafico.rowconfigure(0, weight=1)
    mensagem_grafico = ttk.Label(
        area_grafico,
        text="Selecione os parâmetros e gere uma análise de sensibilidade.",
        justify="center",
        anchor="center",
    )
    mensagem_grafico.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
    figura_grafico = Figure(figsize=(4.5, 3.5), dpi=80)
    eixo_grafico = figura_grafico.add_subplot(111)
    estado_grafico = {
        "figura": figura_grafico,
        "eixo": eixo_grafico,
        "canvas": None,
        "mensagem": mensagem_grafico,
    }


def main():
    root = tk.Tk()
    criar_interface(root)
    root.mainloop()


if __name__ == "__main__":
    main()
