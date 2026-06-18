# Analise atual para entrega das questoes 9 a 21

Data da revisao: 2026-06-18.

Escopo: reavaliacao do estado atual depois das correcoes feitas nas tarefas 13,
14, 16, 17, 18, 19 e 20, usando os enunciados em `questoes/`, os artefatos
existentes nas pastas `Tarefa-*`, `AULA-01-P-GPU/tarefa-20`,
`Aula-P-GPU/tarefa-20` e os relatorios em `relatorios/`.

Observacao de formato: os relatorios centrais `relatorios/relatorio_tarefa*.md`
foram padronizados para terminar com os codigos fonte C usados nos testes e, em
seguida, os scripts `sbatch` do NPAD quando existem.

## Resumo executivo atualizado

| Questao | Status atual | Falta para entrega? |
|---:|---|---|
| 9 | Concluida | Nao. Apenas melhorias opcionais de texto/reprodutibilidade. |
| 10 | Concluida | Nao. Apenas melhorias opcionais de metodologia. |
| 11 | Concluida | Nao. Opcional: explicitar casos `zero` e `uniform` no relatorio. |
| 12 | Concluida | Nao. Opcional: detalhar hardware/topologia do NPAD. |
| 13 | Concluida | Nao para Markdown/PNG/PDF; ja ha CSV, graficos e relatorio. |
| 14 | Concluida | Nao. `MPI_Rsend` foi corrigido e documentado. |
| 15 | Concluida | Nao. Melhorias de medicao sao opcionais. |
| 16 | Concluida | Nao. Ressalva de eficiencia foi explicada. |
| 17 | Concluida | Nao para Markdown/CSV; conferir PDF apenas se ele for exigido. |
| 18 | Concluida | Nao para Markdown/CSV; conferir PDF apenas se ele for exigido. |
| 19 | Concluida | Nao para Markdown/PNG/PDF; ja ha resultados NPAD e relatorio. |
| 20 | Parcial | Sim: ainda faltam medicoes reais GPU/`nsys` e artefatos de comparacao. |
| 21 | Parcial | Sim: pasta pronta; falta execucao GPU/`nsys`, comparacao e resultados. |

## Pendencias obrigatorias ou de alto impacto

### 1. Tarefa 21

Status: parcial.

A pasta `Tarefa-21/` foi criada e esta pronta para submissao no NPAD. Ela contem:

- `heat_cpu.c`: referencia CPU;
- `heat_target_baseline.c`: baseline GPU com `map(tofrom)` por passo;
- `heat_target_resident.c`: versao otimizada com `target enter data` e
  `target exit data`, mantendo `u` e `u_tmp` residentes na GPU durante o laco
  temporal;
- `run_npad.sbatch`: compila e executa CPU, baseline GPU e GPU residente;
- `run_nsys_npad.sbatch`: perfila baseline e/ou residente com `nsys`;
- `comparar_resultados.py`: gera comparacao a partir de CSVs reais;
- `relatorios/relatorio_tarefa21.md`: relatorio inicial com codigos C e scripts
  `sbatch` anexados.

Validacao local feita: compilacao com `gcc -O2 -fopenmp` e execucao host com
`OMP_TARGET_OFFLOAD=DISABLED` para `N=100`, `nsteps=10`; as tres variantes
retornaram `Error (L2norm): 4.015950E-09`. Isso valida sintaxe e consistencia
numerica basica, mas nao valida offload real.

Para entregar, ainda precisa:

- executar em GPU no NPAD;
- gerar `Tarefa-21/resultados/heat_resultados_<job_id>.csv`;
- executar `Tarefa-21/comparar_resultados.py`;
- gerar `comparacao_heat_resumo.csv` e `comparacao_heat.md`;
- rodar `run_nsys_npad.sbatch`;
- comparar baseline e residente no `nsys`, mostrando reducao de copias.

### 2. Tarefa 20

Status: parcial.

Existe codigo e documentacao em `AULA-01-P-GPU/tarefa-20`, com `heat.c`,
`heat_target.c`, scripts SLURM e relatorio em `relatorios/relatorio_tarefa20.md`.
A validacao local confirmou compilacao e resultado numerico no host, mas a pasta
`AULA-01-P-GPU/tarefa-20/resultados/` ainda tem apenas `.gitkeep`.

Para entregar completamente, precisa rodar em ambiente com GPU/NVHPC/`nsys`:

- gerar `resultados/heat_resultados_<job_id>.csv`;
- executar `comparar_resultados.py`;
- gerar `comparacao_heat.md`, resumo CSV e graficos;
- executar `run_nsys_npad.sbatch`;
- preservar `.nsys-rep`, `.sqlite` ou pelo menos o resumo textual de `nsys stats`.

