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


static double f(double x) {
    return sin(x) + x * x;
}

static int ler_argumentos(int argc, char *argv[], double *a, double *b, long *n) {
    *a = 0.0;
    *b = 5.0;
    *n = 1000000L;

    if (argc > 1) {
        *a = atof(argv[1]);
    }
    if (argc > 2) {
        *b = atof(argv[2]);
    }
    if (argc > 3) {
        *n = atol(argv[3]);
    }

    if (*n < 2) {
        fprintf(stderr, "Erro: n deve ser >= 2.\n");
        return 0;
    }

    if (*a >= *b) {
        fprintf(stderr, "Erro: informe um intervalo valido com a < b.\n");
        return 0;
    }

    return 1;
}

int main(int argc, char *argv[]) {
    double a, b;
    long n;

    if (!ler_argumentos(argc, argv, &a, &b, &n)) {
        return 1;
    }

    double *x = (double *)malloc((size_t)n * sizeof(double));
    if (x == NULL) {
        fprintf(stderr, "Erro: nao foi possivel alocar o vetor de pontos.\n");
        return 1;
    }

    double h = (b - a) / (double)(n - 1);
    double soma = 0.0;
    double t0 = omp_get_wtime();

    // #pragma omp parallel for schedule(static)
    # pragma omp parallel section
     {
        #pragma omp section
         for (long i = 0; i < n; i++) {
            x[i] = a + (double)i * h;
        }

        double soma_local = 0.0;
        #pragma omp section
        for (long i = 1; i < n - 1; i++) {
            soma_local += f(x[i]);
        }

        #pragma omp atomic
        soma += soma_local;
    }
    for (long i = 0; i < n; i++) {
        x[i] = a + (double)i * h;
    }

    // #pragma omp parallel for schedule(static) reduction(+:soma)
    for (long i = 1; i < n - 1; i++) {
        soma += f(x[i]);
    }

    double integral = h * (0.5 * f(x[0]) + soma + 0.5 * f(x[n - 1]));
    double elapsed = omp_get_wtime() - t0;

    printf("Metodo do trapezio\n");
    printf("f(x) = sin(x) + x^2\n");
    printf("Intervalo: [%.6f, %.6f]\n", a, b);
    printf("Pontos discretos: %ld\n", n);
    printf("Passo h: %.10f\n", h);
    printf("Integral aproximada: %.12f\n", integral);
    printf("Tempo: %.6f s\n", elapsed);

    free(x);
    return 0;
}
