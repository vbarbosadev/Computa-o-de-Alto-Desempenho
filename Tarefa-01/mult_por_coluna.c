#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

int main(int argc, char *argv[]) {
    int N = (argc > 1) ? atoi(argv[1]) : 1000;

    double *A = malloc((size_t)N * N * sizeof(double));
    double *B = malloc(N * sizeof(double));
    double *C = malloc(N * sizeof(double));

    if (!A || !B || !C) {
        fprintf(stderr, "Erro de alocacao de memoria\n");
        return 1;
    }

    srand(42);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++)
            A[i * N + j] = (double)rand() / RAND_MAX;
        B[i] = (double)rand() / RAND_MAX;
        C[i] = 0.0;
    }

    double start = omp_get_wtime();

    // coluna externa, linha interna — acesso column-major (cache-unfriendly)
    for (int j = 0; j < N; j++)
        for (int i = 0; i < N; i++)
            C[i] += A[i * N + j] * B[j];

    double end = omp_get_wtime();

    // output CSV: N,segundos
    printf("%d,%.6f\n", N, end - start);

    if (C[0] < -1e300) printf("dummy\n");

    free(A); free(B); free(C);
    return 0;
}
