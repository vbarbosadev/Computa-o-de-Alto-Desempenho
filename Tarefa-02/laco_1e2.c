#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define N 10000000

static int A[N];

int main() {
    // laco 1: inicializacao do vetor
    for (int i = 0; i < N; i++)
        A[i] = i + 2;

    // laco 2: soma acumulativa com dependencia entre iteracoes
    long long soma = 0;

    double start = omp_get_wtime();

    for (int i = 0; i < N; i++)
        soma += A[i];

    double end = omp_get_wtime();

    printf("%.6f\n", end - start);
    printf("Soma: %lld\n", soma);

    return 0;
}
