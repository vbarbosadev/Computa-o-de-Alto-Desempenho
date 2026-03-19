#include <stdio.h>
#include <math.h>
#include <omp.h>

#define M_PIl 3.14159265358979323846264338327950288L

// Serie de Leibniz paralelizada com OpenMP
// long double: mais precisao; reduction garante soma correta entre threads
void leibniz_omp(long long n, int num_threads) {
    double start = omp_get_wtime();

    long double sum = 0.0L;

    #pragma omp parallel for reduction(+:sum) num_threads(num_threads)
    for (long long i = 0; i < n; i++) {
        long double term = 1.0L / (2.0L * i + 1.0L);
        sum += (i % 2 == 0) ? term : -term;
    }

    long double pi = 4.0L * sum;
    double end = omp_get_wtime();

    long double erro = fabsl(pi - M_PIl);
    // output CSV: iteracoes,threads,segundos,pi_aprox,erro
    printf("%lld,%d,%.9f,%.21Lf,%.3Le\n", n, num_threads, end - start, pi, erro);
}

int main() {
    long long iteracoes[] = {
        100000000LL, 1000000000LL, 5000000000LL
    };
    int threads[] = {1, 2, 4, 8};

    int ni = sizeof(iteracoes) / sizeof(iteracoes[0]);
    int nt = sizeof(threads) / sizeof(threads[0]);

    printf("# M_PI (referencia): %.21Lf\n", M_PIl);
    printf("iteracoes,threads,segundos,pi_aprox,erro\n");
    for (int i = 0; i < ni; i++)
        for (int j = 0; j < nt; j++)
            leibniz_omp(iteracoes[i], threads[j]);

    return 0;
}
