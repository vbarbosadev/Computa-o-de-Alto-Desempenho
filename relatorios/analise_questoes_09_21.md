# Analise das questoes 9 a 21

Data da revisao: 2026-06-18.

Escopo: leitura dos enunciados em `questoes/tarefa09.md` a
`questoes/tarefa21.md`, confronto com os materiais em `conteudos/` e verificacao
estatica dos codigos, relatorios e resultados existentes. Nao foram submetidos jobs
ao NPAD, nao foram regenerados benchmarks e nao foram sobrescritos resultados.

## Tarefas que deveriam ser rodadas no NPAD

Pelo criterio de executar no NPAD apenas quando o enunciado pede explicitamente, as
seguintes tarefas entram como execucao obrigatoria no NPAD:

- Tarefa 12: o enunciado pede avaliar escalabilidade em um no de computacao do NPAD.
- Tarefa 13: o enunciado pede usar o mesmo no de computacao do NPAD da Tarefa 12.
- Tarefa 19: o enunciado pede executar os exercicios de GPU em um dos nos com GPU
  do NPAD.

Tarefas com ambiente especial, mas sem pedido literal de NPAD no enunciado:

- Tarefa 11: o enunciado inclui um exemplo com `srun --partition=intel-128`, entao
  pode ser rodada em ambiente Slurm/cluster, mas a palavra NPAD nao aparece no
  pedido principal.
- Tarefa 20: requer GPU e `nsys`; os scripts existentes apontam para NPAD, mas o
  enunciado nao cita NPAD literalmente.
- Tarefa 21: requer GPU para validar a otimizacao de transferencia, mas o enunciado
  nao cita NPAD literalmente.

## Organizacao dos subagentes

| Grupo | Questoes | Tipo de tarefa | Foco |
|---|---:|---|---|
| OpenMP / sincronizacao | 9, 10 | Regioes criticas, locks, atomic e reduction | Integridade de dados, contencao e escolha de sincronizacao |
| OpenMP / escalonamento | 11, 12, 13 | Navier-Stokes simplificado, escalabilidade e afinidade | `schedule`, `collapse`, forte/fraca, afinidade |
| MPI | 14, 15, 16, 17, 18 | Comunicacao ponto a ponto, nao bloqueante, coletivas e tipos derivados | Corretude MPI, deadlock, metricas de desempenho |
| GPU / OpenMP offload | 19, 20, 21 | Offload OpenMP em GPU no NPAD | `target`, `map`, `target data`, `nsys` |

## Resumo executivo

| Questao | Status | Avaliacao curta |
|---:|---|---|
| 9 | Concluida | Critical nomeado e locks explicitos implementados; boa discussao de contencao. |
| 10 | Concluida | Cinco versoes comparadas; roteiro de sincronizacao esta bem alinhado ao enunciado. |
| 11 | Concluida | Navier-Stokes simplificado validado e comparacao de `schedule`/`collapse` documentada. |
| 12 | Concluida | Tem codigo, coleta NPAD, CSV, graficos e relatorio. Melhorias sao de documentacao/topologia. |
| 13 | Parcial | Infraestrutura pronta, mas falta resultado versionado de NPAD. |
| 14 | Quase concluida | Benchmark completo, mas `MPI_Rsend` precisa ajuste conceitual ou ressalva forte. |
| 15 | Concluida | Tres versoes MPI implementadas e comparadas; melhorias sao metodologicas. |
| 16 | Concluida com ressalva | Lider-trabalhador correto, mas eficiencia maior que 1 precisa explicacao ou revisao. |
| 17 | Concluida com ressalva | Coletivas corretas; speedup deve ser contextualizado por custo de comunicacao. |
| 18 | Concluida com ressalva | Tipos derivados corretos; `cols_vector` mede sem custo de buffer artificial. |
| 19 | Concluida com ajuste pendente | Resultados NPAD existem; relatorio principal ainda diz que faltava execucao. |
| 20 | Parcial | Codigo e scripts existem, mas faltam CSV, relatorio comparativo e perfil `nsys`. |
| 21 | Nao concluida | Nao ha pasta/codigo especifico; falta versao otimizada com dados residentes na GPU. |

