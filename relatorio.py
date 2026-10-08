"""Geração de relatórios PDF para a análise financeira da frota."""

from datetime import datetime
import math
from pathlib import Path
from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

from calculos import (
    analisar_pontos_inflexao,
    calcular_valor_presente,
    comparar_alternativas,
    gerar_dados_sensibilidade,
    gerar_fluxo_aluguel,
    gerar_fluxo_compra,
)


TITULO = "Análise Financeira: Comprar ou Alugar a Frota?"

_CAMPOS_OBRIGATORIOS = (
    "quantidade",
    "preco",
    "manutencao",
    "seguro",
    "revenda",
    "aluguel",
    "anos",
    "taxa",
    "inflacao",
)

_DEFINICOES_SENSIBILIDADE = {
    "preco": (
        "Preço de compra por veículo",
        "Sensibilidade do custo presente ao preço de compra",
        "Preço de compra por veículo (R$)",
        "R$",
    ),
    "aluguel": (
        "Aluguel mensal por veículo",
        "Sensibilidade do custo presente ao aluguel mensal",
        "Aluguel mensal por veículo (R$)",
        "R$",
    ),
    "manutencao": (
        "Manutenção anual por veículo",
        "Sensibilidade do custo presente à manutenção anual",
        "Manutenção anual por veículo (R$)",
        "R$",
    ),
    "seguro": (
        "Seguro anual por veículo",
        "Sensibilidade do custo presente ao seguro anual",
        "Seguro anual por veículo (R$)",
        "R$",
    ),
    "revenda": (
        "Valor de revenda por veículo",
        "Sensibilidade do custo presente ao valor de revenda",
        "Valor de revenda por veículo (R$)",
        "R$",
    ),
    "taxa": (
        "Taxa de desconto anual",
        "Sensibilidade do custo presente à taxa de desconto",
        "Taxa de desconto anual (%)",
        "%",
    ),
    "anos": (
        "Período de análise em anos",
        "Sensibilidade do custo presente ao período de análise",
        "Período de análise (anos)",
        "anos",
    ),
    "inflacao": (
        "Taxa de inflação anual",
        "Sensibilidade do custo presente à inflação",
        "Taxa de inflação anual (%)",
        "%",
    ),
}


