# Passo a passo NPAD das pendencias 9 a 21

Data: 2026-06-18.

Este arquivo cobre apenas as tarefas que ainda precisam de execucao no NPAD para
fechar a entrega atual. As tarefas 12, 13 e 19 ja possuem resultados NPAD
versionados. As tarefas 9, 10, 11, 14, 15, 16, 17 e 18 nao estao bloqueadas por
nova execucao NPAD no estado atual.

## Resumo

| Tarefa | Precisa rodar no NPAD? | Motivo |
|---:|---|---|
| 20 | Sim | Falta medicao real em GPU, comparacao CPU/GPU e perfil `nsys`. |
| 21 | Sim | Falta validar em GPU a versao otimizada com dados residentes e perfilar com `nsys`. |

## Preparacao comum

No NPAD, entre no diretorio raiz do repositorio:

```bash
cd /caminho/para/CAD
```

Confirme que o SLURM esta disponivel:

```bash
sinfo
squeue -u "$USER"
```

As tarefas GPU usam NVHPC. Os scripts carregam o modulo:

```bash
module load compilers/nvidia/nvhpc/24.11
```

Se esse modulo nao existir no ambiente ativo, verificar os nomes disponiveis:

```bash
module avail nvhpc
module avail compilers
```

Se um script Python falhar com erro parecido com
`SyntaxError: future feature annotations is not defined`, o Python do NPAD e antigo.
Use uma versao mais nova, se disponivel:

```bash
module avail python
module load python/3.10
```

Se nao houver Python novo, use os scripts compatibilizados do repositorio atual.
Eles evitam `from __future__ import annotations`, `dataclasses` e anotacoes modernas
de tipo.

## Tarefa 20 - heat CPU x GPU com OpenMP target

Pasta canonica:

```text
AULA-01-P-GPU/tarefa-20
```

### 1. Rodar comparacao CPU/GPU

Da raiz do repositorio:

```bash
sbatch AULA-01-P-GPU/tarefa-20/run_npad.sbatch
```

O script usa por padrao:

```text
partition=gpu-4-a100
gpus-per-node=1
cpus-per-task=8
CASES="1000:10 2000:20 4000:40"
REPEATS=3
OMP_TARGET_OFFLOAD=MANDATORY
```

Para trocar particao ou casos:

```bash
CASES="500:10 1000:10 2000:20" REPEATS=5 \
  sbatch --partition=gpu-8-v100 AULA-01-P-GPU/tarefa-20/run_npad.sbatch
```

### 2. Acompanhar job

```bash
squeue -u "$USER"
sacct -u "$USER" --starttime today --format=JobID,JobName%20,Partition,State,ExitCode,Elapsed,Reason
```

Logs esperados:

```text
AULA-01-P-GPU/tarefa-20/resultados/tarefa20-<job_id>.out
AULA-01-P-GPU/tarefa-20/resultados/tarefa20-<job_id>.err
```

CSV esperado:

```text
AULA-01-P-GPU/tarefa-20/resultados/heat_resultados_<job_id>.csv
```

### 3. Gerar comparacao

Depois que o job terminar:

```bash
cd AULA-01-P-GPU/tarefa-20
python3 comparar_resultados.py
```

Se o Python do NPAD ainda for antigo e o script falhar, atualizar
`AULA-01-P-GPU/tarefa-20/comparar_resultados.py` com a versao compatibilizada deste
repositorio e rodar novamente:

```bash
python3 comparar_resultados.py
```

Artefatos esperados:

```text
resultados/comparacao_heat_resumo.csv
resultados/comparacao_heat.md
resultados/tempo_solve_cpu_gpu.png
resultados/speedup_solve_cpu_gpu.png
```

Se `matplotlib` nao estiver instalado, o script pode gerar apenas Markdown e CSV. Os
PNGs nao sao bloqueantes se `comparacao_heat.md` e `comparacao_heat_resumo.csv`
foram gerados.

### 4. Rodar perfil com nsys

Da raiz do repositorio:

```bash
sbatch AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Para perfilar um caso maior:

```bash
N=2000 NSTEPS=20 sbatch AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Para perfilar CPU e GPU:

```bash
PROFILE_VARIANT=both sbatch AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Se o job aparecer como `FAILED` mas o log mostrar que `nsys profile` gerou
`.nsys-rep` e `.sqlite`, o perfil ja foi coletado. Um caso observado foi falha no
comando final `nsys stats` por SQLite existente ou ausencia de NVTX:

```text
SKIPPED: ...sqlite does not contain NV Tools Extension (NVTX) data
WARNING: Existing SQLite export found
usage: nsys stats [<args>] <input-file>
```

Para evitar que isso marque o job como falho em uma nova rodada, ajustar o script no
NPAD:

```bash
cd /caminho/para/CAD
perl -0pi -e 's/nsys stats "\$\{output\}\.nsys-rep"/nsys stats --force-export=true "\$\{output\}.nsys-rep" || true/g' \
  AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Depois rerodar:

