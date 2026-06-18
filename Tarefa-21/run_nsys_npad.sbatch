#!/bin/bash
#SBATCH --partition=gpu-4-a100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --job-name=t21-heat-nsys
#SBATCH --output=nsys-tarefa21-%j.slurm.out
#SBATCH --error=nsys-tarefa21-%j.slurm.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/Tarefa-21" ]]; then
    cd "${ROOT}/Tarefa-21"
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
GPU_FLAGS="${GPU_FLAGS:--fast -mp=gpu}"
N="${N:-2000}"
NSTEPS="${NSTEPS:-20}"
PROFILE_VARIANT="${PROFILE_VARIANT:-resident}"
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

profile_variant() {
    local variant="$1"
    local source="$2"
    local executable="bin/heat_${variant}"
    local output="resultados/perfis/nsys_heat_${variant}_n${N}_s${NSTEPS}_${JOB_ID}"

    echo "Compilando ${variant}..."
    "${NVC}" ${GPU_FLAGS} "${source}" -o "${executable}" -lm

    echo "Gerando perfil ${variant} em ${output}.nsys-rep"
    nsys profile \
        --trace=cuda,nvtx,osrt \
        --stats=true \
        --force-overwrite=true \
        -o "${output}" \
        "./${executable}" "${N}" "${NSTEPS}"

    echo
    echo "Resumo ${variant}:"
    nsys stats "${output}.nsys-rep"
}

case "${PROFILE_VARIANT}" in
    resident|optimized|otimizada)
        profile_variant "resident" "heat_target_resident.c"
        ;;
    baseline)
        profile_variant "baseline" "heat_target_baseline.c"
        ;;
    both)
        profile_variant "baseline" "heat_target_baseline.c"
        profile_variant "resident" "heat_target_resident.c"
        ;;
    *)
        echo "Erro: PROFILE_VARIANT deve ser resident, baseline ou both." >&2
        exit 2
        ;;
esac

echo
echo "Perfis gerados em Tarefa-21/resultados/perfis/"