## Referencias usadas

- `conteudos/08-Memoria_Compartilhada_OPENMP.pptx (1).pdf`: base OpenMP,
  regioes paralelas, lacos e variaveis.
- `conteudos/16-OPENMP_Diviso_de_trabalho (2).pdf` e
  `conteudos/16-OPENMP_Diviso_de_trabalho (3).pdf`: `schedule`, `collapse` e
  divisao de trabalho.
- `analise/openmp_diretivas_e_clausulas.md`: apoio local sobre `critical`,
  `atomic`, `reduction`, locks e diretivas OpenMP.
- `conteudos/Programao_Paralela (1).pdf`: speedup e eficiencia.
- `conteudos/Computao_de_Alto_Desempenho (1).pdf`: contexto de memoria/cache e
  gargalos de desempenho.
- `conteudos/21-_Introduo_-_MPI.pdf`: `MPI_Send`, `MPI_Recv`, ranks,
  comunicadores e `MPI_Wtime`.
- `conteudos/22-_MPI_-_Comunicacao_Nao_Bloqueante.pdf`: `MPI_Isend`,
  `MPI_Irecv`, `MPI_Wait` e `MPI_Test`.
- `conteudos/23-_MPI_-_Deadlock.pdf`: cuidados contra deadlock e alternativas
  como comunicacao nao bloqueante.
- `conteudos/24-_MPI_-_Comunicao_Coletiva (1).pdf`: `MPI_Bcast`,
  `MPI_Scatter`, `MPI_Gather` e `MPI_Reduce`.
- `conteudos/25-_MPI_TYPE (1).pdf`: `MPI_Type_vector` e
  `MPI_Type_create_resized`.
- `conteudos/omp_GPGPU_prog_SC23.pdf`: exercicios `vadd.c`, `heat.c`,
  `target`, `map`, `target data`, `target update` e perfil com `nsys`.

## Tarefa 9 - Regioes criticas nomeadas e travas explicitas

Tipo: OpenMP / sincronizacao.

O enunciado pede criar insercoes em duas listas encadeadas, proteger a integridade
com regioes criticas nomeadas para que uma lista nao bloqueie a outra, depois
generalizar para um numero de listas definido pelo usuario e explicar por que
`critical` nomeado nao basta nesse caso.

Arquivos encontrados:

- `Tarefa-09/lists_critical.c`
- `Tarefa-09/lists_lock.c`
- `Tarefa-09/run_tests.py`
- `Tarefa-09/run_tests.sh`
- `Tarefa-09/dados/tarefa9_runs.csv`
- `Tarefa-09/dados/tarefa9_summary.json`
- `Tarefa-09/dados/relatorio_tarefa09.md`
- `relatorios/relatorio_tarefa09.md`
- `relatorios/tarefa9_resultados.png`

Status: concluida.

Aderencia: boa. A primeira versao usa `#pragma omp critical(lista_a)` e
`#pragma omp critical(lista_b)` para duas listas fixas, preservando paralelismo
entre listas diferentes. A segunda usa `omp_lock_t locks[K]`, com
`omp_init_lock`, `omp_set_lock`, `omp_unset_lock` e `omp_destroy_lock`, permitindo
K listas definido em tempo de execucao.

Evidencia de conclusao: ha runner, CSV, JSON de resumo, grafico e relatorio. O
relatorio informa 1.000.000 insercoes, 10 rodadas por configuracao, threads 1, 2,
4, 8 e 12, e validacao de que o total inserido sempre bate com a soma das listas.

Pontos corretos importantes:

- A explicacao de que nomes de `critical` sao identificadores estaticos de codigo
  esta correta; nao ha como criar `critical(lista_k)` dinamicamente com K em tempo
  de execucao.
- A conclusao de que `omp_lock_t` e uma escolha de flexibilidade/granularidade, nao
  necessariamente de velocidade, esta bem sustentada pelos resultados.
- O relatorio aponta corretamente que aumentar threads com apenas 2 listas aumenta
  contencao, enquanto aumentar K reduz colisoes.

Pontos a corrigir ou melhorar:

