#!/bin/bash
#SBATCH --partition=gpu-8-v100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=00:05:00
#SBATCH --job-name=vadd-gpu
#SBATCH --output=vadd-gpu-%j.out
#SBATCH --error=vadd-gpu-%j.err

set -euo pipefail

cd "$(dirname "$0")"

module load compilers/nvidia/nvhpc/24.11

if [[ ! -f vadd-gpu.c ]]; then
    echo "Erro: vadd-gpu.c nao encontrado em $(pwd)." >&2
    exit 1
fi

echo "Compilando vadd-gpu.c..."
nvc -fast -mp=gpu vadd-gpu.c -o vadd-gpu

echo "Executando vadd-gpu..."
export OMP_TARGET_OFFLOAD=MANDATORY
./vadd-gpu
