#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define N 10000000

static int A[N];

int main() {
    // laco 1: inicializacao do vetor
    for (int i = 0; i < N; i++)
        A[i] = i + 2;

    // laco 3: quebra de dependencia com multiplas variaveis acumuladoras
    long long soma1 = 0, soma2 = 0;

    double start = omp_get_wtime();

    for (int i = 0; i < N; i += 2) {
        soma1 += A[i];
        soma2 += A[i + 1];
    }

    double end = omp_get_wtime();

    printf("%.6f\n", end - start);
    printf("Soma: %lld\n", soma1 + soma2);

    return 0;
}
