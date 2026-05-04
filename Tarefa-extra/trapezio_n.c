#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

static double f(double x) {
    return sin(x) + x * x;
}

static double trapezoidalRule(double a, double b, int n) {
    double h = (b - a) / (double)n;
    double sum = 0.5 * (f(a) + f(b));

    for (int i = 1; i < n; i++) {
        double x = a + i * h;
        sum += f(x);
    }

    return sum * h;
}

static double diferenca_finita(double x) {
    double h = 0.01;
    return (f(x + h) - f(x - h)) / (2.0 * h);
}

int main(void) {
    double a = 0.0;
    double b = 100.0;
    double c = 56.0;
    int n = 10000;

    double t0 = 0.0;
    double t1 = 0.0;
    double t2 = 0.0;
    double t3 = 0.0;
    double integralAproximada = 0.0;
    double derivadaAproximada = 0.0;

    #pragma omp parallel sections
    {
        #pragma omp section
        {
            t0 = omp_get_wtime();
            integralAproximada = trapezoidalRule(a, b, n);
            t1 = omp_get_wtime();
        }

        #pragma omp section
        {
            t2 = omp_get_wtime();
            derivadaAproximada = diferenca_finita(c);
            t3 = omp_get_wtime();
        }
    }

    printf("Aproximacao da Integral e da Derivada\n");
    printf("Funcao: f(x) = sin(x) + x^2\n");
    printf("Intervalo: [%.2f, %.2f]\n", a, b);
    printf("Numero de trapezios: %d\n", n);
    printf("Integral aproximada: %.6f\n", integralAproximada);
    printf("Tempo integral: %.10f s\n", t1 - t0);
    printf("Derivada aproximada em x = %.2f: %.6f\n", a, derivadaAproximada);
    printf("Tempo derivada: %.10f s\n", t3 - t2);

    return 0;
}
