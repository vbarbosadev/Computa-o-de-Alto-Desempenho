#include <stdio.h>
#include <math.h>
#include <omp.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

// Serie de Leibniz: pi/4 = 1 - 1/3 + 1/5 - 1/7 + ...
// Convergencia lenta: precisa de muitos termos para boa precisao
void leibniz(long long n) {
    double start = omp_get_wtime();

    double sum = 0.0;
    for (long long i = 0; i < n; i++) {
        double term = 1.0 / (2.0 * i + 1.0);
        sum += (i % 2 == 0) ? term : -term;
    }

    double pi = 4.0 * sum;
    double end = omp_get_wtime();

    double erro = fabs(pi - M_PI);
    // output CSV: iteracoes,segundos,pi_aprox,erro
    printf("%lld,%.9f,%.17f,%.3e\n", n, end - start, pi, erro);
}

int main() {
    long long iteracoes[] = {
        10, 100, 1000, 10000, 100000,
        1000000, 10000000, 100000000
    };
    int n = sizeof(iteracoes) / sizeof(iteracoes[0]);

    printf("# M_PI (referencia): %.17f\n", M_PI);
    printf("iteracoes,segundos,pi_aprox,erro\n");
    for (int i = 0; i < n; i++)
        leibniz(iteracoes[i]);

    return 0;
}
