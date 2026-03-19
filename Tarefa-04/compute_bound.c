#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <omp.h>

#define N 50000

int main() {
    double *resultado = (double*)malloc(N * sizeof(double));

    double start_time = omp_get_wtime();

    #pragma omp parallel for
    for(int i = 0; i < N; i++) {
        double temp = (double)i;
        for (int j = 0; j < 10000; j++) {
            temp = sin(temp) + cos(temp);
        }
        resultado[i] = temp;
    }

    double end_time = omp_get_wtime();

    printf("Compute-bound: Tempo de execucao do laco = %f segundos\n", end_time - start_time);

    free(resultado);
    return 0;
}