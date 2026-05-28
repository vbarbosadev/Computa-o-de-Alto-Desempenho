#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAG_DIREITA 10
#define TAG_ESQUERDA 20

static int ler_inteiro(int argc, char **argv, const char *opcao, int padrao)
{
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], opcao) == 0) {
            return atoi(argv[i + 1]);
        }
    }
    return padrao;
}

static int inicio_local(int rank, int n, int size)
{
    int base = n / size;
    int resto = n % size;
    return rank * base + (rank < resto ? rank : resto);
}

static int tamanho_local(int rank, int n, int size)
{
    int base = n / size;
    int resto = n % size;
    return base + (rank < resto ? 1 : 0);
}

static void inicializar(double *u, int local_n, int inicio)
{
    for (int i = 0; i <= local_n + 1; i++) {
        u[i] = 0.0;
    }
    for (int i = 1; i <= local_n; i++) {
        int global = inicio + i - 1;
        u[i] = (global >= 45 && global <= 55) ? 100.0 : 0.0;
    }
}

static int iniciar_troca(double *u, int local_n, int rank, int size, MPI_Request pedidos[])
{
    int qtd = 0;

    if (rank > 0) {
        MPI_Irecv(&u[0], 1, MPI_DOUBLE, rank - 1, TAG_DIREITA, MPI_COMM_WORLD, &pedidos[qtd++]);
        MPI_Isend(&u[1], 1, MPI_DOUBLE, rank - 1, TAG_ESQUERDA, MPI_COMM_WORLD, &pedidos[qtd++]);
    } else {
        u[0] = 0.0;
    }

    if (rank < size - 1) {
        MPI_Irecv(&u[local_n + 1], 1, MPI_DOUBLE, rank + 1, TAG_ESQUERDA, MPI_COMM_WORLD, &pedidos[qtd++]);
        MPI_Isend(&u[local_n], 1, MPI_DOUBLE, rank + 1, TAG_DIREITA, MPI_COMM_WORLD, &pedidos[qtd++]);
    } else {
        u[local_n + 1] = 0.0;
    }

    return qtd;
}

static void esperar_troca(MPI_Request pedidos[], int qtd)
{
    MPI_Status status;
    for (int i = 0; i < qtd; i++) {
        MPI_Wait(&pedidos[i], &status);
    }
}

static void atualizar(double *u, double *novo, int local_n, double alpha)
{
    for (int i = 1; i <= local_n; i++) {
        novo[i] = u[i] + alpha * (u[i - 1] - 2.0 * u[i] + u[i + 1]);
    }
}

static double soma_local(double *u, int local_n)
{
    double soma = 0.0;
    for (int i = 1; i <= local_n; i++) {
        soma += u[i];
    }
    return soma;
}

int main(int argc, char **argv)
{
    int rank;
    int size;
    int n;
    int passos;
    int local_n;
    int inicio;
    double alpha = 0.25;
    double *u;
    double *novo;
    MPI_Request pedidos[4];

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    n = ler_inteiro(argc, argv, "--n", 100000);
    passos = ler_inteiro(argc, argv, "--passos", 1000);
    local_n = tamanho_local(rank, n, size);
    inicio = inicio_local(rank, n, size);

    if (local_n <= 0) {
        if (rank == 0) {
            printf("Use n maior ou igual ao numero de processos.\n");
        }
        MPI_Finalize();
        return 1;
    }

    u = malloc((size_t)(local_n + 2) * sizeof(double));
    novo = malloc((size_t)(local_n + 2) * sizeof(double));
    if (u == NULL || novo == NULL) {
        printf("Erro ao alocar memoria no rank %d.\n", rank);
        MPI_Finalize();
        return 1;
    }

    inicializar(u, local_n, inicio);
    inicializar(novo, local_n, inicio);

    double inicio_tempo = MPI_Wtime();
    for (int passo = 0; passo < passos; passo++) {
        int qtd = iniciar_troca(u, local_n, rank, size, pedidos);
        esperar_troca(pedidos, qtd);
        atualizar(u, novo, local_n, alpha);
        double *tmp = u;
        u = novo;
        novo = tmp;
    }
    double fim_tempo = MPI_Wtime();

    printf(
        "RESULT versao=isend_irecv_wait rank=%d processos=%d n=%d local_n=%d passos=%d tempo=%.9f soma=%.6f\n",
        rank,
        size,
        n,
        local_n,
        passos,
        fim_tempo - inicio_tempo,
        soma_local(u, local_n)
    );

    free(u);
    free(novo);
    MPI_Finalize();
    return 0;
}
