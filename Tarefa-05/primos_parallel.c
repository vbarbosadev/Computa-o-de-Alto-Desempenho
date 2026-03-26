#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

int is_prime(long int n) {
    if (n <= 1) return 0;
    for (int i = 2; i * i <= n; i++) {
        if (n % i == 0) return 0;
    }
    return 1;
}

#define N 100000000

int main() {

    double start_time = omp_get_wtime();

    int count = 0;
    #pragma omp parallel for
    for (int i = 2; i <= N; i++) {
        if (is_prime(i)) {
            #pragma omp atomic
            count++;
        }
    }
    double end_time = omp_get_wtime();
    printf("Total de numeros primos entre 1 e %d: %d\n", N, count);
    printf("Tempo de execucao: %f segundos\n", end_time - start_time);
    return 0;
}