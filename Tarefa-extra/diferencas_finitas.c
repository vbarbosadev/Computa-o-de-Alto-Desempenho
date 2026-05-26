#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#ifdef _OPENMP
#include <omp.h>
#else
static double omp_get_wtime(void) {
    return 0.0;
}
#endif

/*
 * Aproximacao numerica da derivada de f(x)
 * com pontos discretos usando diferenciacao finita.
 *
 * Regra usada:
 * - diferenca para frente no primeiro ponto
 * - diferenca central nos pontos internos
 * - diferenca para tras no ultimo ponto
 *
 * Compilar:
 *   gcc -O2 -fopenmp -o diferencas_finitas diferencas_finitas.c -lm
 *
 * Executar:
 *   ./diferencas_finitas [a] [b] [n]
 */

static double f(double x) {
    return sin(x) + x * x;
}

static int ler_argumentos(int argc, char *argv[], double *a, double *b, long *n) {
    *a = 0.0;
    *b = 5.0;
    *n = 21L;

    if (argc > 1) {
        *a = atof(argv[1]);
    }
    if (argc > 2) {
        *b = atof(argv[2]);
    }
    if (argc > 3) {
        *n = atol(argv[3]);
    }

    if (*n < 3) {
        fprintf(stderr, "Erro: n deve ser >= 3 para calcular a derivada.\n");
        return 0;
    }

    if (*a >= *b) {
        fprintf(stderr, "Erro: informe um intervalo valido com a < b.\n");
        return 0;
    }

    return 1;
}

static void imprimir_amostra(const double *x, const double *y, const double *dy, long n) {
    long limite = (n <= 10) ? n : 5;

    printf("      x            f(x)         f'(x) aprox\n");
    for (long i = 0; i < limite; i++) {
        printf("%10.6f   %12.6f   %12.6f\n", x[i], y[i], dy[i]);
    }

    if (n > 10) {
        printf("        ...            ...            ...\n");
        for (long i = n - 5; i < n; i++) {
            printf("%10.6f   %12.6f   %12.6f\n", x[i], y[i], dy[i]);
        }
    }
}

int main(int argc, char *argv[]) {
    double a, b;
    long n;

    if (!ler_argumentos(argc, argv, &a, &b, &n)) {
        return 1;
    }

    double *x = (double *)malloc((size_t)n * sizeof(double));
    double *y = (double *)malloc((size_t)n * sizeof(double));
    double *dy = (double *)malloc((size_t)n * sizeof(double));

    if (x == NULL || y == NULL || dy == NULL) {
        fprintf(stderr, "Erro: nao foi possivel alocar os vetores.\n");
        free(x);
        free(y);
        free(dy);
        return 1;
    }

    double h = (b - a) / (double)(n - 1);
    double t0 = omp_get_wtime();

    // #pragma omp parallel for schedule(static)
    for (long i = 0; i < n; i++) {
        x[i] = a + (double)i * h;
        y[i] = f(x[i]);
    }

    dy[0] = (y[1] - y[0]) / h;
    dy[n - 1] = (y[n - 1] - y[n - 2]) / h;

    // #pragma omp parallel for schedule(static)
    for (long i = 1; i < n - 1; i++) {
        dy[i] = (y[i + 1] - y[i - 1]) / (2.0 * h);
    }

    double elapsed = omp_get_wtime() - t0;

    printf("Diferenciacao finita\n");
    printf("f(x) = sin(x) + x^2\n");
    printf("Intervalo: [%.6f, %.6f]\n", a, b);
    printf("Pontos discretos: %ld\n", n);
    printf("Passo h: %.10f\n", h);
    imprimir_amostra(x, y, dy, n);
    printf("Tempo: %.6f s\n", elapsed);

    free(x);
    free(y);
    free(dy);
    return 0;
}
