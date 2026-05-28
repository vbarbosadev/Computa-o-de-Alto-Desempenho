#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int ler_inteiro(int argc, char **argv, const char *opcao, int padrao)
{
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], opcao) == 0) {
            return atoi(argv[i + 1]);
        }
    }
    return padrao;
}

static double valor_a(int i, int j)
{
    return (double)((i + j) % 13 + 1) / 13.0;
}

static double valor_x(int j)
{
    return (double)(j % 7 + 1) / 7.0;
}

static void preencher_x(double *x, int n)
{
    for (int j = 0; j < n; j++) {
        x[j] = valor_x(j);
    }
}

static void preencher_buffer_com_espacamento(double *a_envio, int m, int n, int processos, int colunas_locais, int extensao)
{
    for (int p = 0; p < processos; p++) {
        int coluna_inicial = p * colunas_locais;
        double *base = a_envio + (size_t)p * (size_t)extensao;
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < colunas_locais; j++) {
                base[i * n + j] = valor_a(i, coluna_inicial + j);
            }
        }
    }
}

static void calcular_parcial(double *a_local, double *x_local, double *y_parcial, int m, int colunas_locais)
{
    for (int i = 0; i < m; i++) {
        double soma = 0.0;
        for (int j = 0; j < colunas_locais; j++) {
            soma += a_local[i * colunas_locais + j] * x_local[j];
        }
        y_parcial[i] = soma;
    }
}

int main(int argc, char **argv)
{
    int rank;
    int size;
    int m;
    int n;
    int colunas_locais;
    int extensao_tipo;
    double *a_envio = NULL;
    double *x = NULL;
    double *a_local = NULL;
    double *x_local = NULL;
    double *y_parcial = NULL;
    double *y = NULL;
    MPI_Datatype tipo_colunas;

    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    m = ler_inteiro(argc, argv, "--m", 2000);
    n = ler_inteiro(argc, argv, "--n", 2000);

    if (n % size != 0) {
        if (rank == 0) {
            printf("Para distribuir colunas com MPI_Scatter simples, N deve ser divisivel pelo numero de processos.\n");
        }
        MPI_Finalize();
        return 1;
    }

    colunas_locais = n / size;
    extensao_tipo = (m - 1) * n + colunas_locais;

    MPI_Type_vector(m, colunas_locais, n, MPI_DOUBLE, &tipo_colunas);
    MPI_Type_commit(&tipo_colunas);

    x_local = malloc((size_t)colunas_locais * sizeof(double));
    a_local = malloc((size_t)m * (size_t)colunas_locais * sizeof(double));
    y_parcial = malloc((size_t)m * sizeof(double));

    if (rank == 0) {
        x = malloc((size_t)n * sizeof(double));
        y = malloc((size_t)m * sizeof(double));
        a_envio = calloc((size_t)size * (size_t)extensao_tipo, sizeof(double));
        if (x != NULL && a_envio != NULL) {
            preencher_x(x, n);
            preencher_buffer_com_espacamento(a_envio, m, n, size, colunas_locais, extensao_tipo);
        }
    }

    if (x_local == NULL || a_local == NULL || y_parcial == NULL || (rank == 0 && (x == NULL || y == NULL || a_envio == NULL))) {
        printf("Erro ao alocar memoria no rank %d.\n", rank);
        free(a_envio);
        free(x);
        free(a_local);
        free(x_local);
        free(y_parcial);
        free(y);
        MPI_Type_free(&tipo_colunas);
        MPI_Finalize();
        return 1;
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double inicio = MPI_Wtime();

    MPI_Scatter(x, colunas_locais, MPI_DOUBLE, x_local, colunas_locais, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Scatter(a_envio, 1, tipo_colunas, a_local, m * colunas_locais, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    calcular_parcial(a_local, x_local, y_parcial, m, colunas_locais);

    MPI_Reduce(y_parcial, y, m, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    double fim = MPI_Wtime();

    if (rank == 0) {
        double checksum = 0.0;
        for (int i = 0; i < m; i++) {
            checksum += y[i];
        }
        printf(
            "RESULT versao=cols_vector processos=%d m=%d n=%d colunas_por_processo=%d tempo=%.9f checksum=%.6f\n",
            size,
            m,
            n,
            colunas_locais,
            fim - inicio,
            checksum
        );
    }

    free(a_envio);
    free(x);
    free(a_local);
    free(x_local);
    free(y_parcial);
    free(y);
    MPI_Type_free(&tipo_colunas);
    MPI_Finalize();
    return 0;
}
