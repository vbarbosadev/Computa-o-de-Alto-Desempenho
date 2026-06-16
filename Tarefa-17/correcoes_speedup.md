# Correcoes de speedup e teste correto da Tarefa 17

## Enunciado lido

A Tarefa 17 pede um programa MPI para calcular `y = A * x`, onde `A` tem tamanho
`M x N` e `x` tem tamanho `N`.

A solucao deve:

- dividir `A` por linhas usando `MPI_Scatter`;
- distribuir o vetor `x` inteiro usando `MPI_Bcast`;
- calcular localmente as linhas de `y`;
- reunir o vetor `y` no processo `0` usando `MPI_Gather`;
- comparar tempos para diferentes tamanhos de matriz e quantidades de processos;
- avaliar speedup e eficiencia.

## Diagnostico do problema de speedup

O codigo atual cumpre a parte funcional do enunciado: usa `MPI_Bcast`,
`MPI_Scatter`, `MPI_Gather` e valida o resultado com checksum.

O problema esta na avaliacao de desempenho. O tempo sequencial mede praticamente
apenas o calculo de `y = A * x`, porque a matriz e o vetor ja foram preenchidos
antes do cronometro iniciar.

Ja o tempo MPI mede:

- `MPI_Bcast` do vetor `x`;
- `MPI_Scatter` da matriz `A`;
- multiplicacao local;
- soma local do checksum;
- `MPI_Gather` do vetor `y`;
- `MPI_Reduce` do checksum.

Assim, o speedup atual compara um tempo sequencial barato com um tempo MPI que inclui
comunicacao e sincronizacao. Por isso, o speedup contra a versao sequencial fica
abaixo de 1 mesmo quando o trabalho local e dividido corretamente.

## Correcoes necessarias

### 1. Manter a implementacao coletiva pedida

Nao trocar `MPI_Scatter`, `MPI_Bcast` e `MPI_Gather` por envio ponto a ponto. O
enunciado exige essas coletivas.

Tambem e aceitavel manter a restricao `M % processos == 0`, porque a tarefa pede
`MPI_Scatter` simples. Se fosse necessario aceitar qualquer `M`, a alternativa seria
`MPI_Scatterv`, mas isso fugiria da forma mais direta do enunciado.

### 2. Medir o tempo paralelo pelo processo mais lento

Em MPI, o tempo da execucao paralela deve representar o processo mais lento. A forma
mais correta e reduzir o tempo local com `MPI_MAX`.

Modelo recomendado para `matvec_collective.c`:

```c
MPI_Barrier(MPI_COMM_WORLD);
double inicio_local = MPI_Wtime();

MPI_Bcast(x, n, MPI_DOUBLE, 0, MPI_COMM_WORLD);
MPI_Scatter(a, linhas_locais * n, MPI_DOUBLE,
            a_local, linhas_locais * n, MPI_DOUBLE,
            0, MPI_COMM_WORLD);
multiplicar_local(a_local, x, y_local, linhas_locais, n);
MPI_Gather(y_local, linhas_locais, MPI_DOUBLE,
           y, linhas_locais, MPI_DOUBLE,
           0, MPI_COMM_WORLD);
MPI_Reduce(&checksum_local, &checksum, 1, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

double fim_local = MPI_Wtime();
double tempo_local = fim_local - inicio_local;
double tempo_mpi = 0.0;
MPI_Reduce(&tempo_local, &tempo_mpi, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
```

O processo `0` deve imprimir `tempo_mpi`, nao apenas `fim - inicio` medido localmente
no rank `0`.

### 3. Separar tempo total e tempos parciais

Para explicar corretamente o speedup, o programa MPI deve medir tempos separados:

- `bcast_time`;
- `scatter_time`;
- `compute_time`;
- `gather_time`;
- `reduce_time`;
- `total_time`.

Cada tempo parcial tambem deve ser agregado com `MPI_MAX`, porque a etapa so termina
quando o processo mais lento termina.

Isso permite mostrar no relatorio se o gargalo esta no calculo ou na comunicacao.
Para matriz-vetor, o `MPI_Scatter` tende a pesar bastante, pois distribui `M * N`
valores `double`.

### 4. Calcular dois speedups diferentes

O CSV e o relatorio devem separar dois conceitos:

```text
speedup_seq = tempo_sequencial / total_time_mpi
efficiency_seq = speedup_seq / processos
```

Esse e o speedup contra a versao sequencial. Ele mede se a estrategia MPI completa,
incluindo comunicacao, superou o programa sequencial.

```text
speedup_mpi = total_time_mpi_1_processo / total_time_mpi_p_processos
efficiency_mpi = speedup_mpi / processos
```

