// Carregue o module do SDK da Nvidia:
//      $ module load compilers/nvidia/nvhpc/24.11
// Compile seu código com o compilador da Nvidia
//      $ nvc -fast -mp=gpu gputest.c
// Rode um job com seu código e confira se está rodando na GPU corretamente.
//      $ sbatch gputest.sh
//      $ squeue -u $USER
//      $ cat gputest-<job_id>.out
//      $ cat gputest-1849633.out


#include <stdio.h>   // For printf
#include <stdlib.h>  // For malloc, free
#include <time.h>    // For clock_gettime and struct timespec
#include <omp.h>     // For OpenMP functions like omp_get_num_devices

// Function to perform vector addition on the host (CPU)
void vector_add_host(int* a, int* b, int* c, int N) {
    for (int i = 0; i < N; ++i) {
        c[i] = a[i] + b[i];
    }
}

int main() {
    const int N = 1024 * 1024; // Size of the vectors (e.g., 1 million elements)

    // Declare and allocate host arrays
    int* a_host = (int*)malloc(N * sizeof(int));
    int* b_host = (int*)malloc(N * sizeof(int));
    int* c_host_cpu = (int*)malloc(N * sizeof(int)); // Result for CPU computation
    int* c_host_gpu = (int*)malloc(N * sizeof(int)); // Result for GPU computation

    // Check for successful memory allocation
    if (a_host == NULL || b_host == NULL || c_host_cpu == NULL || c_host_gpu == NULL) {
        fprintf(stderr, "Memory allocation failed!\n");
        return 1;
    }

    // Initialize host vectors
    for (int i = 0; i < N; ++i) {
        a_host[i] = i;
        b_host[i] = i * 2;
    }

    printf("--- OpenMP GPU Offloading Test (C Version) ---\n");
    printf("Vector size: %d\n", N);

    // Check for OpenMP device availability
    int num_devices = omp_get_num_devices();
    printf("Number of OpenMP devices available: %d\n", num_devices);
    if (num_devices == 0) {
        printf("WARNING: No OpenMP target devices found. Code might run on host or offloading might fail.\n");
        printf("Consider setting OMP_TARGET_OFFLOAD=MANDATORY environment variable to force offloading.\n");
    }

    // --- CPU Computation ---
    struct timespec start_cpu, end_cpu;
    clock_gettime(CLOCK_MONOTONIC, &start_cpu);
    vector_add_host(a_host, b_host, c_host_cpu, N);
    clock_gettime(CLOCK_MONOTONIC, &end_cpu);

    double duration_cpu = (end_cpu.tv_sec - start_cpu.tv_sec) + (end_cpu.tv_nsec - start_cpu.tv_nsec) / 1e9;
    printf("CPU computation time: %f seconds\n", duration_cpu);

    // Initialize c_host_gpu with a distinct value to clearly see if it's overwritten by GPU
    for (int i = 0; i < N; ++i) {
        c_host_gpu[i] = -999; // A clear indicator if GPU doesn't write to it
    }

    // --- GPU Offloading with OpenMP ---
    struct timespec start_gpu, end_gpu;
    clock_gettime(CLOCK_MONOTONIC, &start_gpu);

    #pragma omp target map(to:a_host[0:N], b_host[0:N]) map(from:c_host_gpu[0:N])
    {
        // Inside the target region, the code runs on the GPU.
        // The #pragma omp parallel for distributes iterations among GPU threads.
        #pragma omp parallel for
        for (int i = 0; i < N; ++i) {
            c_host_gpu[i] = a_host[i] + b_host[i];
            // Debugging print (use with caution, might impact performance or not work on all devices)
            // Uncomment the following line for very small N to see device-side values:
            // if (i == 0) {
            //     // printf("DEBUG (GPU): a_host[0]=%d, b_host[0]=%d, c_host_gpu[0]=%d\n", a_host[0], b_host[0], c_host_gpu[0]);
            // }
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &end_gpu);
    double duration_gpu = (end_gpu.tv_sec - start_gpu.tv_sec) + (end_gpu.tv_nsec - start_gpu.tv_nsec) / 1e9;
    printf("GPU offloading time: %f seconds\n", duration_gpu);

    // --- Verification ---
    int success = 1; // True
    for (int i = 0; i < N; ++i) {
        if (c_host_cpu[i] != c_host_gpu[i]) {
            printf("Verification failed at index %d: CPU=%d, GPU=%d\n", i, c_host_cpu[i], c_host_gpu[i]);
            success = 0; // False
            // Do not break here, to show more differing elements if needed for debugging
        }
    }

    if (success) {
        printf("Verification successful: CPU and GPU results match.\n");
    } else {
        printf("Verification failed.\n");
    }

    // Optional: Print a few results to confirm
    printf("\nSample results (first 5 elements):\n");
    for (int i = 0; i < 5; ++i) {
        // Corrected printf format string for c_gpu
        printf("c_cpu[%d] = %d, c_gpu[%d] = %d\n", i, c_host_cpu[i], i, c_host_gpu[i]);
    }

    // Free dynamically allocated memory
    free(a_host);
    free(b_host);
    free(c_host_cpu);
    free(c_host_gpu);

    return 0;
}

