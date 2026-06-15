# Correcoes para a Tarefa 18

## Diagnostico

A Tarefa 18 reimplementa o produto `y = A * x` distribuindo colunas da matriz entre
os processos. O enunciado pede duas versoes: uma usando `MPI_Type_vector` e outra
acrescentando `MPI_Type_create_resized`. Tambem pede que os segmentos de `x` sejam
enviados com `MPI_Scatter` e que os vetores parciais de `y` sejam somados com
`MPI_Reduce` e `MPI_SUM`.

Os checksums dos resultados atuais batem com a versao sequencial, entao nao ha
indicio de erro no calculo. O problema principal esta na avaliacao de desempenho e
na comparacao com a Tarefa 17.

Assim como na Tarefa 17, o speedup contra a versao sequencial fica abaixo de 1 porque
o tempo sequencial mede praticamente apenas o calculo, enquanto o tempo MPI mede
comunicacao, copia/empacotamento de dados, calculo local e reducao final.

Nos resultados atuais, os speedups contra o sequencial ficam aproximadamente nestas
faixas:

|Versao|Matriz|Melhor speedup contra sequencial|
|---|---:|---:|
|`cols_vector`|`1000x1000`|0.41|
|`cols_resized`|`1000x1000`|0.41|
|`cols_vector`|`2000x2000`|0.33|
|`cols_resized`|`2000x2000`|0.32|
|`cols_vector`|`4000x2000`|0.25|
|`cols_resized`|`4000x2000`|0.24|

Isso nao significa que o paralelismo esta completamente sem efeito. Usando a versao
MPI com 1 processo como base, o speedup interno chega a cerca de 1.14 a 1.24 com 4
processos, dependendo da matriz e da versao. Ou seja, aumentar os processos reduz o
tempo MPI, mas nao o suficiente para superar o sequencial puro.

## Causas principais

### 1. Comparacao injusta com o sequencial

A versao sequencial da Tarefa 17 mede apenas o trecho de multiplicacao. Ja as versoes
MPI da Tarefa 18 medem:

- `MPI_Scatter` do segmento de `x`;
- `MPI_Scatter` da matriz por colunas usando tipo derivado;
- calculo local da contribuicao parcial;
- `MPI_Reduce` de um vetor de tamanho `M`;
- sincronizacoes implicitas das coletivas.

Por isso, o tempo MPI inclui custos que o tempo sequencial nao inclui.

### 2. Distribuicao por colunas e menos natural em C

Matrizes em C ficam armazenadas por linhas. A Tarefa 17 distribui linhas completas,
que sao blocos contiguos de memoria. A Tarefa 18 distribui colunas, que sao blocos
nao contiguos no layout original da matriz.

O `MPI_Type_vector` descreve corretamente esse padrao, mas o MPI precisa ler dados
com saltos entre linhas e normalmente precisa empacotar esses dados antes de enviar.
Esse padrao tende a ser pior para cache e para comunicacao do que enviar linhas
contiguas.

### 3. `MPI_Reduce` de um vetor inteiro

Na divisao por linhas, cada processo calcula uma parte final de `y`, e o processo
`0` apenas junta os blocos com `MPI_Gather`.

Na divisao por colunas, cada processo calcula uma contribuicao parcial para todos os
elementos de `y`. No fim, todos os vetores parciais de tamanho `M` precisam ser
somados com `MPI_Reduce`.

Esse `Reduce` movimenta e combina mais dados do que um `Gather` simples, alem de
fazer soma elemento a elemento.

### 4. A versao `cols_vector` usa um buffer artificial grande

Em `matvec_cols_vector.c`, o tipo criado por `MPI_Type_vector` tem uma extensao
natural grande. Para que `MPI_Scatter` funcione sem `MPI_Type_create_resized`, o
codigo cria no rank `0` um buffer com espacamento entre os blocos:

```c
a_envio = calloc((size_t)size * (size_t)extensao_tipo, sizeof(double));
```

Esse buffer fica maior que a matriz real quando ha mais de um processo. Exemplos:

|Matriz|Processos|Matriz real|Buffer da `cols_vector`|
|---|---:|---:|---:|
|`1000x1000`|4|7.6 MB|30.5 MB|
|`2000x2000`|4|30.5 MB|122.0 MB|
|`4000x2000`|4|61.0 MB|244.1 MB|

Essa preparacao ocorre antes do trecho cronometrado, mas ainda e um custo real da
implementacao e pode afetar memoria, cache, alocacao e comparabilidade. A versao
`cols_resized` e mais correta para representar a matriz original sem esse buffer
expandido.

### 5. Os graficos usam a melhor rodada, mas a tabela usa media

O script usa a melhor rodada para gerar os graficos, enquanto o relatorio agregado
usa media. Isso pode criar pequenas diferencas entre tabela e grafico. Nao e a causa
do speedup baixo, mas deve ser corrigido para deixar a analise consistente.

