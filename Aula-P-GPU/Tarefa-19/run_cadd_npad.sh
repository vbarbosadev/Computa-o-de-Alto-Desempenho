#!/bin/bash
#SBATCH --partition=gpu-8-v100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --time=00:05:00
#SBATCH --job-name=cadd
#SBATCH --output=cadd-%j.out
#SBATCH --error=cadd-%j.err

set -euo pipefail

cd "$(dirname "$0")"

module load compilers/nvidia/nvhpc/24.11

if [[ ! -f cadd.c ]]; then
    echo "Erro: cadd.c nao encontrado em $(pwd)." >&2
    exit 1
fi

echo "Compilando cadd.c..."
nvc -fast -mp=gpu cadd.c -o cadd

echo "Executando cadd..."
export OMP_TARGET_OFFLOAD=MANDATORY
./cadd
