#!/bin/bash
#SBATCH --partition=gpu-4-a100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --job-name=t20-heat-nsys
#SBATCH --output=nsys-%j.slurm.out
#SBATCH --error=nsys-%j.slurm.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/AULA-01-P-GPU/tarefa-20" ]]; then
    cd "${ROOT}/AULA-01-P-GPU/tarefa-20"
else
    cd "$(dirname "$0")"
fi

mkdir -p bin resultados/perfis

JOB_ID="${SLURM_JOB_ID:-local}"
exec > >(tee -a "resultados/nsys-${JOB_ID}.out")
exec 2> >(tee -a "resultados/nsys-${JOB_ID}.err" >&2)

module load compilers/nvidia/nvhpc/24.11

if ! command -v nsys >/dev/null 2>&1; then
    module load nsight-systems 2>/dev/null || true
fi

if ! command -v nsys >/dev/null 2>&1; then
    echo "Erro: comando nsys nao encontrado. Verifique os modulos disponiveis com: module avail nsight" >&2
    exit 1
fi

NVC="${NVC:-nvc}"
CPU_FLAGS="${CPU_FLAGS:--fast -mp=multicore}"
GPU_FLAGS="${GPU_FLAGS:--fast -mp=gpu}"
N="${N:-1000}"
NSTEPS="${NSTEPS:-10}"
PROFILE_VARIANT="${PROFILE_VARIANT:-gpu}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-1}}"
export OMP_TARGET_OFFLOAD="${OMP_TARGET_OFFLOAD:-MANDATORY}"

echo "Configuracao do perfil:"
echo "  PROFILE_VARIANT=${PROFILE_VARIANT}"
echo "  N=${N}"
echo "  NSTEPS=${NSTEPS}"
echo "  OMP_NUM_THREADS=${OMP_NUM_THREADS}"
echo "  OMP_TARGET_OFFLOAD=${OMP_TARGET_OFFLOAD}"
echo

echo "Compilador:"
"${NVC}" --version
echo

echo "Nsight Systems:"
nsys --version
echo

profile_gpu() {
    echo "Compilando GPU..."
    "${NVC}" ${GPU_FLAGS} heat_target.c -o bin/heat_gpu -lm

    local output="resultados/perfis/nsys_heat_gpu_n${N}_s${NSTEPS}_${JOB_ID}"
    echo "Gerando perfil GPU em ${output}.nsys-rep"

    nsys profile \
        --trace=cuda,nvtx,osrt \
        --stats=true \
        --force-overwrite=true \
        -o "${output}" \
        ./bin/heat_gpu "${N}" "${NSTEPS}"

    echo
    echo "Resumo GPU:"
    nsys stats "${output}.nsys-rep"
}

profile_cpu() {
    echo "Compilando CPU..."
    "${NVC}" ${CPU_FLAGS} heat.c -o bin/heat_cpu -lm

    local output="resultados/perfis/nsys_heat_cpu_n${N}_s${NSTEPS}_${JOB_ID}"
    echo "Gerando perfil CPU em ${output}.nsys-rep"

    nsys profile \
        --trace=osrt,nvtx \
        --stats=true \
        --force-overwrite=true \
        -o "${output}" \
        ./bin/heat_cpu "${N}" "${NSTEPS}"

    echo
    echo "Resumo CPU:"
    nsys stats "${output}.nsys-rep"
}

case "${PROFILE_VARIANT}" in
    gpu)
        profile_gpu
        ;;
    cpu)
        profile_cpu
        ;;
    both)
        profile_gpu
        profile_cpu
        ;;
    *)
        echo "Erro: PROFILE_VARIANT deve ser gpu, cpu ou both." >&2
        exit 2
        ;;
esac

echo
echo "Perfis gerados em Aula-P-GPU/tarefa-20/resultados/perfis/"
