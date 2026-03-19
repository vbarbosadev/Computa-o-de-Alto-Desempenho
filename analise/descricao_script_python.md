# Descrição: Script Python de análise e comparação de dados das Tarefas 1, 2 e 3

## Objetivo geral
Ler os CSVs gerados pelo `run_tests.sh` (pasta `dados/`) e gerar gráficos comparativos para cada tarefa.
Salvar os gráficos em `analise/graficos/`.

---

## Dependências
- pandas
- matplotlib
- numpy

---

## Tarefa 1 — `dados/tarefa1.csv`

**Colunas:** `N, tempo_linha, tempo_coluna`

### Gráfico 1 — Tempo de execução × Tamanho da matriz
- Tipo: linha com marcadores
- Eixo X: N (tamanho da matriz), escala linear
- Eixo Y: tempo em segundos
- Duas séries: "Acesso por Linha (row-major)" e "Acesso por Coluna (column-major)"
- Título: "MxV — Impacto do padrão de acesso à cache"
- Anotar visualmente o ponto onde as curvas começam a divergir

### Gráfico 2 — Speedup (tempo_coluna / tempo_linha) × N
- Tipo: barra ou linha
- Eixo X: N
- Eixo Y: speedup (razão coluna/linha)
- Linha horizontal tracejada em y=1 (referência de equivalência)

---

## Tarefa 2 — `dados/tarefa2.csv`

**Colunas:** `laco, otimizacao, tempo`
- `laco`: "laco2" (dependência) ou "laco3" (sem dependência)
- `otimizacao`: "O0", "O2", "O3"

### Gráfico 3 — Tempo × Nível de otimização por laço
- Tipo: barras agrupadas
- Eixo X: nível de otimização (O0, O2, O3)
- Eixo Y: tempo em segundos (escala logarítmica se a diferença for grande)
- Duas barras por grupo: laço 2 (com dependência) e laço 3 (sem dependência)
- Título: "ILP — Efeito das dependências e nível de otimização"

### Gráfico 4 — Speedup de laco3 em relação a laco2 por nível de otimização
- Tipo: barras simples
- Speedup = tempo_laco2 / tempo_laco3 para cada nível de otimização
- Título: "Ganho ao quebrar dependência de dados"

---

## Tarefa 3 — `dados/tarefa3.csv`

**Colunas:** `iteracoes, segundos, pi_aprox, erro`

### Gráfico 5 — Erro de aproximação × Número de iterações
- Tipo: linha com marcadores
- Eixo X: iterações (escala log ou linear)
- Eixo Y: erro absoluto (|pi_aprox - π|), escala logarítmica
- Linha horizontal tracejada em y=1e-15 (limite de precisão double)
- Título: "Gauss-Legendre — Convergência para π"

### Gráfico 6 — Tempo de execução × Número de iterações
- Tipo: barra
- Eixo X: iterações
- Eixo Y: tempo em segundos
- Título: "Gauss-Legendre — Tempo por número de iterações"

---

## Observações de implementação
- Usar `plt.tight_layout()` em todos os gráficos
- Salvar em PNG com `dpi=150`
- Nomear arquivos: `tarefa1_tempo.png`, `tarefa1_speedup.png`, `tarefa2_barras.png`,
  `tarefa2_speedup.png`, `tarefa3_erro.png`, `tarefa3_tempo.png`
- Ao final, imprimir um resumo em texto no terminal com os valores mais relevantes de cada tabela
