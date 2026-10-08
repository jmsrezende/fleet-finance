# Fleet Finance: comprar ou alugar a frota?

Trabalho de Administração Financeira UFMG, 2026/2.
Dupla: Estêvão Felipe da Fonseca e João Marcos de Sousa Rezende.

## Tema: valor do dinheiro no tempo

A aplicação compara o custo de **comprar** e de **alugar** uma frota de veículos
trazendo os fluxos de caixa de cada alternativa a **valor presente**:

VP = Σ Fluxo_t / (1 + i)^t

- **Compra:** preço no ano 0, manutenção e seguro anuais, revenda no último ano.
- **Aluguel:** mensalidade anualizada, paga ao fim de cada ano.
- **Inflação:** reajusta aluguel, manutenção e seguro ano a ano.
- A alternativa com o **menor VP de custos** é a mais vantajosa.

## Requisitos

- Python 3.10 ou superior
- Dependências: `pip install -r requirements.txt`

## Como executar

```bash
python main.py
```

Testes automatizados:

```bash
python -m unittest -v
```

## Funcionalidades

1. **Captura de dados:** digitação manual ou o botão *Buscar Selic e IPCA (BCB)*,
   que consulta a API pública SGS do Banco Central:
   - Meta Selic (série 432), usada como taxa de desconto;
   - IPCA mensal (série 433), acumulado em 12 meses e usado como inflação.
   Sem internet, o app mantém os valores digitados.
2. **Comparação:** VP de cada alternativa, diferença e decisão.
3. **Análise de sensibilidade:** gráficos do custo ao variar um parâmetro,
   com o ponto de inflexão em que a decisão muda.
4. **Relatório PDF:** exporta entradas, fontes externas, metodologia, resultados,
   pontos de inflexão, gráfico de sensibilidade e limitações da análise.


## Estrutura

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Ponto de entrada |
| `interface.py` | Interface gráfica (Tkinter + Matplotlib) |
| `calculos.py` | Fluxos de caixa, valor presente e sensibilidade |
| `dados_externos.py` | Consulta à API SGS do Banco Central |
| `relatorio.py` | Geração do relatório PDF da análise |
| `test_*.py` | Testes automatizados |

## Limitações

- O IPCA dos últimos 12 meses é inflação passada, usado como estimativa da futura.
- Os fluxos são anuais e pagos no fim de cada ano.
- Uma única taxa de desconto vale para todo o período.
