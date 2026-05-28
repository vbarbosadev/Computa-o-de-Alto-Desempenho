#include <stdio.h>
#include <mpi.h>



int main(int argc, char *argv[]) {
    int rank, size;
    int v;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        v = 42;
        printf("Process 0 sending value %d to process 1\n", v);
    }

    MPI_Bcast(&v, 1, MPI_INT, 0, MPI_COMM_WORLD);
    printf("Process %d received value %d\n", rank, v);
    MPI_Finalize();
    return 0;
}