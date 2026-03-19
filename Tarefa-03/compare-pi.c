#include <stdio.h>
#include <math.h>
#include <omp.h>

// M_PI pode nao estar definido sem _GNU_SOURCE em alguns compiladores
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

void gauss_legendre(int it) {
    double a = 1.0;
    double b = 1.0 / sqrt(2.0);
    double t = 0.25;
    double p = 1.0;
    double a_next, pi;

    double start = omp_get_wtime();

    for (int i = 0; i < it; i++) {
        a_next = (a + b) / 2.0;
        t -= p * (a - a_next) * (a - a_next);
        b = sqrt(a * b);
        a = a_next;
        p = 2.0 * p;
    }

    pi = ((a + b) * (a + b)) / (4.0 * t);

    double end = omp_get_wtime();

    double erro = fabs(pi - M_PI);
    // output CSV: iteracoes,segundos,pi_aprox,erro
    printf("%d,%.9f,%.15f,%.2e\n", it, end - start, pi, erro);
}

int main() {
    int iteracoes[] = {1, 2, 3, 4, 5, 10, 20, 50};
    int n = sizeof(iteracoes) / sizeof(iteracoes[0]);

    printf("iteracoes,segundos,pi_aprox,erro\n");
    for (int i = 0; i < n; i++)
        gauss_legendre(iteracoes[i]);

    return 0;
}
