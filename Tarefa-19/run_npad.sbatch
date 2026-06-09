#!/bin/bash
#SBATCH --partition=gpu-8-v100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:10:00
#SBATCH --job-name=tarefa19-vadd
#SBATCH --output=Tarefa-19/resultados/tarefa19-%j.out
#SBATCH --error=Tarefa-19/resultados/tarefa19-%j.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/Tarefa-19" ]]; then
    cd "${ROOT}/Tarefa-19"
else
    cd "$(dirname "$0")"
fi

mkdir -p resultados

module load compilers/nvidia/nvhpc/24.11

make clean
make

N="${N:-100000000}"
REPEATS="${REPEATS:-5}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-8}}"
export OMP_TARGET_OFFLOAD=MANDATORY

JOB_ID="${SLURM_JOB_ID:-local}"
CSV="resultados/tarefa19_resultados_${JOB_ID}.csv"

printf "variant,device,n,repeats,best_compute_s,avg_compute_s,init_s,verify_s,errors,omp_threads,omp_devices\n" > "${CSV}"

echo "Running CPU version with N=${N}, REPEATS=${REPEATS}, OMP_NUM_THREADS=${OMP_NUM_THREADS}"
./vadd_cpu "${N}" "${REPEATS}" | tee -a "${CSV}"

echo "Running GPU version with N=${N}, REPEATS=${REPEATS}, OMP_TARGET_OFFLOAD=${OMP_TARGET_OFFLOAD}"
./vadd_gpu "${N}" "${REPEATS}" | tee -a "${CSV}"

echo "Results written to ${CSV}"
