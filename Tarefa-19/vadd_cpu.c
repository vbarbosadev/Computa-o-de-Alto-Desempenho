#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#define DEFAULT_N 100000000L
#define DEFAULT_REPEATS 5
#define TOL 1.0e-5f

static long parse_long_arg(int argc, char **argv, int index, long fallback)
{
    if (argc <= index) {
        return fallback;
    }

    char *end = NULL;
    long value = strtol(argv[index], &end, 10);
    if (end == argv[index] || value <= 0) {
        fprintf(stderr, "Invalid numeric argument: %s\n", argv[index]);
        exit(2);
    }
    return value;
}

int main(int argc, char **argv)
{
    const long n = parse_long_arg(argc, argv, 1, DEFAULT_N);
    const int repeats = (int)parse_long_arg(argc, argv, 2, DEFAULT_REPEATS);

    float *a = (float *)malloc((size_t)n * sizeof(float));
    float *b = (float *)malloc((size_t)n * sizeof(float));
    float *c = (float *)malloc((size_t)n * sizeof(float));

    if (a == NULL || b == NULL || c == NULL) {
        fprintf(stderr, "Memory allocation failed for n=%ld\n", n);
        free(a);
        free(b);
        free(c);
        return 1;
    }

    double init_time = -omp_get_wtime();
#pragma omp parallel for
    for (long i = 0; i < n; i++) {
        a[i] = (float)i;
        b[i] = 2.0f * (float)i;
        c[i] = 0.0f;
    }
    init_time += omp_get_wtime();

    double best_compute = 1.0e30;
    double sum_compute = 0.0;

    double warmup = -omp_get_wtime();
#pragma omp parallel for
    for (long i = 0; i < n; i++) {
        c[i] = a[i] + b[i];
    }
    warmup += omp_get_wtime();
    (void)warmup;

    for (int r = 0; r < repeats; r++) {
        double t0 = omp_get_wtime();
#pragma omp parallel for
        for (long i = 0; i < n; i++) {
            c[i] = a[i] + b[i];
        }
        double elapsed = omp_get_wtime() - t0;
        if (elapsed < best_compute) {
            best_compute = elapsed;
        }
        sum_compute += elapsed;
    }

    int errors = 0;
    double verify_time = -omp_get_wtime();
#pragma omp parallel for reduction(+ : errors)
    for (long i = 0; i < n; i++) {
        float expected = a[i] + b[i];
        float limit = TOL * fmaxf(1.0f, fabsf(expected));
        if (fabsf(c[i] - expected) > limit) {
            errors++;
        }
    }
    verify_time += omp_get_wtime();

    printf("cpu,host,%ld,%d,%.9f,%.9f,%.9f,%.9f,%d,%d,%d\n",
           n,
           repeats,
           best_compute,
           sum_compute / repeats,
           init_time,
           verify_time,
           errors,
           omp_get_max_threads(),
           omp_get_num_devices());

    free(a);
    free(b);
    free(c);
    return errors == 0 ? 0 : 1;
}