Esse e o speedup interno da implementacao MPI. Ele mede se aumentar a quantidade de
processos melhora a propria versao MPI.

O relatorio deve deixar claro qual dos dois esta sendo analisado.

### 5. Testar tamanhos suficientes

Os tamanhos pequenos atuais geram tempos sequenciais muito baixos, entao qualquer
custo de MPI domina a medicao. Para avaliar melhor, usar pelo menos:

```text
1000x1000
2000x2000
4000x2000
8000x4000
```

Se houver memoria suficiente no NPAD, testar tambem:

```text
12000x4000
16000x8000
```

Se o ambiente local nao suportar matrizes grandes, a coleta local pode ser usada
apenas como teste funcional, e a coleta de desempenho deve ser feita no NPAD.

### 6. Repetir execucoes

Usar pelo menos 3 repeticoes por configuracao. Para o relatorio, usar media e melhor
tempo, mas calcular graficos preferencialmente com o melhor tempo ou com a media
explicitamente informada.

Nao misturar media em uma tabela e melhor tempo em um grafico sem explicar.

## Formato recomendado do CSV

Adicionar ou ajustar as colunas para:

```text
rep
m
n
processes
rows_per_process
seq_time
total_time
bcast_time
scatter_time
compute_time
gather_time
reduce_time
speedup_seq
efficiency_seq
speedup_mpi
efficiency_mpi
checksum
```

O `speedup_mpi` so pode ser calculado depois de existir a linha MPI com
`processes = 1` para o mesmo tamanho `M x N`.

## Comandos de teste funcional

Executar a partir da raiz do repositorio:

```bash
gcc -O3 -Wall -Wextra Tarefa-17/matvec_seq.c -o /tmp/tarefa17_matvec_seq
mpicc -O3 -Wall -Wextra Tarefa-17/matvec_collective.c -o /tmp/tarefa17_matvec_collective

/tmp/tarefa17_matvec_seq --m 12 --n 8
mpirun -np 1 /tmp/tarefa17_matvec_collective --m 12 --n 8
mpirun -np 2 /tmp/tarefa17_matvec_collective --m 12 --n 8
```

Resultado validado neste ambiente:

```text
RESULT versao=seq m=12 n=8 tempo=0.000000000 checksum=27.549451
RESULT versao=mpi_collective processos=1 m=12 n=8 linhas_por_processo=12 tempo=0.000110879 checksum=27.549451
RESULT versao=mpi_collective processos=2 m=12 n=8 linhas_por_processo=6 tempo=0.000090013 checksum=27.549451
```

O checksum e igual nas tres execucoes, entao o calculo esta correto para esse caso
minimo.

Observacao de ambiente: no sandbox, `mpirun` falhou sem permissao para abrir sockets
locais do runtime MPI. Com permissao de execucao normal, os testes MPI acima rodam.

## Comando de coleta completa

Para coleta local:

```bash
python3 Tarefa-17/coletar_mpi.py \
  --repeats 3 \
  --sizes 1000x1000 2000x2000 4000x2000 8000x4000 \
  --processes 1 2 4

python3 Tarefa-17/gerar_relatorio.py
```

Para o NPAD:

```bash
cd Tarefa-17
sbatch run_npad.sbatch
```

Antes de enviar ao NPAD, ajustar `run_npad.sbatch` para incluir os tamanhos maiores
que couberem na memoria disponivel.

## Criterios para considerar a tarefa correta

- O programa MPI compila com `mpicc -O3 -Wall -Wextra`.
- `M` e divisivel pelo numero de processos testado.
- O checksum MPI bate com o checksum sequencial para cada tamanho.
- O CSV contem tempo sequencial, tempo MPI total, tempos parciais e as duas familias
  de speedup.
- O relatorio explica que `speedup_seq < 1` nao significa erro de calculo; significa
  que comunicacao e sincronizacao custaram mais que o ganho de paralelismo naquele
  ambiente/tamanho.
- Os graficos indicam claramente se mostram `speedup_seq` ou `speedup_mpi`.

## Conclusao

A solucao funcional da Tarefa 17 esta correta quando os checksums batem e as
coletivas exigidas sao usadas. A correcao principal e metodologica: medir o tempo MPI
pelo maior tempo entre processos, separar comunicacao de calculo e reportar
`speedup_seq` e `speedup_mpi` separadamente.

Com isso, o relatorio passa a responder corretamente ao enunciado: ele mostra o
custo da estrategia MPI completa e tambem a escalabilidade interna da versao
paralela conforme o numero de processos aumenta.
