#!/bin/bash
#SBATCH --partition=gpu-4-a100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:40:00
#SBATCH --job-name=t21-heat
#SBATCH --output=tarefa21-%j.slurm.out
#SBATCH --error=tarefa21-%j.slurm.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/Tarefa-21" ]]; then
    cd "${ROOT}/Tarefa-21"
else
    cd "$(dirname "$0")"
fi

mkdir -p bin resultados

JOB_ID="${SLURM_JOB_ID:-local}"
exec > >(tee -a "resultados/tarefa21-${JOB_ID}.out")
exec 2> >(tee -a "resultados/tarefa21-${JOB_ID}.err" >&2)

module load compilers/nvidia/nvhpc/24.11

NVC="${NVC:-nvc}"
CPU_FLAGS="${CPU_FLAGS:--fast -mp=multicore}"
GPU_FLAGS="${GPU_FLAGS:--fast -mp=gpu}"

echo "Compilador:"
"${NVC}" --version
echo

echo "Compilando CPU..."
"${NVC}" ${CPU_FLAGS} heat_cpu.c -o bin/heat_cpu -lm

echo "Compilando GPU baseline com map(tofrom) por passo..."
"${NVC}" ${GPU_FLAGS} heat_target_baseline.c -o bin/heat_gpu_baseline -lm

echo "Compilando GPU otimizada com dados residentes..."
"${NVC}" ${GPU_FLAGS} heat_target_resident.c -o bin/heat_gpu_resident -lm

CSV="resultados/heat_resultados_${JOB_ID}.csv"
CASES="${CASES:-1000:10 2000:20 4000:40}"
REPEATS="${REPEATS:-3}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-1}}"
export OMP_TARGET_OFFLOAD="${OMP_TARGET_OFFLOAD:-MANDATORY}"

printf "job_id,variant,executable,n,nsteps,repeat,status,error_l2,solve_time_s,total_time_s,omp_threads,omp_devices,offload_policy\n" > "${CSV}"

run_case() {
    local variant="$1"
    local executable="$2"
    local n="$3"
    local nsteps="$4"
    local repeat="$5"
    local raw="resultados/raw_${variant}_n${n}_steps${nsteps}_r${repeat}_${JOB_ID}.log"

    echo "Executando ${variant}: n=${n}, nsteps=${nsteps}, repeat=${repeat}"

    set +e
    output="$("${executable}" "${n}" "${nsteps}" 2>&1)"
    status="$?"
    set -e

    printf "%s\n" "${output}" > "${raw}"

    error_l2="$(printf "%s\n" "${output}" | awk -F: '/Error \(L2norm\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"
    solve_time="$(printf "%s\n" "${output}" | awk -F: '/Solve time \(s\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"
    total_time="$(printf "%s\n" "${output}" | awk -F: '/Total time \(s\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"

    printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
        "${JOB_ID}" \
        "${variant}" \
        "${executable}" \
        "${n}" \
        "${nsteps}" \
        "${repeat}" \
        "${status}" \
        "${error_l2}" \
        "${solve_time}" \
        "${total_time}" \
        "${OMP_NUM_THREADS}" \
        "${OMP_NUM_DEVICES:-unknown}" \
        "${OMP_TARGET_OFFLOAD}" >> "${CSV}"

    if [[ "${status}" -ne 0 ]]; then
        echo "Falha em ${variant} n=${n} nsteps=${nsteps}. Veja ${raw}." >&2
        return "${status}"
    fi
}

echo "Configuracao:"
echo "  CASES=${CASES}"
echo "  REPEATS=${REPEATS}"
echo "  OMP_NUM_THREADS=${OMP_NUM_THREADS}"
echo "  OMP_TARGET_OFFLOAD=${OMP_TARGET_OFFLOAD}"
echo "  CSV=${CSV}"
echo

for case_spec in ${CASES}; do
    IFS=: read -r n nsteps <<< "${case_spec}"
    for repeat in $(seq 1 "${REPEATS}"); do
        run_case "cpu" "./bin/heat_cpu" "${n}" "${nsteps}" "${repeat}"
        run_case "gpu_baseline" "./bin/heat_gpu_baseline" "${n}" "${nsteps}" "${repeat}"
        run_case "gpu_resident" "./bin/heat_gpu_resident" "${n}" "${nsteps}" "${repeat}"
    done
done

echo
echo "Resultados gravados em ${CSV}"
echo "Para gerar o relatorio:"
echo "  cd Tarefa-21"
echo "  python3 comparar_resultados.py"