## Mudancas recomendadas

### 1. Instrumentar tempos parciais

Alterar `matvec_cols_vector.c` e `matvec_cols_resized.c` para medir separadamente:

- tempo do `MPI_Scatter` de `x`;
- tempo do `MPI_Scatter` da matriz;
- tempo de calculo local;
- tempo do `MPI_Reduce`;
- tempo total.

Adicionar essas colunas ao CSV:

- `scatter_x_time`;
- `scatter_a_time`;
- `compute_time`;
- `reduce_time`;
- `total_time`.

Isso mostra se o gargalo esta no tipo derivado, no calculo local ou na reducao final.

### 2. Usar `MPI_Reduce` com `MPI_MAX` para tempos

O tempo paralelo deve considerar o rank mais lento, nao apenas o tempo visto pelo
rank `0`. Para cada tempo medido localmente, reduzir com:

```c
MPI_Reduce(&tempo_local, &tempo_global, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
```

Esse mesmo padrao deve ser usado para o tempo total e para os tempos parciais.

### 3. Reportar dois speedups

Manter o speedup contra o sequencial:

```text
speedup_seq = tempo_sequencial / tempo_mpi_total
```

Adicionar tambem o speedup interno do MPI:

```text
speedup_mpi = tempo_mpi_1_processo / tempo_mpi_p_processos
```

O primeiro mostra se a estrategia MPI completa vence o sequencial. O segundo mostra
se a versao MPI escala quando aumenta a quantidade de processos.

### 4. Priorizar `cols_resized` como implementacao principal

A versao `cols_vector` e util para demonstrar o problema da extensao natural do tipo,
mas nao deve ser tratada como a melhor solucao de desempenho. Ela exige o buffer
expandido no rank `0`.

No relatorio, deixar claro:

- `cols_vector` e uma versao didatica;
- `cols_resized` e a versao correta para espalhar blocos consecutivos de colunas a
  partir da matriz real;
- a comparacao de desempenho principal deve dar mais peso a `cols_resized`.

### 5. Incluir custo de preparacao da `cols_vector`

Se a `cols_vector` continuar no comparativo de desempenho, medir tambem o tempo de
preparacao do buffer `a_envio`. Hoje essa preparacao fica fora do tempo medido.

Adicionar ao CSV:

- `setup_time`;
- `send_buffer_mb`;
- `matrix_mb`.

Sem isso, a `cols_vector` parece tao barata quanto a `cols_resized`, mas esconde uma
alocacao muito maior no rank `0`.

### 6. Aumentar o trabalho computacional

Os tempos sequenciais sao muito pequenos para uma avaliacao robusta de MPI. Para
reduzir o peso relativo das coletivas, testar matrizes maiores ou repetir a
multiplicacao varias vezes dentro do mesmo programa.

Opcoes:

- `8000x4000`;
- `12000x4000`;
- `16000x8000`, se houver memoria;
- repetir a multiplicacao 50, 100 ou 200 vezes apos distribuir os dados.

Se a matriz for distribuida uma vez e reutilizada em varias multiplicacoes, o custo
do `MPI_Scatter` da matriz e amortizado.

### 7. Comparar com a Tarefa 17 usando a mesma metodologia

Para comparar Tarefa 17 e Tarefa 18, usar as mesmas metricas:

- tempo total;
- tempo de comunicacao;
- tempo de calculo;
- speedup contra sequencial;
- speedup interno do MPI;
- eficiencia contra sequencial;
- eficiencia interna do MPI.

Tambem e importante que ambas usem a mesma regra de tempo paralelo: tempo maximo
entre ranks com `MPI_MAX`.

### 8. Usar media nos graficos

Alterar `coletar_mpi.py` ou `gerar_relatorio.py` para que os graficos usem a mesma
agregacao da tabela. A recomendacao e usar media e, se possivel, adicionar barras de
minimo/maximo ou desvio.

## Conclusao

A Tarefa 18 esta correta do ponto de vista funcional: os resultados batem com o
sequencial. O desempenho abaixo de 1 contra o sequencial acontece porque a divisao
por colunas exige comunicacao nao contigua e uma reducao final de vetor inteiro, alem
de medir custos que o sequencial nao mede.

Para corrigir a avaliacao, o proximo passo e instrumentar os tempos parciais, usar o
tempo maximo entre ranks, adicionar speedup interno do MPI e explicitar o custo de
memoria da `cols_vector`. Para melhorar o desempenho observado, a versao
`cols_resized` deve ser a principal, e a matriz deve ser reutilizada em varias
multiplicacoes ou testada em tamanhos maiores.

## Observacao sobre a coleta

Esta analise foi feita com base nos resultados ja salvos em
`Tarefa-18/resultados/tarefa18_resultados.csv`. O ambiente local atual nao encontrou
`mpicc` nem `mpirun`, entao a coleta nao foi reexecutada aqui.
