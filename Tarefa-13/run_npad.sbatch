#!/bin/bash
#SBATCH --job-name=tarefa13-affinity
#SBATCH --output=resultados/slurm-%j.out
#SBATCH --error=resultados/slurm-%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --time=01:30:00

set -euo pipefail

if [ -f "$SLURM_SUBMIT_DIR/coletar_afinidade.py" ]; then
  cd "$SLURM_SUBMIT_DIR"
elif [ -f "$SLURM_SUBMIT_DIR/Tarefa-13/coletar_afinidade.py" ]; then
  cd "$SLURM_SUBMIT_DIR/Tarefa-13"
else
  echo "Erro: submeta este job da raiz do repositorio ou de Tarefa-13." >&2
  exit 1
fi

mkdir -p resultados

# Descomente e ajuste se o NPAD exigir carregamento explicito de compilador.
# module purge
# module load gcc

python3 coletar_afinidade.py \
  --max-threads "${SLURM_CPUS_PER_TASK}" \
  --repeats 3 \
  --steps 1000 \
  --n 2048 \
  --mode omp-region \
  --schedule static \
  --collapse 1 \
  --affinities all

python3 gerar_relatorio.py
