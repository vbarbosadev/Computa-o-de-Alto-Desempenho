/*
 * Tarefa 6 - Estimativa estocastica de PI com clausulas OpenMP
 *
 * Reestruturado com #pragma omp parallel + #pragma omp for, aplicando
 * as clausulas: private, firstprivate, lastprivate, shared e default(none).
 *
 * Argumento de linha de comando seleciona o teste:
 *   ./pi_clauses <teste> [N]
 *   teste: 1 = shared+private, 2 = firstprivate, 3 = lastprivate, 4 = default_none
 *
 * Compilar: gcc -O2 -fopenmp -o pi_clauses pi_clauses.c -lm
 */

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include <omp.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/*
 * TESTE 1: shared + private
 *
 * shared(count): todas as threads compartilham a mesma variavel count.
 * private(x, y, seed, local_count): cada thread tem sua propria copia
 *   dessas variaveis. Variaveis private NAO sao inicializadas (comecam
 *   com valor indefinido), por isso precisamos fazer local_count = 0
 *   manualmente dentro do bloco paralelo.
 *
 * Usamos local_count (private) para acumular localmente e depois somamos
 * ao count compartilhado dentro de uma regiao critica, reduzindo o overhead.
 */
void teste_shared_private(int N) {
    int count = 0;
    double x, y;
    unsigned int seed;
    int local_count;
    int threads_used;

    double t0 = omp_get_wtime();

    #pragma omp parallel default(none) shared(count, threads_used, N) private(x, y, seed, local_count)
    {
        seed = time(NULL) ^ omp_get_thread_num();
        local_count = 0;  /* Necessario! private nao inicializa */

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for
        for (int i = 0; i < N; i++) {
            x = (double)rand_r(&seed) / RAND_MAX;
            y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
        }

        #pragma omp critical
        {
            count += local_count;
        }
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=shared_private n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);
}

/*
 * TESTE 2: firstprivate
 *
 * firstprivate(local_count): cada thread recebe uma copia INICIALIZADA
 * com o valor que a variavel tinha antes da regiao paralela.
 * Como local_count = 0 antes do parallel, cada thread comeca com 0
 * automaticamente, sem precisar inicializar manualmente.
 *
 * Diferenca de private: com private, local_count comecaria com lixo.
 */
void teste_firstprivate(int N) {
    int count = 0;
    int local_count = 0;  /* valor copiado para cada thread via firstprivate */
    double x, y;
    unsigned int seed;
    int threads_used;

    double t0 = omp_get_wtime();

    #pragma omp parallel default(none) shared(count, threads_used, N) firstprivate(local_count) private(x, y, seed)
    {
        seed = time(NULL) ^ omp_get_thread_num();

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for
        for (int i = 0; i < N; i++) {
            x = (double)rand_r(&seed) / RAND_MAX;
            y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
        }

        #pragma omp critical
        {
            count += local_count;
        }
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=firstprivate n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);
}

/*
 * TESTE 3: lastprivate
 *
 * lastprivate(last_i): apos o termino do loop, a variavel last_i recebe
 * o valor correspondente a ULTIMA iteracao (na ordem sequencial, i = N-1).
 *
 * Util quando precisamos saber o estado de uma variavel ao final do loop,
 * como se ele tivesse sido executado sequencialmente.
 */
void teste_lastprivate(int N) {
    int count = 0;
    int local_count;
    int last_i = -1;
    double x, y;
    unsigned int seed;
    int threads_used;

    double t0 = omp_get_wtime();

    #pragma omp parallel default(none) shared(count, threads_used, N, last_i) private(x, y, seed, local_count)
    {
        seed = time(NULL) ^ omp_get_thread_num();
        local_count = 0;

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for lastprivate(last_i)
        for (int i = 0; i < N; i++) {
            x = (double)rand_r(&seed) / RAND_MAX;
            y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
            last_i = i;
        }

        #pragma omp critical
        {
            count += local_count;
        }
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=lastprivate n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f last_i=%d\n",
           pi, count, N, error, elapsed, last_i);
}

/*
 * TESTE 4: default(none) — forcando escopo explicito
 *
 * Com default(none), TODA variavel usada dentro da regiao paralela deve
 * ter seu escopo declarado explicitamente. Caso contrario, o compilador
 * emite um erro.
 *
 * Vantagem: evita erros silenciosos onde uma variavel e acidentalmente
 * compartilhada (causando race conditions) ou acidentalmente privada
 * (causando uso de valor indefinido). Em programas complexos, isso torna
 * o codigo mais seguro e mais claro.
 */
void teste_default_none(int N) {
    int count = 0;
    int local_count = 0;
    double x, y;
    unsigned int seed;
    int threads_used;

    double t0 = omp_get_wtime();

    #pragma omp parallel default(none) \
        shared(count, threads_used, N) \
        firstprivate(local_count) \
        private(x, y, seed)
    {
        seed = time(NULL) ^ omp_get_thread_num();

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for
        for (int i = 0; i < N; i++) {
            x = (double)rand_r(&seed) / RAND_MAX;
            y = (double)rand_r(&seed) / RAND_MAX;
            if (x * x + y * y <= 1.0)
                local_count++;
        }

        #pragma omp critical
        {
            count += local_count;
        }
    }

    double t1 = omp_get_wtime();
    double elapsed = t1 - t0;
    double pi = 4.0 * count / N;
    double error = fabs(pi - M_PI);

    printf("CONFIG program=default_none n=%d threads=%d\n", N, threads_used);
    printf("RESULT pi=%.10f count=%d total=%d error=%.10f elapsed=%.6f\n",
           pi, count, N, error, elapsed);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <teste> [N]\n", argv[0]);
        fprintf(stderr, "  teste: 1=shared+private 2=firstprivate 3=lastprivate 4=default_none\n");
        return 1;
    }

    int teste = atoi(argv[1]);
    int N = 10000000;
    if (argc > 2) N = atoi(argv[2]);

    switch (teste) {
        case 1: teste_shared_private(N); break;
        case 2: teste_firstprivate(N); break;
        case 3: teste_lastprivate(N); break;
        case 4: teste_default_none(N); break;
        default:
            fprintf(stderr, "Teste invalido: %d (use 1-4)\n", teste);
            return 1;
    }

    return 0;
}
