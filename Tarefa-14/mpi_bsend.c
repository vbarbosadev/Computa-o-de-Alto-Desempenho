#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAG_IDA 10
#define TAG_VOLTA 20

static int ler_inteiro(int argc, char **argv, const char *opcao, int padrao)
{
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], opcao) == 0) {
            return atoi(argv[i + 1]);
        }
    }
    return padrao;
}

int main(int argc, char **argv)
{
    int rank;
    int size;
    int bytes;
    int iteracoes;
    int tamanho_buffer;
    char *mensagem;
    char *buffer;
    MPI_Status status;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (size != 2) {
        if (rank == 0) {
            printf("Execute com exatamente 2 processos: mpirun -np 2 ./mpi_bsend\n");
        }
        MPI_Finalize();
        return 1;
    }

    bytes = ler_inteiro(argc, argv, "--bytes", 8);
    iteracoes = ler_inteiro(argc, argv, "--iteracoes", 1000);

    mensagem = malloc((size_t)bytes);
    tamanho_buffer = bytes + MPI_BSEND_OVERHEAD;
    buffer = malloc((size_t)tamanho_buffer);
    if (mensagem == NULL || buffer == NULL) {
        printf("Erro ao alocar memoria.\n");
        MPI_Finalize();
        return 1;
    }

    MPI_Buffer_attach(buffer, tamanho_buffer);
    memset(mensagem, 'A' + rank, (size_t)bytes);

    double inicio = MPI_Wtime();

    for (int i = 0; i < iteracoes; i++) {
        if (rank == 0) {
            MPI_Bsend(mensagem, bytes, MPI_BYTE, 1, TAG_IDA, MPI_COMM_WORLD);
            MPI_Recv(mensagem, bytes, MPI_BYTE, 1, TAG_VOLTA, MPI_COMM_WORLD, &status);
        } else {
            MPI_Recv(mensagem, bytes, MPI_BYTE, 0, TAG_IDA, MPI_COMM_WORLD, &status);
            MPI_Bsend(mensagem, bytes, MPI_BYTE, 0, TAG_VOLTA, MPI_COMM_WORLD);
        }
    }

    double fim = MPI_Wtime();

    if (rank == 0) {
        printf(
            "RESULT metodo=MPI_Bsend bytes=%d iteracoes=%d tempo_total=%.9f tempo_medio=%.12f\n",
            bytes,
            iteracoes,
            fim - inicio,
            (fim - inicio) / iteracoes
        );
    }

    MPI_Buffer_detach(&buffer, &tamanho_buffer);
    free(buffer);
    free(mensagem);
    MPI_Finalize();
    return 0;
}