- A frase do enunciado "cada lista associada a uma thread" e ambigua. O codigo
  interpreta como threads escolhendo aleatoriamente entre listas compartilhadas,
  que e coerente com o restante do enunciado; ainda assim, vale mencionar essa
  interpretacao no relatorio.
- O uso de `malloc` dentro da regiao protegida pode adicionar contencao da libc e
  misturar custo de alocacao com custo do lock. O relatorio ja cita esse efeito,
  mas poderia propor uma versao com pool/prealocacao para isolar melhor o custo de
  sincronizacao.
- As seeds usam `time(NULL)` combinado com id da thread; isso e suficiente para a
  tarefa, mas nao garante reprodutibilidade perfeita entre rodadas. Registrar seed
  base fixa ajudaria em comparacoes.

## Tarefa 10 - Critical, atomic, privados e reduction no estimador de PI

Tipo: OpenMP / sincronizacao e reducao.

O enunciado pede reimplementar o estimador da Tarefa 8 com contador compartilhado e
`rand_r`, trocar `critical` por `atomic`, comparar com versoes de contadores
privados, adicionar uma versao com `reduction`, e propor um roteiro de escolha entre
mecanismos de sincronizacao, incluindo critical nomeadas e locks explicitos.

Arquivos encontrados:

- `Tarefa-10/pi_randr_shared_critical.c`
- `Tarefa-10/pi_randr_shared_atomic.c`
- `Tarefa-10/pi_randr_private_critical.c`
- `Tarefa-10/pi_randr_private_vector.c`
- `Tarefa-10/pi_randr_reduction.c`
- `Tarefa-10/portable_rand_r.h`
- `Tarefa-10/run_tests.py`
- `Tarefa-10/generate_plot.py`
- `Tarefa-10/dados/tarefa10_runs.csv`
- `Tarefa-10/dados/tarefa10_summary.json`
- `Tarefa-10/relatorios/relatorio_tarefa10.md`
- `Tarefa-10/relatorios/tarefa10_resultados.png`
- `relatorios/relatorio_tarefa10.md`

Status: concluida.

Aderencia: boa. As cinco versoes pedidas existem e usam `rand_r()` com seed privada
por thread. O benchmark cobre 1, 2, 4, 8 e 12 threads, 10 rodadas por configuracao e
N = 10.000.000 pontos.

Evidencia de conclusao: ha CSV, JSON, grafico e relatorio. O resumo valida
`count <= N`, `total == N`, parse correto das saidas e erro numerico de Monte Carlo
em faixa esperada.

Pontos corretos importantes:

- A comparacao mostra corretamente que trocar `critical` por `atomic` melhora o
  incremento simples, mas nao resolve a contencao estrutural de um contador global.
- `private_critical` e `reduction` aparecem como melhores alternativas porque
  removem sincronizacao por iteracao.
- O roteiro final esta alinhado ao conteudo de OpenMP: `reduction` para somas
  associativas, `atomic` para operacoes simples, `critical` para blocos curtos,
  `critical(nome)` para poucos recursos fixos e `omp_lock_t` para recursos
  dinamicos.

Pontos a corrigir ou melhorar:

- `private_vector` e discutido como afetado por false sharing, mas nao ha versao com
  padding/alinhamento para confirmar a causa. Uma melhoria seria adicionar uma
  variante `private_vector_padded`.
- Em 12 threads, `private_critical` e `reduction` variam bastante entre min e max;
  reportar mediana junto da media deixaria a comparacao mais robusta.
- Como a tarefa e sobre mecanismos de sincronizacao, seria util incluir uma tabela
  separando "frequencia de sincronizacao" de "tipo de primitiva", pois esse e o
  principal aprendizado dos resultados.

## Tarefa 11 - Escalonamento com Navier-Stokes simplificado

Tipo: OpenMP / escalonamento.

O enunciado pede implementar uma simulacao de fluido ao longo do tempo usando
Navier-Stokes com apenas viscosidade, validar estabilidade com campo parado/constante
e perturbacao, depois paralelizar com OpenMP e explorar `schedule` e `collapse`.

Arquivos encontrados:

