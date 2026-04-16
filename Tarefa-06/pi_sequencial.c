/*
 * Tarefa 6 - Estimativa estocastica de PI (versao sequencial)
 *
 * Metodo de Monte Carlo: sorteia pontos aleatorios no quadrado [0,1]x[0,1]
 * e verifica quantos caem dentro do circulo unitario (x^2 + y^2 <= 1).
 * A razao pontos_dentro / total_pontos aproxima PI/4.
 *
 * Compilar: gcc -O2 -o pi_sequencial pi_sequencial.c -lm
 * Executar: ./pi_sequencial [N]
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

int main(int argc, char *argv[]) {
    int N = 10000000;
    if (argc > 1) N = atoi(argv[1]);

    int count = 0;
    double x, y;
    unsigned int seed = time(NULL);

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    for (int i = 0; i < N; i++) {
        x = (double)rand_r(&seed) / RAND_MAX;
        y = (double)rand_r(&seed) / RAND_MAX;
        if (x * x + y * y <= 1.0)
            count++;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) / 1e9;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=sequencial n=%d threads=1\n", N);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);

    return 0;
}
