# Tarefa 21 - heat com dados residentes na GPU

Esta pasta prepara a Tarefa 21 para execucao no NPAD, sem incluir resultados
fabricados.

## Arquivos

- `heat_cpu.c`: versao CPU sequencial usada como referencia.
- `heat_target_baseline.c`: versao GPU base da Tarefa 20, com
  `map(tofrom: u[0:n*n], u_tmp[0:n*n])` dentro de `solve()`.
- `heat_target_resident.c`: versao GPU otimizada para a Tarefa 21. Ela usa
`target enter data` antes do laco temporal e `target exit data` depois,
seguindo a estrutura da solucao `heat_target_map_opt.c` do tutorial
`UoB-HPC/openmp-tutorial`, mantendo `u` e `u_tmp` residentes no dispositivo
durante os passos.
- `run_npad.sbatch`: compila com NVHPC e roda CPU, GPU baseline e GPU
  otimizada, gravando CSV em `resultados/`.
- `run_nsys_npad.sbatch`: gera perfil Nsight Systems da versao otimizada e,
  opcionalmente, da baseline.
- `comparar_resultados.py`: le CSVs reais de `resultados/` e gera
  `comparacao_heat_resumo.csv` e `comparacao_heat.md`.

## Ideia da otimizacao

O exercicio pede reduzir movimentacao CPU-GPU. A baseline chama `solve()` a cada
passo, e dentro de `solve()` ha um `target map(tofrom: ...)`, o que pode copiar
os dois arrays em cada iteracao temporal.

Na versao `heat_target_resident.c`, a sequencia e:

```c
#pragma omp target enter data map(to: u[0:n*n], u_tmp[0:n*n])
for (int t = 0; t < nsteps; ++t) {
  solve(...);
  troca_de_ponteiros_no_host;
}
#pragma omp target exit data map(from: u[0:n*n])
```

Assim, `u` e `u_tmp` entram uma vez no ambiente de dados do dispositivo, e apenas
o array que contem a solucao final volta para o host. A troca de ponteiros continua
funcionando porque os valores dos ponteiros sao copiados para cada regiao `target`,
enquanto as associacoes de memoria ja existem no ambiente de dados do dispositivo.

## Submeter no NPAD

Execute a partir da raiz do repositorio:

```bash
sbatch Tarefa-21/run_npad.sbatch
```

A particao padrao no script e `gpu-4-a100`. Para sobrescrever na submissao:

```bash
sbatch --partition=gpu-8-v100 Tarefa-21/run_npad.sbatch
```

Configuracao padrao:

```text
CASES="1000:10 2000:20 4000:40"
REPEATS=3
OMP_TARGET_OFFLOAD=MANDATORY
```

Cada caso usa o formato `N:nsteps`. Para alterar casos ou repeticoes:

```bash
CASES="1000:10 2000:50 4000:100" REPEATS=5 sbatch Tarefa-21/run_npad.sbatch
```

## Saidas geradas

O job cria arquivos em `Tarefa-21/resultados/`:

```text
heat_resultados_<job_id>.csv
tarefa21-<job_id>.out
tarefa21-<job_id>.err
raw_cpu_*.log
raw_gpu_baseline_*.log
raw_gpu_resident_*.log
```

O CSV contem uma linha por variante, tamanho e repeticao. As variantes sao:

```text
cpu
gpu_baseline
gpu_resident
```

## Gerar relatorio

Depois que houver pelo menos um CSV real:

```bash
cd Tarefa-21
python3 comparar_resultados.py
```

Saidas:

```text
resultados/comparacao_heat_resumo.csv
resultados/comparacao_heat.md
```

Tambem e possivel passar CSVs especificos:

```bash
python3 comparar_resultados.py resultados/heat_resultados_<job_id>.csv
```

## Perfil com Nsight Systems

Por padrao, o perfil roda a versao otimizada:

```bash
sbatch Tarefa-21/run_nsys_npad.sbatch
```

Configuracao padrao:

```text
PROFILE_VARIANT=resident
N=2000
NSTEPS=20
```

Para perfilar baseline e otimizada no mesmo job:

```bash
PROFILE_VARIANT=both N=2000 NSTEPS=20 sbatch Tarefa-21/run_nsys_npad.sbatch
```

Perfis gerados:

```text
Tarefa-21/resultados/perfis/nsys_heat_baseline_*.nsys-rep
Tarefa-21/resultados/perfis/nsys_heat_resident_*.nsys-rep
```

No resumo do `nsys`, a expectativa e que a baseline mostre mais atividade de
copia associada aos passos temporais, enquanto a versao residente concentre as
transferencias no inicio e no fim da execucao.

## Validacao local

Localmente, use `gcc` apenas para checar sintaxe e fallback host. Isso nao valida
offload real para GPU:

```bash
mkdir -p Tarefa-21/bin
gcc -O2 -fopenmp Tarefa-21/heat_cpu.c -o Tarefa-21/bin/heat_cpu_gcc -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_baseline.c -o Tarefa-21/bin/heat_gpu_baseline_gcc -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_resident.c -o Tarefa-21/bin/heat_gpu_resident_gcc -lm
Tarefa-21/bin/heat_cpu_gcc 100 10
OMP_TARGET_OFFLOAD=DISABLED Tarefa-21/bin/heat_gpu_baseline_gcc 100 10
OMP_TARGET_OFFLOAD=DISABLED Tarefa-21/bin/heat_gpu_resident_gcc 100 10
```
