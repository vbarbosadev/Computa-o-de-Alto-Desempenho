# Tarefa 19 - vadd com OpenMP em GPU

Entrega baseada nos exercicios `vadd.c` dos slides do tutorial
`conteudos/omp_GPGPU_prog_SC23.pdf`:

- versao CPU: `#pragma omp parallel for`;
- versao GPU: `#pragma omp target` seguido de `#pragma omp loop`.

## Arquivos

- `vadd_cpu.c`: adicao de vetores na CPU com OpenMP.
- `vadd_gpu.c`: adicao de vetores com offload OpenMP para GPU.
- `Makefile`: compila as duas versoes com NVHPC.
- `run_npad.sbatch`: executa no NPAD e grava CSV em `resultados/`.
- `relatorio_tarefa19.md`: relatorio da tarefa e espaco para registrar os tempos obtidos.

## Execucao no NPAD

Envie a pasta do repositorio para o NPAD e rode a partir da raiz:

```bash
sbatch Tarefa-19/run_npad.sbatch
```

Parametros opcionais:

```bash
N=50000000 REPEATS=7 sbatch Tarefa-19/run_npad.sbatch
```

O script usa a particao `gpu-8-v100`, carrega
`compilers/nvidia/nvhpc/24.11`, compila com `nvc` e define
`OMP_TARGET_OFFLOAD=MANDATORY` para evitar fallback silencioso para CPU.

O CSV gerado tem este formato:

```text
variant,device,n,repeats,best_compute_s,avg_compute_s,init_s,verify_s,errors,omp_threads,omp_devices
```
