#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

#define N 100000000  

int main(int argc, char *argv[]) {
    int num_threads = 1;
    if (argc > 1) {
        num_threads = atoi(argv[1]);
        omp_set_num_threads(num_threads);
    }

    double *A = (double*)malloc(N * sizeof(double));
    double *B = (double*)malloc(N * sizeof(double));
    double *C = (double*)malloc(N * sizeof(double));

    if (!A || !B || !C) {
        fprintf(stderr, "Erro: falha na alocacao de memoria\n");
        return 1;
    }

    #pragma omp parallel for
    for (long i = 0; i < N; i++) {
        A[i] = 1.0;
        B[i] = 2.0;
    }

    double start = omp_get_wtime();

    #pragma omp parallel for
    for (long i = 0; i < N; i++) {
        C[i] = A[i] + B[i];
    }

    double elapsed = omp_get_wtime() - start;


    int actual_threads = omp_get_max_threads();
    printf("RESULT threads=%d time=%.6f\n",
           actual_threads, elapsed);

    free(A); free(B); free(C);
    return 0;
}