- `Tarefa-11/navier_stokes_viscosidade.c`
- `Tarefa-11/coletar_resultados.py`
- `Tarefa-11/run_tests.py`
- `Tarefa-11/resultados/resultados.csv`
- `Tarefa-11/resultados/schedules_8threads.png`
- `Tarefa-11/resultados/speedup_static_collapse2.png`
- `relatorios/relatorio_tarefa11.md`
- `relatorios/tarefa11_schedules_8threads.png`
- `relatorios/tarefa11_speedup_static_collapse2.png`

Status: concluida.

Aderencia: boa. O codigo implementa uma equacao de difusao 2D para uma componente
escalar de velocidade, com pressao, forcas externas e conveccao desconsideradas,
como pede o enunciado. Usa dois buffers, diferencas finitas, criterio de
estabilidade `dt * nu <= 0.25`, modos sequencial/OpenMP, `schedule(runtime)` e
opcao `collapse` 1 ou 2.

Evidencia de conclusao: ha CSV de resultados, relatorio, graficos e validacao
numerica. A perturbacao permanece estavel e se difunde suavemente; maximo e norma
L2 diminuem, e as versoes OpenMP preservam os mesmos resultados finais.

Pontos corretos importantes:

- A discussao de `schedule(static)` como melhor escolha para stencil regular esta
  correta.
- A conclusao de que `collapse(2)` piorou neste caso e bem fundamentada: o laco
  externo ja tinha iteracoes suficientes e o collapse aumentou overhead/prejudicou
  localidade.
- O melhor resultado reportado, `static collapse=1` com 8 threads, speedup medio em
  torno de `2.87x`, e coerente com o gargalo de memoria de um stencil 2D.

Pontos a corrigir ou melhorar:

- O enunciado tambem menciona fluido parado ou velocidade constante. O codigo tem
  `--init zero|uniform|perturb`, mas o relatorio foca na perturbacao. Incluir uma
  tabela curta validando `zero` e `uniform` deixaria a aderencia mais completa.
- O codigo chama uma regiao paralela a cada passo de tempo. A Tarefa 12 melhora isso
  com `omp-region`; vale apontar no relatorio da 11 que essa e uma versao inicial.
- O relatorio poderia separar tempo do kernel de atualizacao e tempo de aplicacao de
  bordas para explicar melhor gargalos.

## Tarefa 12 - Escalabilidade do Navier-Stokes

Tipo: OpenMP / NPAD.

O enunciado pede avaliar a escalabilidade do codigo de Navier-Stokes em um no de
computacao do NPAD, identificar gargalos e comentar escalabilidade forte e fraca de
versoes sucessivas.

Arquivos encontrados:

- `Tarefa-12/navier_scaling.c`
- `Tarefa-12/coletar_npad.py`
- `Tarefa-12/gerar_relatorio.py`
- `Tarefa-12/run_npad.sbatch`
- `Tarefa-12/resultados/tarefa12_resultados.csv`
- `Tarefa-12/resultados/strong_scaling.png`
- `Tarefa-12/resultados/weak_scaling.png`
- `Tarefa-12/resultados/relatorio_tarefa12.md`
- `relatorios/relatorio_tarefa12.md`

Status: concluida.

Aderencia: boa. A entrega compara `omp-basic` e `omp-region`, mede 1 a 32
threads, inclui escalabilidade forte e fraca, valida estabilidade numerica e tem
logs Slurm. O melhor caso forte reportado para `omp-region` ocorre em 16 threads,
com cerca de `1.754s` e speedup `3.70x`; em 32 threads ha saturacao. Na fraca, a
eficiencia cai ate cerca de `0.06`, coerente com gargalo de memoria/sincronizacao.

Pontos a corrigir ou melhorar:

- Explicitar no relatorio que o codigo e um Navier-Stokes simplificado por
  difusao/viscosidade, sem pressao, forcas externas ou termo convectivo.
- Registrar identificacao do no/CPU do NPAD, modulos carregados e, se possivel,
  `lscpu` ou `numactl --hardware`.
- Aprofundar a explicacao da escalabilidade fraca ruim com topologia, cache,
  largura de banda de memoria e afinidade.

## Tarefa 13 - Afinidades de threads

Tipo: OpenMP / NPAD.