def _formatar_reais(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _formatar_percentual(taxa):
    return f"{taxa * 100:.2f}%"


def _validar_dados(dados, considerando_inflacao):
    if not isinstance(dados, dict):
        raise ValueError("Os dados da análise devem ser informados em um dicionário.")

    ausentes = [campo for campo in _CAMPOS_OBRIGATORIOS if campo not in dados]
    if ausentes:
        raise ValueError(
            "Dados insuficientes para o relatório: " + ", ".join(ausentes) + "."
        )

    for campo in _CAMPOS_OBRIGATORIOS:
        valor = dados[campo]
        if (
            isinstance(valor, bool)
            or not isinstance(valor, (int, float))
            or not math.isfinite(valor)
            or valor < 0
        ):
            raise ValueError(f"O dado '{campo}' deve ser finito e não negativo.")

    if (
        isinstance(dados["quantidade"], bool)
        or not isinstance(dados["quantidade"], int)
        or dados["quantidade"] < 1
    ):
        raise ValueError("A quantidade de veículos deve ser um inteiro positivo.")
    if (
        isinstance(dados["anos"], bool)
        or not isinstance(dados["anos"], int)
        or dados["anos"] < 1
    ):
        raise ValueError("O período de análise deve ser um inteiro positivo.")
    if not isinstance(considerando_inflacao, bool):
        raise ValueError("Informe se a inflação foi considerada na análise.")


def _calcular_sensibilidade(dados, parametro, taxa_inflacao_informada):
    definicao = _DEFINICOES_SENSIBILIDADE.get(parametro)
    if definicao is None:
        raise ValueError("Selecione um parâmetro válido para a sensibilidade.")

    valor_atual = (
        taxa_inflacao_informada if parametro == "inflacao" else dados[parametro]
    )
    if parametro == "anos":
        limite_inferior = max(1, math.floor(valor_atual * 0.5))
        limite_superior = max(limite_inferior + 1, math.ceil(valor_atual * 1.5))
        valores = list(range(limite_inferior, limite_superior + 1))
    else:
        limite_inferior = max(0, valor_atual * 0.5)
        limite_superior = (
            valor_atual * 1.5
            if valor_atual
            else 0.1
            if parametro in ("taxa", "inflacao")
            else 1
        )
        valores = [
            limite_inferior + (limite_superior - limite_inferior) * indice / 40
            for indice in range(41)
        ]

    resultado = gerar_dados_sensibilidade(parametro, dados, valores)
    ponto = resultado["ponto_inflexao"]
    if (
        ponto is not None
        and limite_inferior <= ponto <= limite_superior
        and ponto not in valores
    ):
        valores.append(ponto)
        valores.sort()
        resultado = gerar_dados_sensibilidade(parametro, dados, valores)
    return resultado, definicao


def _criar_grafico_sensibilidade(dados, parametro, taxa_inflacao_informada):
    resultado, definicao = _calcular_sensibilidade(
        dados, parametro, taxa_inflacao_informada
    )
    rotulo, titulo, rotulo_x, unidade = definicao
    valores = resultado["valores"]
    custos_compra = resultado["custos_compra"]
    custos_aluguel = resultado["custos_aluguel"]

    figura = Figure(figsize=(8.2, 4.4), dpi=150)
    eixo = figura.add_subplot(111)
    eixo.plot(valores, custos_compra, label="Custo presente da compra")
    eixo.plot(valores, custos_aluguel, label="Custo presente do aluguel")
    eixo.fill_between(
        valores,
        custos_compra,
        custos_aluguel,
        where=[compra < aluguel for compra, aluguel in zip(custos_compra, custos_aluguel)],
        alpha=0.12,
        label="Compra mais barata",
    )
    eixo.fill_between(
        valores,
        custos_compra,
        custos_aluguel,
        where=[aluguel < compra for compra, aluguel in zip(custos_compra, custos_aluguel)],
        alpha=0.12,
        label="Aluguel mais barato",
    )

    ponto = resultado["ponto_inflexao"]
    if ponto is not None and valores[0] <= ponto <= valores[-1]:
        indice_ponto = min(
            range(len(valores)), key=lambda indice: abs(valores[indice] - ponto)
        )
        if math.isclose(valores[indice_ponto], ponto, rel_tol=1e-9, abs_tol=1e-9):
            eixo.axvline(
                ponto,
                color="black",
                linestyle=":",
                label=f"Ponto de inflexão: {ponto:,.2f}",
            )
            eixo.scatter(
                [ponto], [custos_compra[indice_ponto]], color="black", zorder=4
            )

    eixo.set_title(titulo, fontsize=11)
    eixo.set_xlabel(rotulo_x, fontsize=9)
    eixo.set_ylabel("Valor presente dos custos (R$)", fontsize=9)
    eixo.grid(True, alpha=0.3)
    eixo.tick_params(axis="both", labelsize=8)
    if unidade == "R$":
        eixo.xaxis.set_major_formatter(
            FuncFormatter(lambda valor, _: f"R$ {valor:,.0f}".replace(",", "."))
        )
    elif unidade == "%":
        eixo.xaxis.set_major_formatter(
            FuncFormatter(lambda valor, _: f"{valor:.1%}")
        )
    else:
        eixo.xaxis.set_major_formatter(
            FuncFormatter(lambda valor, _: f"{valor:.0f}")
        )
    eixo.yaxis.set_major_formatter(
        FuncFormatter(lambda valor, _: f"R$ {valor:,.0f}".replace(",", "."))
    )
    eixo.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2, fontsize=8)
    figura.tight_layout(rect=(0, 0.14, 1, 1))

    imagem = BytesIO()
    FigureCanvasAgg(figura).print_png(imagem)
    imagem.seek(0)
    return imagem, rotulo, resultado


def _texto_origem(origem):
    if origem and origem.get("fonte") == "bcb":
        data = origem.get("data")
        referencia = f" (referência: {data})" if data else ""
        return f"Obtido da API do Banco Central{referencia}."
    if origem and origem.get("fallback"):
        return (
            "Informado manualmente; valor digitado mantido como fallback "
            "porque a API do Banco Central não estava disponível."
        )
    return "Informado manualmente."


