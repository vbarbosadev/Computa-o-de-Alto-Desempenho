# Tarefa 12 - Como rodar no NPAD

## 1. Enviar a pasta para o NPAD

Na sua maquina local, a partir da raiz do repositorio:

```bash
scp -r Tarefa-12 usuario@servidor-do-npad:~/atividades-aula/
```

Substitua `usuario` e `servidor-do-npad` pelos dados do seu acesso.

## 2. Entrar no NPAD

```bash
ssh usuario@servidor-do-npad
cd ~/atividades-aula/Tarefa-12
```

## 3. Criar ambiente Python seguro

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib
```

O `venv` isola apenas as dependencias Python. O compilador C/OpenMP deve existir no
sistema ou ser carregado por modulo.

Se o NPAD usar modules:

```bash
module avail gcc
module load gcc
```

## 4. Teste rapido em ambiente interativo

```bash
gcc -O3 -march=native -fopenmp navier_scaling.c -lm -o navier_scaling
OMP_NUM_THREADS=4 OMP_PROC_BIND=close OMP_PLACES=cores \
  ./navier_scaling --mode omp-region --nx 1024 --ny 1024 --steps 200 \
  --schedule static --collapse 1
```

Se esse comando imprimir `RESULT elapsed=...`, o codigo esta pronto para a coleta.

## 5. Rodar coleta completa sem Slurm

Use apenas se estiver em um no de computacao liberado para execucao interativa:

```bash
source .venv/bin/activate
python coletar_npad.py \
  --max-threads 32 \
  --repeats 3 \
  --steps 1000 \
  --strong-n 2048 \
  --weak-base-n 1024 \
  --schedule static \
  --collapse 1 \
  --modes omp-basic omp-region

python gerar_relatorio.py
```

## 6. Rodar com Slurm

Edite `run_npad.sbatch` se precisar trocar particao, tempo ou numero de CPUs.
Depois submeta:

```bash
sbatch run_npad.sbatch
```

Consultar fila:

```bash
squeue -u $USER
```

Quando terminar, os arquivos ficarao em:

```bash
Tarefa-12/resultados/tarefa12_resultados.csv
Tarefa-12/resultados/strong_scaling.png
Tarefa-12/resultados/weak_scaling.png
Tarefa-12/resultados/relatorio_tarefa12.md
Tarefa-12/resultados/slurm-*.out
Tarefa-12/resultados/slurm-*.err
```

## 7. Baixar resultados para a maquina local

Na maquina local:

```bash
scp -r usuario@servidor-do-npad:~/atividades-aula/Tarefa-12/resultados ./Tarefa-12/
```

## 8. O que analisar no relatorio

- Escalabilidade forte: se o speedup cresce ao aumentar threads para a mesma malha.
- Escalabilidade fraca: se o tempo se mantem estavel ao aumentar a malha junto com as threads.
- Gargalos: queda de eficiencia por banda de memoria, barreiras entre passos e overhead de OpenMP.
- Evolucao do codigo: comparar `omp-basic` contra `omp-region`.
