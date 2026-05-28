#include <math.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define TAG_TAREFA 10
#define TAG_RESULTADO 20
#define TAG_PARAR 30

static int ler_inteiro(int argc, char **argv, const char *opcao, int padrao)
{
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], opcao) == 0) {
            return atoi(argv[i + 1]);
        }
    }
    return padrao;
}

static int eh_primo(int n)
{
    if (n < 2) {
        return 0;
    }
    if (n == 2) {
        return 1;
    }
    if (n % 2 == 0) {
        return 0;
    }

    int limite = (int)sqrt((double)n);
    for (int d = 3; d <= limite; d += 2) {
        if (n % d == 0) {
            return 0;
        }
    }
    return 1;
}

static int contar_primos(int inicio, int fim)
{
    int total = 0;
    for (int n = inicio; n <= fim; n++) {
        total += eh_primo(n);
    }
    return total;
}

static void montar_tarefa(int indice, int total_tarefas, int maximo, int tarefa[3])
{
    int quantidade = maximo - 1;
    int base = quantidade / total_tarefas;
    int resto = quantidade % total_tarefas;
    int tamanho = base + (indice < resto ? 1 : 0);
    int deslocamento = indice * base + (indice < resto ? indice : resto);

    tarefa[0] = indice;
    tarefa[1] = 2 + deslocamento;
    tarefa[2] = tarefa[1] + tamanho - 1;
}

static void lider(int size, int maximo, int total_tarefas)
{
    int trabalhadores = size - 1;
    int proxima_tarefa = 0;
    int tarefas_concluidas = 0;
    int total_primos = 0;
    int tarefas_por_trabalhador[size];
    MPI_Status status;

    for (int i = 0; i < size; i++) {
        tarefas_por_trabalhador[i] = 0;
    }

    double inicio = MPI_Wtime();

    for (int worker = 1; worker <= trabalhadores; worker++) {
        if (proxima_tarefa < total_tarefas) {
            int tarefa[3];
            montar_tarefa(proxima_tarefa, total_tarefas, maximo, tarefa);
            MPI_Send(tarefa, 3, MPI_INT, worker, TAG_TAREFA, MPI_COMM_WORLD);
            proxima_tarefa++;
        } else {
            int vazio[3] = {-1, 0, 0};
            MPI_Send(vazio, 3, MPI_INT, worker, TAG_PARAR, MPI_COMM_WORLD);
        }
    }

    while (tarefas_concluidas < total_tarefas) {
        int resultado[3];
        MPI_Recv(resultado, 3, MPI_INT, MPI_ANY_SOURCE, TAG_RESULTADO, MPI_COMM_WORLD, &status);

        int worker = status.MPI_SOURCE;
        tarefas_concluidas++;
        total_primos += resultado[2];
        tarefas_por_trabalhador[worker]++;

        if (proxima_tarefa < total_tarefas) {
            int tarefa[3];
            montar_tarefa(proxima_tarefa, total_tarefas, maximo, tarefa);
            MPI_Send(tarefa, 3, MPI_INT, worker, TAG_TAREFA, MPI_COMM_WORLD);
            proxima_tarefa++;
        } else {
            int vazio[3] = {-1, 0, 0};
            MPI_Send(vazio, 3, MPI_INT, worker, TAG_PARAR, MPI_COMM_WORLD);
        }
    }

    double fim = MPI_Wtime();

    printf(
        "RESULT versao=leader_worker processos=%d trabalhadores=%d max=%d tarefas=%d primos=%d tempo=%.9f",
        size,
        trabalhadores,
        maximo,
        total_tarefas,
        total_primos,
        fim - inicio
    );
    for (int worker = 1; worker <= trabalhadores; worker++) {
        printf(" w%d=%d", worker, tarefas_por_trabalhador[worker]);
    }
    printf("\n");
}

static void trabalhador(int rank)
{
    MPI_Status status;

    while (1) {
        int tarefa[3];
        MPI_Recv(tarefa, 3, MPI_INT, 0, MPI_ANY_TAG, MPI_COMM_WORLD, &status);

        if (status.MPI_TAG == TAG_PARAR || tarefa[0] < 0) {
            break;
        }

        int resultado[3];
        resultado[0] = tarefa[0];
        resultado[1] = rank;
        resultado[2] = contar_primos(tarefa[1], tarefa[2]);
        MPI_Send(resultado, 3, MPI_INT, 0, TAG_RESULTADO, MPI_COMM_WORLD);
    }
}

int main(int argc, char **argv)
{
    int rank;
    int size;
    int maximo;
    int total_tarefas;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    maximo = ler_inteiro(argc, argv, "--max", 1000000);
    total_tarefas = ler_inteiro(argc, argv, "--tarefas", 32);

    if (size < 2) {
        if (rank == 0) {
            printf("Execute com pelo menos 2 processos: 1 lider e 1 trabalhador.\n");
        }
        MPI_Finalize();
        return 1;
    }

    if (total_tarefas < 1 || maximo < 2) {
        if (rank == 0) {
            printf("Use --max >= 2 e --tarefas >= 1.\n");
        }
        MPI_Finalize();
        return 1;
    }

    if (rank == 0) {
        lider(size, maximo, total_tarefas);
    } else {
        trabalhador(rank);
    }

    MPI_Finalize();
    return 0;
}
