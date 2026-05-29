/*
 * mpi_subgrupos_derivada_integral.c
 *
 * Atividade: MPI Subgrupos
 * - Metade dos processos calcula a derivada de uma função usando diferenças finitas.
 * - A outra metade calcula a integral da mesma função usando o método do trapézio.
 *
 * Função usada como exemplo:
 *   f(x) = x^2 + 3x + 2
 *
 * Derivada aproximada:
 *   f'(x) ≈ (f(x + h) - f(x - h)) / (2h)
 *
 * Integral aproximada:
 *   ∫[a,b] f(x) dx pelo método do trapézio composto.
 *
 * Compilação:
 *   mpicc mpi_subgrupos_der_int.c -o mpi_subgrupos_derivada_integral -lm
 *
 * Execução:
 *   mpirun -np 4 ./mpi_subgrupos_derivada_integral
 */

#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define GRUPO_DERIVADA 0
#define GRUPO_INTEGRAL 1

/* Função que será usada nos dois cálculos. Altere aqui se quiser outro exemplo. */
double f(double x) {
    return x * x + 3.0 * x + 2.0;
}

/* Diferença finita central para aproximar a derivada em um ponto x. */
double calcular_derivada_diferencas_finitas(double x, double h) {
    return (f(x + h) - f(x - h)) / (2.0 * h);
}

/*
 * Cada processo do subgrupo da derivada calcula uma parte dos pontos.
 * Exemplo: se existem 10 pontos e 2 processos, cada processo pega alguns índices.
 */
void executar_calculo_derivada(MPI_Comm subcomunicador) {
    int sub_rank, sub_size;
    MPI_Comm_rank(subcomunicador, &sub_rank);
    MPI_Comm_size(subcomunicador, &sub_size);

    const int total_pontos = 10;
    const double inicio = 0.0;
    const double fim = 9.0;
    const double h = 1e-5;

    double soma_local = 0.0;
    int quantidade_local = 0;

    if (sub_rank == 0) {
        printf("Calculando derivada usando diferenças finitas centrais...\n");
        for (int i = 0; i < total_pontos; i++) {
            double x = inicio + i * ((fim - inicio) / (total_pontos - 1));
            double derivada = calcular_derivada_diferencas_finitas(x, h);

            printf("[DERIVADA] Processo local %d calculou f'(%.2f) ≈ %.6f\n",
                   sub_rank, x, derivada);

            soma_local += derivada;
            quantidade_local++;
            }
        }

        else {
            for (int i = sub_rank; i < total_pontos; i += sub_size) {
                double x = inicio + i * ((fim - inicio) / (total_pontos - 1));
                double derivada = calcular_derivada_diferencas_finitas(x, h);

                printf("[DERIVADA] Processo local %d calculou f'(%.2f) ≈ %.6f\n",
                       sub_rank, x, derivada);

                soma_local += derivada;
                quantidade_local++;
            }
        }
    

    double soma_global = 0.0;
    int quantidade_global = 0;

    MPI_Reduce(&soma_local, &soma_global, 1, MPI_DOUBLE, MPI_SUM, 0, subcomunicador);
    MPI_Reduce(&quantidade_local, &quantidade_global, 1, MPI_INT, MPI_SUM, 0, subcomunicador);

    if (sub_rank == 0) {
        printf("\n[DERIVADA] Média das derivadas aproximadas = %.6f\n\n",
               soma_global / quantidade_global);
    }
}

/*
 * Método do trapézio composto em paralelo.
 * Cada processo calcula uma faixa de trapézios e depois as áreas são somadas.
 */
void executar_calculo_integral(MPI_Comm subcomunicador) {
    int sub_rank, sub_size;
    MPI_Comm_rank(subcomunicador, &sub_rank);
    MPI_Comm_size(subcomunicador, &sub_size);

    const double a = 0.0;
    const double b = 10.0;
    const int n = 100000; /* quantidade de trapézios */
    const double largura = (b - a) / n;

    double area_local = 0.0;

    for (int i = sub_rank; i < n; i += sub_size) {
        double x_i = a + i * largura;
        double x_proximo = x_i + largura;

        area_local += ((f(x_i) + f(x_proximo)) / 2.0) * largura;
    }

    double area_total = 0.0;
    MPI_Reduce(&area_local, &area_total, 1, MPI_DOUBLE, MPI_SUM, 0, subcomunicador);

    printf("[INTEGRAL] Processo local %d calculou área parcial = %.6f\n",
           sub_rank, area_local);

    if (sub_rank == 0) {
        printf("\n[INTEGRAL] Integral aproximada de f(x) em [%.2f, %.2f] = %.6f\n\n",
               a, b, area_total);
    }
}

int main(int argc, char *argv[]) {
    MPI_Init(&argc, &argv);

    int rank_global, size_global;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank_global);
    MPI_Comm_size(MPI_COMM_WORLD, &size_global);

    if (size_global < 2) {
        if (rank_global == 0) {
            printf("Erro: execute com pelo menos 2 processos.\n");
            printf("Exemplo: mpirun -np 4 ./mpi_subgrupos_derivada_integral\n");
        }
        MPI_Finalize();
        return EXIT_FAILURE;
    }

    /*
     * Divide os processos em dois subgrupos:
     * - Primeira metade: derivada
     * - Segunda metade: integral
     */
    int metade = size_global / 2;
    int cor_grupo;

    if (rank_global < metade) {
        cor_grupo = GRUPO_DERIVADA;
    } else {
        cor_grupo = GRUPO_INTEGRAL;
    }

    MPI_Comm subcomunicador;
    MPI_Comm_split(MPI_COMM_WORLD, cor_grupo, rank_global, &subcomunicador);

    if (rank_global == 0) {
        printf("Programa MPI com subgrupos\n");
        printf("Total de processos: %d\n", size_global);
        printf("Processos no grupo da derivada: %d\n", metade);
        printf("Processos no grupo da integral: %d\n\n", size_global - metade);
    }

    MPI_Barrier(MPI_COMM_WORLD);

    if (cor_grupo == GRUPO_DERIVADA) {
        executar_calculo_derivada(subcomunicador);
    } else {
        executar_calculo_integral(subcomunicador);
    }

    MPI_Comm_free(&subcomunicador);
    MPI_Finalize();

    return EXIT_SUCCESS;
}
