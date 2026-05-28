#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <omp.h>

#define N       50000   /* iteracoes externas */
#define INNER   10000   /* iteracoes internas de calculo intensivo */

int main(int argc, char *argv[]) {
    int num_threads = 1;
    if (argc > 1) {
        num_threads = atoi(argv[1]);
        omp_set_num_threads(num_threads);
    }

    double *resultado = (double*)malloc(N * sizeof(double));
    if (!resultado) {
        fprintf(stderr, "Erro: falha na alocacao de memoria\n");
        return 1;
    }

    double start = omp_get_wtime();

    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        double temp = (double)i;
        for (int j = 0; j < INNER; j++) {
            temp = sin(temp) + cos(temp);
        }
        resultado[i] = temp;
    }

    double elapsed = omp_get_wtime() - start;

    double gflops = ((double)N * INNER * 2.0) / elapsed / 1e9;

    int actual_threads = omp_get_max_threads();
    printf("RESULT threads=%d time=%.6f gflops=%.3f\n",
           actual_threads, elapsed, gflops);

    free(resultado);
    return 0;
}
