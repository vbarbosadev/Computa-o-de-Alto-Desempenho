#include <stdio.h>
#include <math.h>
#include <omp.h>

#define M_PIl 3.14159265358979323846264338327950288L

#define LINE "+-----------+----------+----------------+----------------------------------+-------------+"
#define HEADER "| Iteracoes |  Threads |   Tempo (s)    |             PI aprox             |    Erro     |"

void leibniz_omp(long long n, int num_threads) {
    double start = omp_get_wtime();

    long double sum = 0.0L;

    #pragma omp parallel for 
    for (long long i = 0; i < n; i++) {
        long double term = 1.0L / (2.0L * i + 1.0L);
        sum += (i % 2 == 0) ? term : -term;
    }

    long double pi = 4.0L * sum;
    double end = omp_get_wtime();

    double elapsed = end - start;

    long double erro = fabsl(pi - M_PIl);

    /* linha PI correto (referencia) */
    printf("|           |          |                | %.21Lf (ref)  |             |\n", M_PIl);

    /* linha PI encontrado com marcador de diferenca */
    printf("|           |          |                | %.21Lf        |             |\n", pi);

    /* linha de dados principal */
    printf("| %9lld | %8d | %14.9f | (acima)                   | %11.3Le |\n",
           n, num_threads, elapsed, erro);

    printf("%s\n", LINE);
}

int main() {
    long long iteracoes[] = {
        100000000LL
    };
    int threads[] = {1, 2, 4, 8};

    int ni = sizeof(iteracoes) / sizeof(iteracoes[0]);
    int nt = sizeof(threads) / sizeof(threads[0]);

    printf("\n  omp critical -- Leibniz-Madhava para PI\n\n");
    printf("%s\n", LINE);
    printf("%s\n", HEADER);
    printf("%s\n", LINE);

    for (int i = 0; i < ni; i++)
        for (int j = 0; j < nt; j++)
            leibniz_omp(iteracoes[i], threads[j]);

    return 0;
}

