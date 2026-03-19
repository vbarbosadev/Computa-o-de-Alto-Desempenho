#include <stdio.h>
#include <omp.h>

#define N 100000008  // multiplo de 12

static int A[N];

int main() {
    for (int i = 0; i < N; i++)
        A[i] = i + 2;

    long long soma1  = 0, soma2  = 0, soma3  = 0, soma4  = 0;
    long long soma5  = 0, soma6  = 0, soma7  = 0, soma8  = 0;
    long long soma9  = 0, soma10 = 0, soma11 = 0, soma12 = 0;

    double start = omp_get_wtime();

    for (int i = 0; i < N; i += 12) {
        soma1  += A[i];
        soma2  += A[i + 1];
        soma3  += A[i + 2];
        soma4  += A[i + 3];
        soma5  += A[i + 4];
        soma6  += A[i + 5];
        soma7  += A[i + 6];
        soma8  += A[i + 7];
        soma9  += A[i + 8];
        soma10 += A[i + 9];
        soma11 += A[i + 10];
        soma12 += A[i + 11];
    }

    double end = omp_get_wtime();

    printf("%.6f\n", end - start);
    printf("Soma: %lld\n", soma1  + soma2  + soma3  + soma4  +
                           soma5  + soma6  + soma7  + soma8  +
                           soma9  + soma10 + soma11 + soma12);

    return 0;
}
