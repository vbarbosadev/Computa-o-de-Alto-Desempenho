#!/bin/bash
# Script dedicado para compilar e coletar dados da Tarefa 3 (Leibniz)
# Uso: chmod +x run_tarefa3.sh && ./run_tarefa3.sh

set -e
mkdir -p dados

echo "=== Tarefa 3: Aproximacao de pi — Serie de Leibniz ==="

gcc -O2 -fopenmp Tarefa-03/leibniz_seq.c -o Tarefa-03/leibniz_seq -lm
gcc -O2 -fopenmp Tarefa-03/leibniz_omp.c -o Tarefa-03/leibniz_omp -lm

echo ""
echo "-- Sequencial (10 ate 5 bilhoes de termos) --"
./Tarefa-03/leibniz_seq | tee /dev/stderr | grep -v '^#' > dados/tarefa3_seq.csv
echo "-> dados/tarefa3_seq.csv salvo"

echo ""
echo "-- Paralelo (100M, 1B, 5B termos x 1/2/4/8 threads) --"
./Tarefa-03/leibniz_omp | tee /dev/stderr | grep -v '^#' > dados/tarefa3_omp.csv
echo "-> dados/tarefa3_omp.csv salvo"

echo ""
echo "Coleta concluida."