Nao foi identificada necessidade de alterar a pasta da Tarefa 20 antes da execucao:
`AULA-01-P-GPU/tarefa-20/run_npad.sbatch` e
`AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch` ja compilam com NVHPC, usam
`OMP_TARGET_OFFLOAD=MANDATORY`, salvam CSV/logs e direcionam os perfis para
`resultados/perfis/`.

### 3. Tarefa 13

Status: concluida em Markdown/PNG/PDF.

Foram gerados:

- `Tarefa-13/resultados/relatorio_tarefa13.md`;
- `Tarefa-13/resultados/affinity_elapsed.png`;
- `Tarefa-13/resultados/affinity_speedup.png`;
- `relatorios/relatorio_tarefa13.md`;
- `relatorios/tarefa13_affinity_elapsed.png`;
- `relatorios/tarefa13_affinity_speedup.png`.

Tambem existe `Tarefa-13/resultados/relatorio_tarefa13.pdf`.

### 4. Tarefa 19

Status: concluida em Markdown/PNG/PDF.

O relatorio principal foi atualizado com os resultados reais de NPAD:

- CPU media `0.108146763s`;
- GPU media `0.125197220s`;
- `errors = 0`;
- speedup GPU vs CPU `0.864x`;
- ressalva de que a linha CPU usa `OMP_NUM_THREADS=1`.

Foram sincronizados:

- `Tarefa-19/relatorio_tarefa19.md`;
- `relatorios/relatorio_tarefa19.md`;
- `relatorios/tarefa19_tempo_computacao.png`;
- `relatorios/tarefa19_speedup_gpu_vs_cpu.png`;
- `relatorios/tarefa19_componentes_tempo_total.png`.

Tambem existe `Tarefa-19/resultados/relatorio_tarefa19_resultados.pdf`.

## Pendencias condicionais

### PDFs de tarefas alteradas

Os Markdown de 14, 16, 17 e 18 foram atualizados. Se o professor exige PDF, conferir
se os PDFs correspondentes representam a versao mais recente:

- Tarefa 14 e 16 ja aparecem com PDFs modificados no estado atual.
- Tarefa 17 e 18 tem Markdown atualizado; conferir se os PDFs locais representam a
  versao nova antes de entregar.

### Artefatos locais nao essenciais

Foram encontrados artefatos locais que nao sao entrega principal:

- `AULA-01-P-GPU/tarefa-20/bin/`;
- `__pycache__/` em algumas tarefas;
- binarios em `build/`.

Eles nao bloqueiam a entrega, mas vale decidir se devem ficar fora do pacote final.

## Tarefas que nao precisam de acao para entrega

### Tarefa 14

Status atualizado: concluida.

O problema antigo de `MPI_Rsend` foi corrigido: o receptor agora posta `MPI_Irecv`
antes de avisar o emissor, e o relatorio explica a regra do ready send. Ha CSV,
graficos, relatorio local e relatorio na raiz.

### Tarefa 16

Status atualizado: concluida.

O relatorio agora diferencia eficiencia por trabalhadores e por processos totais,
explica o baseline sequencial e contextualiza speedups superlineares.

### Tarefa 17

Status atualizado: concluida.

O programa MPI coletivo agora reporta tempo total pelo maior tempo entre ranks,
tempos parciais (`Bcast`, `Scatter`, computacao, `Gather`, validacao), speedup
contra sequencial e speedup interno MPI. O CSV e o Markdown foram atualizados.

### Tarefa 18

Status atualizado: concluida.

As versoes por colunas agora documentam a diferenca entre `cols_vector` e
`cols_resized`. O codigo passa a reportar `tempo_max` e tempos por fase em novas
execucoes, e o relatorio deixa claro que o CSV atual ainda e do formato antigo.

## Prioridade recomendada

1. Rodar a Tarefa 20 no NPAD com GPU/`nsys`.
2. Rodar a Tarefa 21 no NPAD com GPU/`nsys`.
3. Conferir/regenerar PDFs das tarefas alteradas, se PDF for parte obrigatoria da
   entrega.

## Tarefas que ainda precisam rodar no NPAD

- Tarefa 20: precisa de execucao real em GPU e perfil `nsys`.
- Tarefa 21: a pasta ja esta preparada; precisa ser executada em GPU com perfil
  `nsys`.

As tarefas 12, 13 e 19 ja possuem resultados de NPAD versionados. As tarefas 14 a
18 sao MPI e podem ser validadas localmente ou no cluster, mas nao estao bloqueadas
por uma rodada NPAD especifica no estado atual da entrega.