def _descricao_pontos_inflexao(resultados):
    nomes = {
        "preco": "preço de compra por veículo",
        "aluguel": "aluguel mensal por veículo",
        "manutencao": "manutenção anual por veículo",
        "seguro": "seguro anual por veículo",
        "revenda": "valor de revenda por veículo",
        "taxa": "taxa de desconto anual",
        "anos": "período de análise",
    }
    descricoes = []
    for resultado in resultados:
        nome = nomes[resultado["parametro"]]
        ponto = resultado["ponto"]
        if ponto is None:
            descricoes.append(
                f"<b>{nome.capitalize()}:</b> não foi identificado ponto de "
                "inflexão no intervalo avaliado pelo modelo."
            )
        elif resultado["parametro"] == "anos":
            anos = ponto["entre"]
            if ponto["ponto"] is not None:
                texto = f"equilíbrio em {ponto['ponto']} anos"
            else:
                texto = (
                    f"mudança de decisão entre {anos[0]} e {anos[1]} anos"
                )
            descricoes.append(
                f"<b>{nome.capitalize()}:</b> {texto}; mantendo as demais "
                "premissas constantes."
            )
        else:
            valor = ponto["ponto"]
            unidade = "%" if resultado["parametro"] == "taxa" else "R$"
            formatado = (
                _formatar_percentual(valor)
                if unidade == "%"
                else _formatar_reais(valor)
            )
            descricoes.append(
                f"<b>{nome.capitalize()}:</b> aproximadamente {formatado}; "
                "nesse valor as alternativas se equilibram, mantendo as "
                "demais premissas constantes."
            )
    return descricoes


