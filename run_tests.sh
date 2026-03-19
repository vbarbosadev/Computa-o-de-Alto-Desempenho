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

for N in 100 500 1000 2000 3000 4000 5000; do
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
    gcc -${OPT} -fopenmp Tarefa-02/laco_1e2.c -o Tarefa-02/laco2_${OPT} -lm
    gcc -${OPT} -fopenmp Tarefa-02/laco_1e3.c -o Tarefa-02/laco3_${OPT} -lm

    t2=$(./Tarefa-02/laco2_${OPT} | head -1)
    t3=$(./Tarefa-02/laco3_${OPT} | head -1)

    echo "laco2,$OPT,$t2"
    echo "laco3,$OPT,$t3"
    echo "laco2,$OPT,$t2" >> dados/tarefa2.csv
    echo "laco3,$OPT,$t3" >> dados/tarefa2.csv
done

# ─── TAREFA 3 ──────────────────────────────────────────────────────────────
echo ""
echo "=== Tarefa 3: Aproximacao de pi ==="

gcc -O2 -fopenmp Tarefa-03/compare-pi.c -o Tarefa-03/compare-pi -lm

./Tarefa-03/compare-pi | tee dados/tarefa3.csv

echo ""
echo "Dados salvos em dados/"
