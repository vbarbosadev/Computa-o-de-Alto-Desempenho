#include <stdio.h>
#include <omp.h>

int main () {
    # pragma omp parallel num_threads(4)
    {
        int id = omp_get_thread_num();
        printf("Hello from thread %d\n", id);
    #pragma opm parallel for
    for (int i=0; i<10; i++){
        printf("Thread %d is processing iteration %d\n", id, i);
    }
    

    }

}