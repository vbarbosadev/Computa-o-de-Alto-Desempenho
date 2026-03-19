#include <stdio.h>
#include <math.h>
#include <omp.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Serie de Leibniz paralelizada com OpenMP
// Cada thread calcula um subconjunto dos termos (reduction garante soma correta)
void leibniz_omp(long long n, int num_threads) {
    double start = omp_get_wtime();

    double sum = 0.0;

    #pragma omp parallel for reduction(+:sum) num_threads(num_threads)
    for (long long i = 0; i < n; i++) {
        double term = 1.0 / (2.0 * i + 1.0);
        sum += (i % 2 == 0) ? term : -term;
    }

    double pi = 4.0 * sum;
    double end = omp_get_wtime();

    double erro = fabs(pi - M_PI);
    // output CSV: iteracoes,threads,segundos,pi_aprox,erro
    printf("%lld,%d,%.9f,%.17f,%.3e\n", n, num_threads, end - start, pi, erro);
}

int main() {
    long long iteracoes[] = {
        10000000, 100000000, 1000000000
    };
    int threads[] = {1, 2, 4, 8};

    int ni = sizeof(iteracoes) / sizeof(iteracoes[0]);
    int nt = sizeof(threads) / sizeof(threads[0]);

    printf("# M_PI (referencia): %.17f\n", M_PI);
    printf("iteracoes,threads,segundos,pi_aprox,erro\n");
    for (int i = 0; i < ni; i++)
        for (int j = 0; j < nt; j++)
            leibniz_omp(iteracoes[i], threads[j]);

    return 0;
}