O enunciado pede avaliar como a escalabilidade do Navier-Stokes muda com afinidades
de threads do sistema operacional e do OpenMP, no mesmo no do NPAD usado na Tarefa
12.

Arquivos encontrados:

- `Tarefa-13/navier_scaling.c`
- `Tarefa-13/coletar_afinidade.py`
- `Tarefa-13/gerar_relatorio.py`
- `Tarefa-13/run_npad.sbatch`
- `Tarefa-13/README_NPAD.md`

Status: parcial.

Aderencia: a infraestrutura esta bem alinhada. O script testa `sem_bind`,
`close_cores`, `spread_cores`, `close_threads`, `spread_threads` e
`gomp_cpu_affinity`, usando `OMP_PROC_BIND`, `OMP_PLACES` e `GOMP_CPU_AFFINITY`.
Ele reaproveita o modo `omp-region`, malha fixa e variacao de threads.

O que falta:

- Executar no NPAD, pois o enunciado pede explicitamente esse ambiente.
- Versionar `Tarefa-13/resultados/tarefa13_afinidade.csv`.
- Gerar `affinity_elapsed.png`, `affinity_speedup.png` e
  `relatorio_tarefa13.md`.
- Registrar se o no e o mesmo da Tarefa 12.

Pontos a corrigir ou melhorar:

- Se o professor espera afinidade via sistema operacional/Slurm, acrescentar casos
  ou discussao com `taskset`, `numactl` ou `srun --cpu-bind`.
- Incluir no relatorio a topologia do no e a politica de binding aplicada pelo
  Slurm.

## Tarefa 14 - Comunicacao MPI

Tipo: MPI ponto a ponto.

O enunciado pede quatro programas com exatamente dois processos, usando
`MPI_Send`, `MPI_Bsend`, `MPI_Rsend` e `MPI_Ssend`, medindo varias trocas com
`MPI_Wtime`, variando tamanho de mensagem e analisando latencia e largura de banda.

Arquivos encontrados:

- `Tarefa-14/mpi_send.c`
- `Tarefa-14/mpi_bsend.c`
- `Tarefa-14/mpi_rsend.c`
- `Tarefa-14/mpi_ssend.c`
- `Tarefa-14/coletar_mpi.py`
- `Tarefa-14/gerar_relatorio.py`
- `Tarefa-14/resultados/tarefa14_resultados.csv`
- `Tarefa-14/resultados/tempo_por_tamanho.png`
- `Tarefa-14/resultados/largura_banda.png`
- `Tarefa-14/resultados/relatorio_tarefa14.md`

Status: quase concluida.

Aderencia: boa para `MPI_Send`, `MPI_Bsend` e `MPI_Ssend`. Ha CSV com tamanhos de
8 bytes a 1 MiB, tres rodadas, graficos e discussao de latencia ate cerca de 1 KiB
e banda para mensagens maiores.

Problema principal:

- `mpi_rsend.c` usa mensagens de "pronto", mas isso nao garante formalmente que o
  `MPI_Recv` correspondente ja foi postado antes do `MPI_Rsend`. A regra do ready
  send exige que o recebimento ja esteja iniciado. O protocolo atual pode funcionar
  na pratica, mas e conceitualmente fragil.

O que precisa mudar:

- Corrigir `MPI_Rsend` usando um `MPI_Irecv` previamente postado no receptor antes
  do aviso de pronto, seguido de `MPI_Wait`.
- Alternativamente, manter o codigo e documentar explicitamente a limitacao
  conceitual, mas a correcao e preferivel.

## Tarefa 15 - Difusao de calor 1D

Tipo: MPI ponto a ponto e comunicacao nao bloqueante.

O enunciado pede uma simulacao de difusao de calor em barra 1D dividida entre
processos, com celulas fantasmas e tres versoes: `MPI_Send/MPI_Recv`,
`MPI_Isend/MPI_Irecv + MPI_Wait` e `MPI_Test` para sobrepor comunicacao e
computacao.

Arquivos encontrados:

