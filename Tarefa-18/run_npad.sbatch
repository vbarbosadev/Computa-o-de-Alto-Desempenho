#!/bin/bash
#SBATCH --job-name=tarefa18_mpi_type
#SBATCH --output=Tarefa-18/resultados/slurm-%j.out
#SBATCH --ntasks=4
#SBATCH --time=00:20:00

set -e

cd "$SLURM_SUBMIT_DIR"
mkdir -p Tarefa-18/resultados

python3 -m venv Tarefa-18/.venv
Tarefa-18/.venv/bin/python -m pip install --upgrade pip
Tarefa-18/.venv/bin/python -m pip install matplotlib

Tarefa-18/.venv/bin/python Tarefa-18/coletar_mpi.py
Tarefa-18/.venv/bin/python Tarefa-18/gerar_relatorio.py
