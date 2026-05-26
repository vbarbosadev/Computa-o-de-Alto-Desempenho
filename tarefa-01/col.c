#include <stdio.h>
#include <stdlib.h>

#ifdef _WIN32
#include <windows.h>
double get_wall_time() {
    LARGE_INTEGER time,freq;
    if (!QueryPerformanceFrequency(&freq)) return 0;
    if (!QueryPerformanceCounter(&time)) return 0;
    return (double)time.QuadPart / freq.QuadPart;
}
#else
#include <sys/time.h>
double get_wall_time() {
    struct timeval time;
    if (gettimeofday(&time,NULL)) return 0;
    return (double)time.tv_sec + (double)time.tv_usec * .000001;
}
#endif

#define N 10000

static int A[N][N];
static int B[N];


static int C[N];


int main() {
    srand(42);

    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            A[i][j] = rand() / RAND_MAX;
            B[i] = rand() / RAND_MAX;
            C[i] = 0;
        }
    }

    printf("Iniciando algoritmo POR COLUNA (coluna externa, linha interna)...\n");
    double start = get_wall_time();


    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            C[i] += B[i] * A[j][i];
        }
    }

    double end = get_wall_time();
    printf("-> Tempo executado (Walltime): %f segundos\n", end - start);

    return 0;
}