- `Tarefa-15/heat_send_recv.c`
- `Tarefa-15/heat_isend_irecv_wait.c`
- `Tarefa-15/heat_isend_irecv_test.c`
- `Tarefa-15/coletar_mpi.py`
- `Tarefa-15/gerar_relatorio.py`
- `Tarefa-15/resultados/tarefa15_resultados.csv`
- `Tarefa-15/resultados/relatorio_tarefa15.md`
- graficos em `Tarefa-15/resultados/`

Status: concluida.

Aderencia: boa. As tres versoes existem, usam troca de bordas, resultados para 2 e
4 processos, tamanhos `100000` e `1000000`, e 2000 passos. A soma final constante
ajuda a validar a simulacao.

Pontos a corrigir ou melhorar:

- A versao com `MPI_Test` chama teste dentro do laco interno, o que aumenta
  overhead. Isso esta explicado no relatorio, mas pode ser melhorado testando em
  blocos maiores.
- Medir o tempo maximo entre ranks dentro do proprio programa com
  `MPI_Reduce(MPI_MAX)`, em vez de depender apenas do script externo.
- Separar tempo de comunicacao e tempo de computacao para sustentar melhor a
  discussao de sobreposicao.

## Tarefa 16 - Escalonador lider-trabalhador

Tipo: MPI dinamico / mestre-trabalhador.

O enunciado pede um escalonador dinamico em que o lider distribui tarefas conforme
os trabalhadores terminam, aplicado a contagem de primos, com avaliacao de speedup,
eficiencia e garantia contra deadlock.

Arquivos encontrados:

- `Tarefa-16/primos_seq.c`
- `Tarefa-16/leader_worker_primes.c`
- `Tarefa-16/coletar_mpi.py`
- `Tarefa-16/gerar_relatorio.py`
- `Tarefa-16/resultados/tarefa16_resultados.csv`
- `Tarefa-16/resultados/relatorio_tarefa16.md`
- graficos em `Tarefa-16/resultados/`

Status: concluida com ressalva metodologica.

Aderencia: boa. O lider usa recebimento de qualquer trabalhador com
`MPI_ANY_SOURCE`, trabalhadores recebem tarefa ou parada, e nao ha espera circular
aparente. Os resultados variam quantidade de tarefas e processos.

Problema principal:

- O relatorio mostra eficiencia acima de 1, inclusive com 1 trabalhador. Isso pode
  acontecer por diferencas de baseline, cache, variacao de medicao ou por comparar
  tempos que nao representam exatamente o mesmo custo, mas precisa ser explicado.

O que precisa mudar:

- Explicar explicitamente que a eficiencia foi calculada por numero de
  trabalhadores, nao por processos totais.
- Justificar os casos superlineares ou revisar a metodologia do baseline.
- Considerar mais repeticoes, mediana e separacao do overhead do lider.

## Tarefa 17 - Multiplicacao matriz-vetor por linhas

Tipo: MPI coletivo.

O enunciado pede calcular `y = A*x`, dividir `A` por linhas com `MPI_Scatter`,
distribuir `x` com `MPI_Bcast`, reunir `y` com `MPI_Gather`, e avaliar tempos,
speedup e eficiencia.

Arquivos encontrados:

- `Tarefa-17/matvec_seq.c`
- `Tarefa-17/matvec_collective.c`
- `Tarefa-17/coletar_mpi.py`
- `Tarefa-17/gerar_relatorio.py`
- `Tarefa-17/correcoes_speedup.md`
- `Tarefa-17/resultados/tarefa17_resultados.csv`
- `Tarefa-17/resultados/relatorio_tarefa17.md`
- graficos em `Tarefa-17/resultados/`

Status: concluida com ressalva metodologica.

Aderencia: boa. O codigo usa `MPI_Bcast`, `MPI_Scatter` e `MPI_Gather`, valida por
checksum e testa 1, 2 e 4 processos. A restricao `M % size == 0` e aceitavel para
uso simples de `MPI_Scatter`, e os casos testados respeitam essa condicao.

Pontos a corrigir ou melhorar:

- O speedup contra a versao sequencial fica menor que 1 porque o sequencial mede
  quase so computacao, enquanto o MPI mede distribuicao, broadcast, gather e
  validacao. O relatorio ja discute isso, mas a tabela deve deixar a metodologia
  muito clara.
