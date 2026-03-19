#include <stdio.h>
#include <math.h>
#include <omp.h>

// Referencia com casas extras para long double (18-19 digitos significativos)
#define M_PIl 3.14159265358979323846264338327950288L

// Serie de Leibniz: pi/4 = 1 - 1/3 + 1/5 - 1/7 + ...
// long double: ~18-19 digitos significativos vs ~15-16 do double
void leibniz(long long n) {
    double start = omp_get_wtime();

    long double sum = 0.0L;
    for (long long i = 0; i < n; i++) {
        long double term = 1.0L / (2.0L * i + 1.0L);
        sum += (i % 2 == 0) ? term : -term;
    }

    long double pi = 4.0L * sum;
    double end = omp_get_wtime();

    long double erro = fabsl(pi - M_PIl);
    // output CSV: iteracoes,segundos,pi_aprox,erro
    printf("%lld,%.9f,%.21Lf,%.3Le\n", n, end - start, pi, erro);
}

int main() {
    long long iteracoes[] = {
        10, 100, 1000, 10000, 100000,
        1000000, 10000000, 100000000,
        1000000000LL, 5000000000LL
    };
    int n = sizeof(iteracoes) / sizeof(iteracoes[0]);

    printf("# M_PI (referencia): %.21Lf\n", M_PIl);
    printf("iteracoes,segundos,pi_aprox,erro\n");
    for (int i = 0; i < n; i++)
        leibniz(iteracoes[i]);

    return 0;
}
