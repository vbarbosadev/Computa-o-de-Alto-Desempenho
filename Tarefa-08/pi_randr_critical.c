/*
 * Tarefa 8 - Versao 3: rand_r() + variavel privada + #pragma omp critical
 *
 * Cada thread possui sua propria seed (privada), eliminando a disputa
 * pelo estado global de rand(). O gerador rand_r() e reentrante e nao
 * usa nenhum lock interno.
 *
 * Os acertos sao contados em uma variavel local por thread e acumulados
 * na variavel global 'count' com #pragma omp critical ao final do laco.
 *
 * Comparado com a versao rand_critical, o ganho esperado vem da remocao
 * do gargalo interno de rand(): as threads agora geram numeros de forma
 * verdadeiramente paralela.
 *
 * Compilar: gcc -O2 -fopenmp -o pi_randr_critical pi_randr_critical.c -lm
 * Executar: ./pi_randr_critical [N]
 */

#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(int argc, char *argv[]) {
    long N = 10000000L;
    if (argc > 1) N = atol(argv[1]);

    long count       = 0;
    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        /* seed unica por thread — sem compartilhamento do estado do RNG */
        unsigned int seed = (unsigned int)(time(NULL)) ^ (unsigned int)(omp_get_thread_num() * 2654435761u);
        long local_count  = 0;

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            double x = (double)rand_r(&seed) / RAND_MAX;
            double y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
        }

        #pragma omp critical
        count += local_count;
    }

    double elapsed = omp_get_wtime() - t0;
    double pi      = 4.0 * (double)count / (double)N;
    double error   = fabs(pi - M_PI);

    printf("CONFIG program=randr_critical n=%ld threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%ld total=%ld error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