- Medir tempos parciais: `Bcast`, `Scatter`, computacao local, `Gather` e
  validacao.
- Usar `MPI_Reduce(MPI_MAX)` para reportar o tempo paralelo pelo rank mais lento.
- Reportar tambem speedup interno MPI, por exemplo comparando 1 processo MPI contra
  2 e 4 processos MPI.

## Tarefa 18 - Multiplicacao matriz-vetor por colunas

Tipo: MPI com tipos derivados.

O enunciado pede reimplementar a Tarefa 17 distribuindo colunas, com uma versao
`MPI_Type_vector` e outra com `MPI_Type_create_resized`, espalhando blocos de
colunas e segmentos de `x`, e somando contribuicoes com `MPI_Reduce(MPI_SUM)`.

Arquivos encontrados:

- `Tarefa-18/matvec_cols_vector.c`
- `Tarefa-18/matvec_cols_resized.c`
- `Tarefa-18/coletar_mpi.py`
- `Tarefa-18/gerar_relatorio.py`
- `Tarefa-18/correcoes_speedup.md`
- `Tarefa-18/resultados/tarefa18_resultados.csv`
- `Tarefa-18/resultados/relatorio_tarefa18.md`
- graficos em `Tarefa-18/resultados/`
- `Tarefa-18-OpenMP/`, que e comparacao separada e nao substitui a entrega MPI.

Status: concluida com ressalva metodologica.

Aderencia: boa. A versao `cols_resized` usa `MPI_Type_vector` e
`MPI_Type_create_resized`, espalha `x` e blocos de matriz com `MPI_Scatter`, calcula
contribuicoes parciais e usa `MPI_Reduce` para formar `y`.

Pontos a corrigir ou melhorar:

- `cols_vector` usa buffer artificial expandido no rank 0 para compensar a extensao
  natural do tipo derivado; esse custo fica fora da medicao. Isso deve ser
  enfatizado ou medido.
- Priorizar `cols_resized` como a versao tecnicamente mais fiel ao enunciado.
- Medir tempos parciais e o tempo maximo entre ranks.
- Assim como na Tarefa 17, manter speedup contra sequencial, mas adicionar speedup
  interno MPI para interpretacao mais justa.

## Tarefa 19 - Adicao de vetores em GPU

Tipo: GPU / OpenMP offload.

O enunciado pede fazer os exercicios `vadd.c` dos slides 27 e 48 do tutorial de
GPU com OpenMP, rodar em no GPU do NPAD, comparar CPU e GPU, e relatar problemas e
solucoes.

Arquivos encontrados:

- `Tarefa-19/vadd_cpu.c`
- `Tarefa-19/vadd_gpu.c`
- `Tarefa-19/Makefile`
- `Tarefa-19/run_npad.sbatch`
- `Tarefa-19/README.md`
- `Tarefa-19/relatorio_tarefa19.md`
- `Tarefa-19/resultados/tarefa19_resultados_1858301.csv`
- `Tarefa-19/resultados/relatorio_tarefa19_resultados.md`
- graficos em `Tarefa-19/resultados/`
- versoes-base em `Aula-P-GPU/Tarefa-19/`

Status: concluida com ajuste pendente de relatorio.

Aderencia: boa. A versao GPU usa `#pragma omp target` com `#pragma omp loop` e
mapeamento explicito de `a`, `b` e `c`. Ha resultado real de NPAD: `N=100000000`,
5 repeticoes, CPU media `0.108146763s`, GPU media `0.125197220s`, `errors=0` e
speedup GPU de `0.864x`.

Pontos a corrigir:

- `Tarefa-19/relatorio_tarefa19.md` ainda diz que a execucao no NPAD nao foi feita,
  mas `Tarefa-19/resultados/relatorio_tarefa19_resultados.md` mostra execucao
  concluida. Atualizar o relatorio principal.
- A CPU foi medida com `OMP_NUM_THREADS=1`; registrar isso como baseline de uma
  thread e, se necessario, executar tambem baseline multicore.

## Tarefa 20 - Heat em GPU com OpenMP

