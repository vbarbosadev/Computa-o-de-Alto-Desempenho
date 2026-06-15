# Correcoes para o speedup da Tarefa 17

## Diagnostico

O speedup MPI ficou abaixo de 1 porque a comparacao atual nao mede exatamente o
mesmo tipo de custo nas duas versoes.

Na versao sequencial, o tempo comeca depois que a matriz `A` e o vetor `x` ja foram
preenchidos. Portanto, o tempo sequencial mede basicamente apenas o calculo de
`y = A * x`.

Na versao MPI, o tempo medido inclui:

- `MPI_Bcast` do vetor `x`;
- `MPI_Scatter` da matriz `A`;
- calculo local de cada bloco de linhas;
- checksum local;
- `MPI_Gather` do vetor `y`;
- `MPI_Reduce` do checksum.

Assim, o MPI esta sendo comparado contra um sequencial muito mais barato. O maior
custo extra e o `MPI_Scatter`, porque ele distribui `M * N` valores `double` da
matriz. Para a matriz `4000x2000`, isso representa cerca de 61 MB movimentados antes
do calculo.

## Problema principal

O programa MPI cumpre o enunciado da tarefa, pois usa `MPI_Scatter`, `MPI_Bcast` e
`MPI_Gather`. O problema esta na metodologia de avaliacao: o tempo total MPI inclui
comunicacao e sincronizacao, enquanto o tempo sequencial mede apenas computacao.

Por isso, mesmo com divisao correta do trabalho, o ganho da multiplicacao local nao
compensa o custo de distribuir a matriz para os tamanhos testados.

## Mudancas recomendadas

### 1. Separar tempo de comunicacao e tempo de calculo

Alterar `matvec_collective.c` para medir separadamente:

- tempo de `MPI_Bcast`;
- tempo de `MPI_Scatter`;
- tempo de multiplicacao local;
- tempo de `MPI_Gather`;
- tempo de `MPI_Reduce`;
- tempo total.

Isso permite mostrar no relatorio se o gargalo esta no calculo ou na comunicacao.

### 2. Medir o tempo maximo entre processos

Em programas MPI, o tempo da execucao paralela deve considerar o processo mais lento.
Depois de medir o tempo local em cada rank, usar:

```c
MPI_Reduce(&tempo_local, &tempo_total, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
```

O mesmo pode ser feito para os tempos parciais. Isso deixa a medicao mais correta do
que usar apenas o tempo observado no rank `0`.

### 3. Calcular dois tipos de speedup

Manter o speedup contra a versao sequencial:

```text
speedup_seq = tempo_sequencial / tempo_mpi_total
```

E adicionar o speedup interno do MPI:

```text
speedup_mpi = tempo_mpi_1_processo / tempo_mpi_p_processos
```

Nos resultados atuais, o speedup contra o sequencial fica menor que 1, mas o speedup
interno do MPI mostra que a versao com mais processos reduz um pouco o tempo em
relacao ao MPI com 1 processo.

### 4. Amortizar o custo do `MPI_Scatter`

Para obter speedup real em uma simulacao mais proxima de uso pratico, distribuir a
matriz `A` uma vez e executar varias multiplicacoes usando o mesmo bloco local.

Exemplo de organizacao:

1. preencher `A` no rank `0`;
2. distribuir `A` com `MPI_Scatter`;
3. repetir varias vezes:
   - atualizar ou preencher `x`;
   - distribuir `x` com `MPI_Bcast`;
   - calcular `y_local`;
   - reunir `y` com `MPI_Gather`, se necessario;
4. medir separadamente o tempo com e sem o `Scatter` inicial.

Com isso, o custo de distribuir a matriz deixa de ser pago integralmente em cada
multiplicacao.

### 5. Aumentar o tamanho dos testes

Os tempos sequenciais atuais sao muito pequenos. Para avaliar MPI, usar matrizes
maiores ou mais repeticoes internas, por exemplo:

- `8000x4000`;
- `12000x4000`;
- `16000x8000`, se houver memoria suficiente;
- ou repetir a multiplicacao 50, 100 ou 200 vezes no mesmo programa.

O objetivo e aumentar a razao entre computacao e comunicacao.

### 6. Atualizar o CSV e o relatorio

Adicionar colunas no CSV, por exemplo:

- `total_time`;
- `bcast_time`;
- `scatter_time`;
- `compute_time`;
- `gather_time`;
- `reduce_time`;
- `speedup_seq`;
- `speedup_mpi`;
- `efficiency_seq`;
- `efficiency_mpi`.

No relatorio, explicar que:

- o speedup contra o sequencial mede o custo total da estrategia MPI;
- o speedup interno do MPI mede apenas a escalabilidade da versao paralela;
- `MPI_Scatter` domina quando a matriz e grande e a multiplicacao e executada poucas
  vezes;
- o MPI tende a melhorar quando os dados ja estao distribuidos ou quando o mesmo
  bloco de matriz e reutilizado em varias multiplicacoes.

## Conclusao

Nao ha indicio de erro no calculo: os checksums batem. O speedup abaixo de 1 acontece
porque a comunicacao da matriz, principalmente via `MPI_Scatter`, custa mais do que o
ganho obtido ao dividir a multiplicacao nos tamanhos testados.

Para corrigir a avaliacao, o proximo passo e instrumentar os tempos parciais, usar
`MPI_Reduce` com `MPI_MAX` para o tempo paralelo e reportar tanto o speedup contra o
sequencial quanto o speedup interno do MPI. Para melhorar o desempenho observado,
deve-se amortizar a distribuicao da matriz ou aumentar bastante o volume de calculo.
