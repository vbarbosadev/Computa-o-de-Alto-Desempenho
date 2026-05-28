# Tarefa 17 - Como rodar

## Teste rapido

```bash
cd Tarefa-17
gcc -O3 -Wall -Wextra matvec_seq.c -o matvec_seq
mpicc -O3 -Wall -Wextra matvec_collective.c -o matvec_collective

./matvec_seq --m 1000 --n 1000
mpirun -np 4 ./matvec_collective --m 1000 --n 1000
```

## Coleta completa

```bash
cd Tarefa-17
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --sizes 1000x1000 2000x2000 4000x2000 \
  --processes 1 2 4

python gerar_relatorio.py
```

## Slurm

```bash
cd Tarefa-17
sbatch run_npad.sbatch
```

Resultados esperados:

```bash
Tarefa-17/resultados/tarefa17_resultados.csv
Tarefa-17/resultados/speedup.png
Tarefa-17/resultados/eficiencia.png
Tarefa-17/resultados/relatorio_tarefa17.md
```