Tipo: GPU / OpenMP offload e profiling.

O enunciado pede fazer o exercicio `heat.c` do slide 64, explorar paralelizacao e
movimentacao de dados entre host/dispositivo, testar tamanhos diferentes e perfilar
com `nsys`.

Arquivos encontrados:

- `Aula-P-GPU/tarefa-20/heat.c`
- `Aula-P-GPU/tarefa-20/heat_target.c`
- `Aula-P-GPU/tarefa-20/run_npad.sbatch`
- `Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch`
- `Aula-P-GPU/tarefa-20/comparar_resultados.py`
- `Aula-P-GPU/tarefa-20/README_NPAD.md`
- copia equivalente em `AULA-01-P-GPU/tarefa-20/`

Status: parcial.

Aderencia: o codigo esta alinhado ao exercicio-base. `heat_target.c` usa
`#pragma omp target map(tofrom: u[0:n*n], u_tmp[0:n*n])` e
`#pragma omp loop collapse(2)`, que e a versao inicial em que movimentacao de dados
ainda domina.

O que falta:

- Executar no NPAD, pois o enunciado pede profiling em GPU.
- Versionar CSVs `heat_resultados_*.csv`.
- Gerar `comparacao_heat.md`, resumo CSV e graficos.
- Rodar `nsys` e preservar `.nsys-rep`, `.sqlite` ou pelo menos o resumo textual.

Pontos a corrigir:

- Ha duas pastas quase iguais: `Aula-P-GPU/tarefa-20` e
  `AULA-01-P-GPU/tarefa-20`. Os scripts em `Aula-P-GPU/tarefa-20` entram em
  `AULA-01-P-GPU/tarefa-20` quando essa pasta existe. Isso pode gravar resultados
  na copia errada. Escolher uma pasta canonica ou corrigir o `cd` dos scripts.

## Tarefa 21 - Otimizacao de transferencia GPU/CPU

Tipo: GPU / OpenMP offload com dados residentes.

O enunciado pede fazer o exercicio `heat.c` do slide 102, usando diretivas de
movimentacao de dados para evitar que transferencias CPU/GPU dominem a execucao e
deixem a GPU ociosa.

Arquivos encontrados:

- Nao foi encontrada pasta `Tarefa-21`, `tarefa-21` ou implementacao especifica.
- O arquivo mais proximo e `Aula-P-GPU/tarefa-20/heat_target.c`, mas ele ainda usa
  `map(tofrom)` dentro de `solve()`, o que corresponde ao estagio anterior.

Status: nao concluida.

O que precisa ser feito:

- Criar uma versao otimizada, por exemplo `Tarefa-21/heat_target_data.c` ou
  `Aula-P-GPU/tarefa-21/heat_target_data.c`.
- Manter `u` e `u_tmp` residentes no dispositivo durante todo o laco temporal com
  `target data`, `target enter data`/`target exit data`, ou estrategia equivalente.
- Remover copias repetidas por passo de tempo.
- Copiar de volta apenas o vetor necessario para validacao final.
- Comparar com a Tarefa 20 usando `nsys`, mostrando reducao de copias e melhor uso
  da GPU.
- Gerar relatorio, CSV e perfis.

## Prioridade de acao

1. Tarefa 21: implementar do zero a versao otimizada de `heat.c` com dados
   residentes na GPU.
2. Tarefa 13: rodar no NPAD e gerar os resultados de afinidade.
3. Tarefa 20: rodar no NPAD com `nsys`, gerar comparacao e resolver duplicacao de
   pastas.
4. Tarefa 14: corrigir a versao `MPI_Rsend`.
5. Tarefa 19: atualizar o relatorio principal com os resultados ja existentes.
6. Tarefas 9, 10 e 11: manter como concluidas; apenas enriquecer a documentacao
   com interpretacao do enunciado da 9, mediana/padding na 10 e casos
   `zero`/`uniform` na 11.
7. Tarefas 16, 17 e 18: melhorar metodologia de desempenho e explicacao das
   metricas, sem necessidade de reescrever o nucleo funcional.
8. Tarefa 12: apenas enriquecer documentacao sobre hardware/topologia e limite do
   modelo fisico.
