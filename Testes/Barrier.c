#include <stdio.h>
#include <mpi.h>



int main(int argc, char *argv[]) {
    int rank, size;
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (rank == 0) {
        printf("Estou atrasado para a barreira ! \n");
        getchar();
    }

    MPI_Barrier(MPI_COMM_WORLD);
    printf("Process %d passed the barrier of %d processes\n", rank, size);
    MPI_Finalize();
    return 0;
}