/*
 * Tarefa 6 - Estimativa estocastica de PI com #pragma omp parallel for
 *
 * PROBLEMA: Esta versao apresenta CONDICAO DE CORRIDA.
 *
 * A variavel 'count' e compartilhada entre todas as threads. Quando multiplas
 * threads executam 'count++' simultaneamente, ocorre uma condicao de corrida
 * (race condition): duas ou mais threads podem ler o mesmo valor de count,
 * incrementar e escrever de volta, perdendo incrementos.
 *
 * Alem disso, rand() nao e thread-safe: seu estado interno e global e
 * compartilhado, causando resultados imprevisiveis.
 *
 * Resultado: o valor de PI sera INCORRETO e variara entre execucoes,
 * geralmente ficando abaixo do esperado.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_parallel_for pi_parallel_for.c -lm
 * Executar: ./pi_parallel_for [N]
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
    double x, y;
    int threads_used;

    double t0 = omp_get_wtime();

    /* CONDICAO DE CORRIDA: count compartilhado sem protecao, rand() nao thread-safe */
    #pragma omp parallel for
    for (int i = 0; i < N; i++) {
        x = (double)rand() / RAND_MAX;
        y = (double)rand() / RAND_MAX;
        if (x * x + y * y <= 1.0)
            count++;  /* RACE CONDITION */
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    #pragma omp parallel
    {
        #pragma omp single
        threads_used = omp_get_num_threads();
    }

    printf("CONFIG program=parallel_for n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
