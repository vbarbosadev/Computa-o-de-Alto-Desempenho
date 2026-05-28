# Tarefa 16 - Como rodar

## Teste rapido

```bash
cd Tarefa-16
gcc -O3 -Wall -Wextra primos_seq.c -lm -o primos_seq
mpicc -O3 -Wall -Wextra leader_worker_primes.c -lm -o leader_worker_primes

./primos_seq --max 300000
mpirun -np 4 ./leader_worker_primes --max 300000 --tarefas 32
```

## Coleta completa

```bash
cd Tarefa-16
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --maximums 300000 1000000 \
  --tasks 8 32 128 \
  --processes 2 4

python gerar_relatorio.py
```

## Slurm

```bash
cd Tarefa-16
sbatch run_npad.sbatch
```

Resultados esperados:

```bash
Tarefa-16/resultados/tarefa16_resultados.csv
Tarefa-16/resultados/speedup_max300000.png
Tarefa-16/resultados/speedup_max1000000.png
Tarefa-16/resultados/eficiencia.png
Tarefa-16/resultados/relatorio_tarefa16.md
```
