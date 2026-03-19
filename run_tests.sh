#!/bin/bash
# Script de compilacao e coleta de dados para as 3 tarefas
# Rodar em Linux: chmod +x run_tests.sh && ./run_tests.sh

set -e
mkdir -p dados

# ─── TAREFA 1 ──────────────────────────────────────────────────────────────
echo "=== Tarefa 1: MxV linha vs coluna ==="

gcc -O2 -fopenmp Tarefa-01/mult_por_linha.c   -o Tarefa-01/linha   -lm
gcc -O2 -fopenmp Tarefa-01/mult_por_coluna.c  -o Tarefa-01/coluna  -lm

echo "N,tempo_linha,tempo_coluna" > dados/tarefa1.csv

for N in 10 50 100 500 1000 2000 3000 5000 8000 10000; do
    t_linha=$(./Tarefa-01/linha  $N | cut -d',' -f2)
    t_col=$(./Tarefa-01/coluna $N | cut -d',' -f2)
    echo "$N,$t_linha,$t_col"
    echo "$N,$t_linha,$t_col" >> dados/tarefa1.csv
done

# ─── TAREFA 2 ──────────────────────────────────────────────────────────────
echo ""
echo "=== Tarefa 2: ILP — lacos 2 e 3 com -O0 / -O2 / -O3 ==="

echo "laco,otimizacao,tempo" > dados/tarefa2.csv

for OPT in O0 O2 O3; do
    gcc -${OPT} -fopenmp Tarefa-02/laco_soma_simples.c -o Tarefa-02/laco_soma_${OPT}      -lm
    gcc -${OPT} -fopenmp Tarefa-02/laco_unroll_2.c     -o Tarefa-02/laco_unroll_2_${OPT}  -lm
    gcc -${OPT} -fopenmp Tarefa-02/laco_unroll_4.c     -o Tarefa-02/laco_unroll_4_${OPT}  -lm
    gcc -${OPT} -fopenmp Tarefa-02/laco_unroll_8.c     -o Tarefa-02/laco_unroll_8_${OPT}  -lm
    gcc -${OPT} -fopenmp Tarefa-02/laco_unroll_12.c    -o Tarefa-02/laco_unroll_12_${OPT} -lm

    t_soma=$(./Tarefa-02/laco_soma_${OPT}      | head -1)
    t_u2=$(./Tarefa-02/laco_unroll_2_${OPT}    | head -1)
    t_u4=$(./Tarefa-02/laco_unroll_4_${OPT}    | head -1)
    t_u8=$(./Tarefa-02/laco_unroll_8_${OPT}    | head -1)
    t_u12=$(./Tarefa-02/laco_unroll_12_${OPT}  | head -1)

    for row in \
        "laco_soma,$OPT,$t_soma" \
        "laco_unroll_2,$OPT,$t_u2" \
        "laco_unroll_4,$OPT,$t_u4" \
        "laco_unroll_8,$OPT,$t_u8" \
        "laco_unroll_12,$OPT,$t_u12"; do
        echo "$row"
        echo "$row" >> dados/tarefa2.csv
    done
done

# ─── TAREFA 3 ──────────────────────────────────────────────────────────────
echo ""
echo "=== Tarefa 3: Aproximacao de pi ==="

gcc -O2 -fopenmp Tarefa-03/compare-pi.c -o Tarefa-03/compare-pi -lm

# linha com # e impressa no terminal mas nao entra no CSV
./Tarefa-03/compare-pi | tee /dev/stderr | grep -v '^#' > dados/tarefa3.csv

echo ""
echo "Dados salvos em dados/"
