#include <stdio.h>
#include <omp.h>

#define N 100000000

static int A[N];

int main() {
    for (int i = 0; i < N; i++)
        A[i] = i + 2;

    long long soma1 = 0, soma2 = 0, soma3 = 0, soma4 = 0;

    double start = omp_get_wtime();

    for (int i = 0; i < N; i += 4) {
        soma1 += A[i];
        soma2 += A[i + 1];
        soma3 += A[i + 2];
        soma4 += A[i + 3];
    }

    double end = omp_get_wtime();

    printf("%.6f\n", end - start);
    printf("Soma: %lld\n", soma1 + soma2 + soma3 + soma4);

    return 0;
}
