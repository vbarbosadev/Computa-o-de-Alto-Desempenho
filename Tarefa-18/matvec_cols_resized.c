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

static void preencher_matriz(double *a, int m, int n)
{
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            a[i * n + j] = valor_a(i, j);
        }
    }
}

static void preencher_x(double *x, int n)
{
    for (int j = 0; j < n; j++) {
        x[j] = valor_x(j);
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
    double *a = NULL;
    double *x = NULL;
    double *a_local = NULL;
    double *x_local = NULL;
    double *y_parcial = NULL;
    double *y = NULL;
    MPI_Datatype tipo_colunas;
    MPI_Datatype tipo_colunas_redimensionado;

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

    MPI_Type_vector(m, colunas_locais, n, MPI_DOUBLE, &tipo_colunas);
    MPI_Type_create_resized(tipo_colunas, 0, (MPI_Aint)colunas_locais * (MPI_Aint)sizeof(double), &tipo_colunas_redimensionado);
    MPI_Type_commit(&tipo_colunas_redimensionado);

    x_local = malloc((size_t)colunas_locais * sizeof(double));
    a_local = malloc((size_t)m * (size_t)colunas_locais * sizeof(double));
    y_parcial = malloc((size_t)m * sizeof(double));

    if (rank == 0) {
        a = malloc((size_t)m * (size_t)n * sizeof(double));
        x = malloc((size_t)n * sizeof(double));
        y = malloc((size_t)m * sizeof(double));
        if (a != NULL && x != NULL) {
            preencher_matriz(a, m, n);
            preencher_x(x, n);
        }
    }

    if (x_local == NULL || a_local == NULL || y_parcial == NULL || (rank == 0 && (a == NULL || x == NULL || y == NULL))) {
        printf("Erro ao alocar memoria no rank %d.\n", rank);
        free(a);
        free(x);
        free(a_local);
        free(x_local);
        free(y_parcial);
        free(y);
        MPI_Type_free(&tipo_colunas_redimensionado);
        MPI_Type_free(&tipo_colunas);
        MPI_Finalize();
        return 1;
    }

    MPI_Barrier(MPI_COMM_WORLD);
    double inicio = MPI_Wtime();

    MPI_Scatter(x, colunas_locais, MPI_DOUBLE, x_local, colunas_locais, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    MPI_Scatter(a, 1, tipo_colunas_redimensionado, a_local, m * colunas_locais, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    calcular_parcial(a_local, x_local, y_parcial, m, colunas_locais);

    MPI_Reduce(y_parcial, y, m, MPI_DOUBLE, MPI_SUM, 0, MPI_COMM_WORLD);

    double fim = MPI_Wtime();

    if (rank == 0) {
        double checksum = 0.0;
        for (int i = 0; i < m; i++) {
            checksum += y[i];
        }
        printf(
            "RESULT versao=cols_resized processos=%d m=%d n=%d colunas_por_processo=%d tempo=%.9f checksum=%.6f\n",
            size,
            m,
            n,
            colunas_locais,
            fim - inicio,
            checksum
        );
    }

    free(a);
    free(x);
    free(a_local);
    free(x_local);
    free(y_parcial);
    free(y);
    MPI_Type_free(&tipo_colunas_redimensionado);
    MPI_Type_free(&tipo_colunas);
    MPI_Finalize();
    return 0;
}
