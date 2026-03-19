#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

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

#define N 100000000

int main(int argc, char *argv[]) {
    double *A = (double*)malloc(N * sizeof(double));
    double *B = (double*)malloc(N * sizeof(double));
    double *C = (double*)malloc(N * sizeof(double));
    
    // #pragma omp parallel
    for(long i = 0; i < N; i++) {
        A[i] = 1.0;
        B[i] = 2.0;
    }

    double start_time = omp_get_wtime();

    #pragma omp parallel for
    for(long i = 0; i < N; i++) {
        C[i] = A[i] + B[i];
    }

    double end_time = omp_get_wtime();

    printf("Memory-bound: Tempo de execucao do laco = %f segundos\n", end_time - start_time);

    free(A); free(B); free(C);
    return 0;
    
}