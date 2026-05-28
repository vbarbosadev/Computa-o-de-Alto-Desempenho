#!/bin/bash
#SBATCH --job-name=tarefa12-navier
#SBATCH --output=resultados/slurm-%j.out
#SBATCH --error=resultados/slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:00:00

set -euo pipefail

cd "$SLURM_SUBMIT_DIR"
mkdir -p resultados

# Descomente e ajuste se o NPAD exigir carregamento explicito de compilador.
# module purge
# module load gcc

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

export OMP_PROC_BIND=close
export OMP_PLACES=cores

python coletar_npad.py \
  --max-threads "${SLURM_CPUS_PER_TASK}" \
  --repeats 3 \
  --steps 1000 \
  --strong-n 2048 \
  --weak-base-n 1024 \
  --schedule static \
  --collapse 1 \
  --modes omp-basic omp-region

python gerar_relatorio.py
