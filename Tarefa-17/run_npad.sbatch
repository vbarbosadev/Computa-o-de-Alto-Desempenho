#!/bin/bash
#SBATCH --job-name=tarefa17-mpi
#SBATCH --output=resultados/slurm-%j.out
#SBATCH --error=resultados/slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00

set -euo pipefail

cd "$SLURM_SUBMIT_DIR"
mkdir -p resultados

# Descomente e ajuste se o ambiente exigir carregamento explicito de MPI.
# module purge
# module load openmpi
# module load gcc

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --sizes 1000x1000 2000x2000 4000x2000 \
  --processes 1 2 4

python gerar_relatorio.py
