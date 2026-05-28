# Tarefa 15 - Como rodar

## Teste rapido

```bash
cd Tarefa-15
mpicc -O3 -Wall -Wextra heat_send_recv.c -lm -o heat_send_recv
mpirun -np 2 ./heat_send_recv --n 100000 --passos 1000
```

Se o comando imprimir linhas `RESULT versao=send_recv ...`, o ambiente MPI esta
funcionando.

## Coleta completa

```bash
cd Tarefa-15
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --steps 2000 \
  --processes 2 4 \
  --sizes 100000 1000000

python gerar_relatorio.py
```

## Slurm

```bash
cd Tarefa-15
sbatch run_npad.sbatch
```

Resultados esperados:

```bash
Tarefa-15/resultados/tarefa15_resultados.csv
Tarefa-15/resultados/tempo_n100000.png
Tarefa-15/resultados/tempo_n1000000.png
Tarefa-15/resultados/speedup_relativo.png
Tarefa-15/resultados/relatorio_tarefa15.md
```
