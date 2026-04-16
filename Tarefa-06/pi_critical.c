/*
 * Tarefa 6 - Estimativa estocastica de PI com #pragma omp critical
 *
 * Corrige a condicao de corrida usando #pragma omp critical para proteger
 * o acesso a variavel compartilhada 'count'. A regiao critica garante que
 * apenas uma thread por vez executa count++.
 *
 * Usa rand_r() com seed privada por thread para evitar problema de thread-safety.
 *
 * Nota: critical serializa o acesso, reduzindo o paralelismo.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_critical pi_critical.c -lm
 * Executar: ./pi_critical [N]
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <omp.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(int argc, char *argv[]) {
    int N = 10000000;
    if (argc > 1) N = atoi(argv[1]);

    int count = 0;
    int threads_used;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = time(NULL) ^ omp_get_thread_num();
        double x, y;

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for
        for (int i = 0; i < N; i++) {
            x = (double)rand_r(&seed) / RAND_MAX;
            y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0) {
                #pragma omp critical
                {
                    count++;
                }
            }
        }
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=critical n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