```bash
PROFILE_VARIANT=both N=1000 NSTEPS=10 sbatch AULA-01-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Artefatos esperados:

```text
AULA-01-P-GPU/tarefa-20/resultados/perfis/nsys_heat_gpu_*.nsys-rep
AULA-01-P-GPU/tarefa-20/resultados/perfis/nsys_heat_gpu_*.sqlite
AULA-01-P-GPU/tarefa-20/resultados/nsys-<job_id>.out
```

No resumo `nsys`, procurar:

```text
CUDA Kernel Statistics
CUDA Memory Operation Statistics
```

### 5. O que anexar/registrar na entrega

- CSV bruto `heat_resultados_<job_id>.csv`;
- `comparacao_heat.md`;
- `comparacao_heat_resumo.csv`;
- graficos gerados;
- resumo textual do `nsys` ou arquivos `.nsys-rep`/`.sqlite`;
- observacao sobre custo de transferencia causado por `map(tofrom)` dentro da
  versao baseline.

Dados importantes a extrair do `nsys` da Tarefa 20:

- `Solve time` e `Total time` impressos pelo programa;
- quantidade de `cuLaunchKernel`;
- quantidade e volume de `CUDA memcpy Host-to-Device`;
- quantidade e volume de `CUDA memcpy Device-to-Host`.

Na execucao ja observada de `N=1000`, `NSTEPS=10`, o perfil GPU indicou 10 kernels e
20 copias HtoD + 20 copias DtoH, com 160 MB em cada direcao. Isso confirma que a
baseline da Tarefa 20 transfere dados repetidamente.

## Tarefa 21 - heat com dados residentes na GPU

Pasta:

```text
Tarefa-21
```

Variantes preparadas:

- `cpu`: referencia CPU em `heat_cpu.c`;
- `gpu_baseline`: baseline GPU com `map(tofrom)` por passo, em
  `heat_target_baseline.c`;
- `gpu_resident`: versao otimizada com dados residentes no dispositivo, em
  `heat_target_resident.c`.

### 1. Rodar comparacao CPU/GPU baseline/GPU residente

Da raiz do repositorio:

```bash
sbatch Tarefa-21/run_npad.sbatch
```

O script usa por padrao:

```text
partition=gpu-4-a100
gpus-per-node=1
cpus-per-task=8
CASES="1000:10 2000:20 4000:40"
REPEATS=3
OMP_TARGET_OFFLOAD=MANDATORY
```

Para trocar particao ou casos:

```bash
CASES="1000:10 2000:50 4000:100" REPEATS=5 \
  sbatch --partition=gpu-8-v100 Tarefa-21/run_npad.sbatch
```

### 2. Acompanhar job

```bash
squeue -u "$USER"
sacct -u "$USER" --starttime today --format=JobID,JobName%20,Partition,State,ExitCode,Elapsed,Reason
```

Logs esperados:

```text
Tarefa-21/resultados/tarefa21-<job_id>.out
Tarefa-21/resultados/tarefa21-<job_id>.err
```

CSV esperado:

```text
Tarefa-21/resultados/heat_resultados_<job_id>.csv
```

### 3. Gerar comparacao

Depois que o job terminar:

```bash
cd Tarefa-21
python3 comparar_resultados.py
```

Se aparecer o mesmo erro de Python antigo, atualizar `Tarefa-21/comparar_resultados.py`
com a versao compatibilizada do repositorio atual ou carregar Python mais novo:

```bash
module avail python
module load python/3.10
python3 comparar_resultados.py
```

Artefatos esperados:

```text
resultados/comparacao_heat_resumo.csv
resultados/comparacao_heat.md
```

O relatorio deve comparar:

- CPU versus `gpu_baseline`;
- CPU versus `gpu_resident`;
- `gpu_baseline` versus `gpu_resident`.

### 4. Rodar perfil com nsys

Da raiz do repositorio, para perfilar apenas a versao residente:

```bash
sbatch Tarefa-21/run_nsys_npad.sbatch
```

Para perfilar baseline e residente no mesmo job:

```bash
PROFILE_VARIANT=both N=2000 NSTEPS=20 sbatch Tarefa-21/run_nsys_npad.sbatch
```

Se o `nsys stats` falhar depois de gerar `.nsys-rep`/`.sqlite`, aplicar a mesma
correcao usada na Tarefa 20:

```bash
cd /caminho/para/CAD
perl -0pi -e 's/nsys stats "\$\{output\}\.nsys-rep"/nsys stats --force-export=true "\$\{output\}.nsys-rep" || true/g' \
  Tarefa-21/run_nsys_npad.sbatch
```

Artefatos esperados:

```text
Tarefa-21/resultados/perfis/nsys_heat_baseline_*.nsys-rep
Tarefa-21/resultados/perfis/nsys_heat_resident_*.nsys-rep
Tarefa-21/resultados/nsys-<job_id>.out
```

No resumo `nsys`, comparar principalmente:

```text
CUDA Kernel Statistics
CUDA Memory Operation Statistics
```

A expectativa e que `gpu_resident` concentre as copias no inicio/fim e reduza
operacoes de memoria host-dispositivo em relacao a `gpu_baseline`.

### 5. O que anexar/registrar na entrega

- CSV bruto `heat_resultados_<job_id>.csv`;
- `comparacao_heat.md`;
- `comparacao_heat_resumo.csv`;
- resumo textual do `nsys`;
- perfis `.nsys-rep`/`.sqlite`, se forem aceitos na entrega;
- discussao destacando se a residencia de dados reduziu o custo de copia e melhorou
  `solve_time_s`.
