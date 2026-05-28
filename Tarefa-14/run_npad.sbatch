#!/bin/bash
#SBATCH --job-name=tarefa14-mpi
#SBATCH --output=resultados/slurm-%j.out
#SBATCH --error=resultados/slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00

set -euo pipefail

cd "$SLURM_SUBMIT_DIR"
mkdir -p resultados

# Descomente e ajuste se o NPAD exigir carregamento explicito de MPI.
# module purge
# module load openmpi
# module load gcc

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --sizes 8 16 32 64 128 256 512 1024 4096 16384 65536 262144 1048576

python gerar_relatorio.py