def _criar_estilos():
    estilos = getSampleStyleSheet()
    estilos.add(
        ParagraphStyle(
            name="TituloRelatorio",
            parent=estilos["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=23,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365D"),
            spaceAfter=14,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="SecaoRelatorio",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="TextoRelatorio",
            parent=estilos["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            spaceAfter=5,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="ConclusaoRelatorio",
            parent=estilos["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#17365D"),
            backColor=colors.HexColor("#EAF1F8"),
            borderColor=colors.HexColor("#9FBAD0"),
            borderWidth=0.7,
            borderPadding=9,
            spaceBefore=5,
            spaceAfter=9,
        )
    )
    estilos.add(
        ParagraphStyle(
            name="FormulaRelatorio",
            parent=estilos["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=6,
            spaceAfter=6,
        )
    )
    return estilos


def _adicionar_rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(2 * cm, 1.2 * cm, "Análise financeira da frota")
    canvas.drawRightString(
        A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}"
    )
    canvas.restoreState()


def _caminho_padrao():
    pasta = Path(__file__).resolve().parent / "relatorios"
    pasta.mkdir(parents=True, exist_ok=True)
    base = datetime.now().strftime("relatorio_frota_%Y%m%d_%H%M%S")
    caminho = pasta / f"{base}.pdf"
    sequencia = 1
    while caminho.exists():
        caminho = pasta / f"{base}_{sequencia:02d}.pdf"
        sequencia += 1
    return caminho


def gerar_relatorio_pdf(
    dados,
    considerando_inflacao,
    origem_dados=None,
    parametro_sensibilidade="aluguel",
    caminho_saida=None,
):
    """Gera o PDF com os resultados calculados a partir dos dados recebidos."""
    _validar_dados(dados, considerando_inflacao)
    origem_dados = origem_dados or {}

    dados_analise = dict(dados)
    if not considerando_inflacao:
        dados_analise["inflacao"] = 0

    fluxo_compra = gerar_fluxo_compra(
        dados_analise["quantidade"],
        dados_analise["preco"],
        dados_analise["manutencao"],
        dados_analise["seguro"],
        dados_analise["revenda"],
        dados_analise["anos"],
        dados_analise["inflacao"],
    )
    fluxo_aluguel = gerar_fluxo_aluguel(
        dados_analise["quantidade"],
        dados_analise["aluguel"],
        dados_analise["anos"],
        dados_analise["inflacao"],
    )
    custo_compra = calcular_valor_presente(fluxo_compra, dados_analise["taxa"])
    custo_aluguel = calcular_valor_presente(fluxo_aluguel, dados_analise["taxa"])
    alternativa, diferenca = comparar_alternativas(custo_compra, custo_aluguel)

    pontos_inflexao = analisar_pontos_inflexao(
        dados_analise["quantidade"],
        dados_analise["preco"],
        dados_analise["manutencao"],
        dados_analise["seguro"],
        dados_analise["revenda"],
        dados_analise["aluguel"],
        dados_analise["anos"],
        dados_analise["taxa"],
        dados_analise["inflacao"],
    )
    taxa_inflacao_informada = (
        dados["inflacao"] if parametro_sensibilidade == "inflacao" else 0
    )
    grafico, rotulo_sensibilidade, resultado_sensibilidade = (
        _criar_grafico_sensibilidade(
            dados_analise,
            parametro_sensibilidade,
            taxa_inflacao_informada,
        )
    )

    gerado_em = datetime.now().astimezone()
    caminho = Path(caminho_saida) if caminho_saida else _caminho_padrao()
    caminho.parent.mkdir(parents=True, exist_ok=True)

    estilos = _criar_estilos()
    elementos = [
        Paragraph(TITULO, estilos["TituloRelatorio"]),
        Paragraph(
            f"Relatório gerado em {gerado_em.strftime('%d/%m/%Y às %H:%M:%S %Z')}.",
            estilos["TextoRelatorio"],
        ),
        Paragraph("Dados de entrada", estilos["SecaoRelatorio"]),
    ]

    entradas = [
        ["Dado", "Premissa utilizada"],
        ["Quantidade de veículos", f"{dados_analise['quantidade']:.0f}"],
        ["Preço de compra por veículo", _formatar_reais(dados_analise["preco"])],
        ["Custo anual de manutenção por veículo", _formatar_reais(dados_analise["manutencao"])],
        ["Custo anual de seguro por veículo", _formatar_reais(dados_analise["seguro"])],
        ["Valor de revenda por veículo", _formatar_reais(dados_analise["revenda"])],
        ["Aluguel mensal por veículo", _formatar_reais(dados_analise["aluguel"])],
        ["Período de análise", f"{dados_analise['anos']:.0f} anos"],
        ["Taxa de desconto anual", _formatar_percentual(dados_analise["taxa"])],
        [
            "Inflação considerada",
            "Sim" if considerando_inflacao else "Não",
        ],
    ]
    if considerando_inflacao:
        entradas.append(
            ["Taxa de inflação anual", _formatar_percentual(dados_analise["inflacao"])]
        )
    elementos.append(_criar_tabela(entradas))

    elementos.append(Paragraph("Dados externos e origem", estilos["SecaoRelatorio"]))
    elementos.append(
        Paragraph(
            f"<b>Selic:</b> {_formatar_percentual(dados_analise['taxa'])} ao ano. "
            f"{_texto_origem(origem_dados.get('selic'))}",
            estilos["TextoRelatorio"],
        )
    )
    origem_ipca = origem_dados.get("ipca")
    if considerando_inflacao:
        data_ipca = origem_ipca.get("data") if origem_ipca else None
        periodo = (
            f"Acumulado em 12 meses até {data_ipca}."
            if data_ipca
            else "Estimativa informada para o período de 12 meses."
        )
        elementos.append(
            Paragraph(
                f"<b>IPCA:</b> {_formatar_percentual(dados_analise['inflacao'])}. "
                f"{periodo} {_texto_origem(origem_ipca)}",
                estilos["TextoRelatorio"],
            )
        )
    elif origem_ipca and origem_ipca.get("fonte") == "bcb":
        elementos.append(
            Paragraph(
                f"<b>IPCA:</b> {_formatar_percentual(dados['inflacao'])}, "
                f"acumulado em 12 meses até {origem_ipca.get('data', 'data não informada')}; "
                "consultado na API do Banco Central, mas não considerado porque "
                "a inflação está desabilitada.",
                estilos["TextoRelatorio"],
            )
        )
    else:
        elementos.append(
            Paragraph(
                "IPCA não utilizado: a inflação está desabilitada.",
                estilos["TextoRelatorio"],
            )
        )

    elementos.extend(
        [
            Paragraph("Metodologia", estilos["SecaoRelatorio"]),
            Paragraph(
                "A análise compara o valor presente dos custos/desembolsos das "
                "alternativas de compra e aluguel.",
                estilos["TextoRelatorio"],
            ),
            Paragraph(
                "VP = <font name=\"Symbol\">S</font> Fluxo<sub>t</sub> / "
                "(1 + i)<super>t</super>",
                estilos["FormulaRelatorio"],
            ),
            Paragraph(
                "Na compra, considera-se o desembolso inicial, manutenção e seguro "
                "anuais, além do valor de revenda no último ano. No aluguel, "
                "consideram-se os pagamentos mensais anualizados ao longo do período. "
                "Os fluxos futuros são trazidos a valor presente pela taxa de desconto "
                "anual. A alternativa com menor valor presente dos custos é considerada "
                "financeiramente mais vantajosa dentro das premissas adotadas.",
                estilos["TextoRelatorio"],
            ),
        ]
    )
    if considerando_inflacao:
        elementos.append(
            Paragraph(
                "Com a inflação habilitada, manutenção, seguro e aluguel são "
                "reajustados ano a ano pela taxa informada; o preço inicial e o "
                "valor de revenda seguem a modelagem financeira existente.",
                estilos["TextoRelatorio"],
            )
        )

    elementos.append(Paragraph("Resultado principal", estilos["SecaoRelatorio"]))
    resultados = [
        ["Alternativa", "Valor presente dos custos"],
        ["Compra", _formatar_reais(custo_compra)],
        ["Aluguel", _formatar_reais(custo_aluguel)],
        ["Diferença absoluta", _formatar_reais(diferenca)],
    ]
    elementos.append(_criar_tabela(resultados))
    if alternativa == "compra":
        conclusao = (
            "Considerando as premissas informadas, a alternativa de compra "
            "apresenta menor valor presente dos custos e, portanto, é a alternativa "
            "financeiramente mais vantajosa no período analisado."
        )
    elif alternativa == "aluguel":
        conclusao = (
            "Considerando as premissas informadas, a alternativa de aluguel "
            "apresenta menor valor presente dos custos e, portanto, é a alternativa "
            "financeiramente mais vantajosa no período analisado."
        )
    else:
        conclusao = (
            "Considerando as premissas informadas, as alternativas apresentam "
            "o mesmo valor presente dos custos no período analisado."
        )
    elementos.append(Paragraph(conclusao, estilos["ConclusaoRelatorio"]))
    elementos.append(
        Paragraph("Análise de pontos de inflexão", estilos["SecaoRelatorio"])
    )
    elementos.append(
        Paragraph(
            "Os pontos abaixo são os retornados pela análise do modelo. Um ponto "
            "de equilíbrio indica o valor aproximado do parâmetro para o qual as "
            "alternativas se igualam, mantendo as demais premissas constantes. "
            "Para o período em anos, o modelo identifica uma transição entre anos "
            "inteiros.",
            estilos["TextoRelatorio"],
        )
    )
    elementos.extend(
        Paragraph(descricao, estilos["TextoRelatorio"])
        for descricao in _descricao_pontos_inflexao(pontos_inflexao)
    )

    elementos.append(Paragraph("Análise de sensibilidade", estilos["SecaoRelatorio"]))
    elementos.append(
        Paragraph(
            f"O gráfico varia o parâmetro <b>{rotulo_sensibilidade.lower()}</b>, "
            "mantendo os demais dados constantes. O eixo vertical apresenta os "
            "custos presentes de compra e aluguel; as áreas destacam qual alternativa "
            "tem menor custo em cada faixa. "
            + (
                "A linha pontilhada, quando exibida, marca o ponto de inflexão "
                "retornado pelo modelo."
                if resultado_sensibilidade["ponto_inflexao"] is not None
                else "Não foi identificado ponto de inflexão para o parâmetro no intervalo avaliado."
            ),
            estilos["TextoRelatorio"],
        )
    )
    largura_grafico = A4[0] - 4 * cm
    elementos.append(
        Image(grafico, width=largura_grafico, height=largura_grafico * 4.4 / 8.2)
    )
    elementos.append(Paragraph("Premissas e limitações", estilos["SecaoRelatorio"]))
    elementos.append(
        Paragraph(
            "Os fluxos são modelados conforme as premissas informadas pelo usuário, "
            "e a taxa de desconto é aplicada a todo o período de análise. O IPCA "
            "acumulado nos 12 meses disponíveis é uma estimativa baseada em dados "
            "observados, não uma previsão garantida da inflação futura. O modelo "
            "não contempla, salvo se explicitamente informado e modelado, fatores "
            "como tributação, financiamento, custos financeiros ou uma modelagem "
            "detalhada da depreciação do veículo.",
            estilos["TextoRelatorio"],
        )
    )
    documento = SimpleDocTemplate(
        str(caminho),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
        title=TITULO,
        author="Fleet Finance",
        pageCompression=0,
    )
    documento.build(
        elementos,
        onFirstPage=_adicionar_rodape,
        onLaterPages=_adicionar_rodape,
    )
    grafico.close()
    return caminho


def _criar_tabela(dados):
    tabela = Table(dados, colWidths=(8.7 * cm, 8.5 * cm), repeatRows=1, hAlign="LEFT")
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#AAB7C4")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F5F7FA")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return tabela
