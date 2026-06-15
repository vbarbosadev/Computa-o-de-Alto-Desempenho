# Tarefa 20 - heat CPU x GPU no NPAD

Esta pasta compara:

- `heat.c`: versao CPU original;
- `heat_target.c`: versao com OpenMP target para GPU.

O script `run_npad.sbatch` compila as duas versoes com NVHPC, executa os
mesmos tamanhos de entrada e grava um CSV em `resultados/`.

O script `run_nsys_npad.sbatch` roda o Nsight Systems (`nsys`) para gerar o
perfil de execucao da versao GPU, CPU ou das duas.

## 1. Enviar os arquivos para o NPAD

Se o repositorio ainda nao estiver no NPAD, envie a pasta do projeto:

```bash
scp -r atividades-aula usuario@servidor-do-npad:~/
```

Substitua `usuario` e `servidor-do-npad` pelos dados do seu acesso.

Depois acesse o NPAD:

```bash
ssh usuario@servidor-do-npad
cd ~/atividades-aula
```

## 2. Submeter a execucao padrao

Rode a partir da raiz do repositorio:

```bash
sbatch Aula-P-GPU/tarefa-20/run_npad.sbatch
```

A particao padrao configurada e `gpu-4-a100`. Se ela estiver ocupada e outra
particao GPU estiver livre, sobrescreva na submissao:

```bash
sbatch --partition=gpu-8-v100 Aula-P-GPU/tarefa-20/run_npad.sbatch
```

A configuracao padrao executa:

```text
CASES="1000:10 2000:20 4000:40"
REPEATS=3
```

Cada caso usa o formato `N:nsteps`. Por exemplo, `1000:10` roda uma malha
`1000 x 1000` por `10` passos de tempo.

## 3. Alterar tamanhos ou repeticoes

Para testar outros tamanhos:

```bash
CASES="500:10 1000:10 2000:20" REPEATS=5 sbatch Aula-P-GPU/tarefa-20/run_npad.sbatch
```

Para aumentar o tempo limite, edite a linha `#SBATCH --time=00:30:00` no
arquivo `run_npad.sbatch`.

## 4. Acompanhar o job

```bash
squeue -u "$USER"
```

Se o job nao aparecer no `squeue`, ele pode ja ter terminado ou falhado logo no
inicio. Confira o historico recente:

```bash
sacct -u "$USER" --starttime today --format=JobID,JobName%20,Partition,State,ExitCode,Elapsed,Reason
```

Para consultar um job especifico:

```bash
sacct -j <job_id> --format=JobID,JobName%20,Partition,State,ExitCode,Elapsed,Reason
```

As saidas do SLURM ficam em:

```text
Aula-P-GPU/tarefa-20/resultados/tarefa20-<job_id>.out
Aula-P-GPU/tarefa-20/resultados/tarefa20-<job_id>.err
```

Se o job falhar antes de entrar no script, o SLURM pode deixar arquivos na pasta
de onde voce chamou `sbatch`:

```text
tarefa20-<job_id>.slurm.out
tarefa20-<job_id>.slurm.err
```

Nesse caso, leia o `.slurm.err` primeiro.

O CSV principal fica em:

```text
Aula-P-GPU/tarefa-20/resultados/heat_resultados_<job_id>.csv
```

Tambem sao salvos logs brutos por variante, tamanho e repeticao:

```text
Aula-P-GPU/tarefa-20/resultados/raw_cpu_*.log
Aula-P-GPU/tarefa-20/resultados/raw_gpu_*.log
```

## 5. Gerar a comparacao

Depois que o job terminar:

```bash
cd Aula-P-GPU/tarefa-20
python3 comparar_resultados.py
```

O comparador le todos os arquivos `resultados/heat_resultados_*.csv` e gera:

```text
resultados/comparacao_heat_resumo.csv
resultados/comparacao_heat.md
resultados/tempo_solve_cpu_gpu.png
resultados/speedup_solve_cpu_gpu.png
```

Se o Python do NPAD nao tiver `matplotlib`, o relatorio Markdown e o CSV ainda
serao gerados, mas os graficos PNG serao ignorados.

## 6. Interpretar os dados

No relatorio, `speedup_solve` e calculado como:

```text
tempo medio CPU / tempo medio GPU
```

- valor maior que `1`: GPU foi mais rapida;
- valor menor que `1`: CPU foi mais rapida;
- `Delta L2`: diferenca entre os erros numericos medios das duas versoes.

Como `heat_target.c` usa `map(tofrom: ...)` dentro de `solve()`, a transferencia
CPU-GPU-CPU acontece em cada passo de tempo. Portanto o tempo da GPU inclui o
custo de offload e copia de dados, nao apenas o calculo aritmetico do stencil.

## 7. Gerar perfil com nsys

Para gerar um perfil da versao GPU com Nsight Systems:

```bash
sbatch Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Por padrao, o perfil usa:

```text
PROFILE_VARIANT=gpu
N=1000
NSTEPS=10
```

Para mudar o tamanho do caso:

```bash
N=2000 NSTEPS=20 sbatch Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Para perfilar CPU, GPU ou as duas:

```bash
PROFILE_VARIANT=cpu sbatch Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
PROFILE_VARIANT=gpu sbatch Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
PROFILE_VARIANT=both sbatch Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Tambem e possivel trocar a particao na submissao:

```bash
sbatch --partition=gpu-4-a100 Aula-P-GPU/tarefa-20/run_nsys_npad.sbatch
```

Os arquivos do perfil ficam em:

```text
Aula-P-GPU/tarefa-20/resultados/perfis/nsys_heat_gpu_*.nsys-rep
Aula-P-GPU/tarefa-20/resultados/perfis/nsys_heat_gpu_*.sqlite
```

O proprio job tambem executa `nsys stats` e grava o resumo em:

```text
Aula-P-GPU/tarefa-20/resultados/nsys-<job_id>.out
```

Para ver se o offload esta acontecendo, procure no resumo por secoes como:

```text
CUDA Kernel Statistics
CUDA Memory Operation Statistics
```

Se o tempo de memoria aparecer alto, isso e esperado nesta primeira versao GPU,
porque o `map(tofrom: u[0:n*n], u_tmp[0:n*n])` esta dentro da funcao `solve()`
e pode transferir dados a cada passo.

Para abrir o perfil no seu computador, copie o `.nsys-rep` do NPAD:

```bash
scp usuario@servidor-do-npad:~/atividades-aula/Aula-P-GPU/tarefa-20/resultados/perfis/nsys_heat_gpu_*.nsys-rep .
```

Depois abra esse arquivo no NVIDIA Nsight Systems local.
