/*
 * Tarefa 9 - Parte 2: K listas encadeadas com omp_lock_t (travas explicitas)
 *
 * Generaliza o problema para K listas (K passado pelo usuario).
 * Cada lista tem seu proprio lock: omp_lock_t locks[K].
 *
 * Por que critical nomeado NAO funciona aqui:
 *   - Os nomes de #pragma omp critical devem ser identificadores literais
 *     escritos no codigo-fonte e conhecidos em tempo de compilacao.
 *   - Nao e possivel criar "critical(lista_0)", "critical(lista_1)", ...
 *     de forma dinamica em funcao do valor de K fornecido em tempo de execucao.
 *   - Mesmo que K fosse fixo, seria necessario escrever K blocos critical
 *     distintos no codigo — impraticavel para valores grandes de K.
 *
 * Solucao com travas explicitas:
 *   omp_init_lock(&locks[k])    ->  inicializa o lock da lista k
 *   omp_set_lock(&locks[k])     ->  adquire o lock antes de inserir
 *   omp_unset_lock(&locks[k])   ->  libera o lock apos inserir
 *   omp_destroy_lock(&locks[k]) ->  destroi o lock ao final
 *
 * Vantagem sobre critical anonimo:
 *   Um unico critical anonimo serializaria TODAS as insercoes, independente
 *   da lista escolhida. Com locks individuais, a insercao na lista k so
 *   bloqueia outra thread que tambem quer inserir na lista k — exatamente
 *   o mesmo comportamento do critical nomeado da Parte 1, mas para K arbitrario.
 *
 * Compilar: gcc -O2 -fopenmp -o lists_lock lists_lock.c
 * Executar: ./lists_lock [N] [K]
 */

#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define DEFAULT_N  1000000L
#define DEFAULT_K  2
#define MAX_LISTS  1024

/* ------------------------------------------------------------------ */
/* Estruturas                                                           */
/* ------------------------------------------------------------------ */

struct Node {
    int           value;
    struct Node  *next;
};

struct List {
    struct Node *head;
    long         count;
};

static void list_insert(struct List *list, int value) {
    struct Node *node = (struct Node *)malloc(sizeof(struct Node));
    if (!node) { fprintf(stderr, "malloc falhou\n"); exit(1); }
    node->value = value;
    node->next  = list->head;
    list->head  = node;
    list->count++;
}

static void list_free(struct List *list) {
    struct Node *cur = list->head;
    while (cur) {
        struct Node *tmp = cur;
        cur = cur->next;
        free(tmp);
    }
    list->head  = NULL;
    list->count = 0;
}

/* ------------------------------------------------------------------ */
/* main                                                                 */
/* ------------------------------------------------------------------ */

int main(int argc, char *argv[]) {
    long N = DEFAULT_N;
    int  K = DEFAULT_K;

    if (argc > 1) {
        N = atol(argv[1]);
        if (N <= 0) { fprintf(stderr, "Uso: %s [N > 0] [K > 0]\n", argv[0]); return 1; }
    }
    if (argc > 2) {
        K = atoi(argv[2]);
        if (K <= 0 || K > MAX_LISTS) {
            fprintf(stderr, "K deve ser entre 1 e %d\n", MAX_LISTS);
            return 1;
        }
    }

    /* aloca K listas e K locks */
    struct List *lists = (struct List *)calloc(K, sizeof(struct List));
    omp_lock_t  *locks = (omp_lock_t  *)malloc(K * sizeof(omp_lock_t));
    if (!lists || !locks) { fprintf(stderr, "malloc falhou\n"); return 1; }

    for (int k = 0; k < K; k++)
        omp_init_lock(&locks[k]);

    int threads_used = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        unsigned int seed = (unsigned int)(time(NULL))
                          ^ (unsigned int)(omp_get_thread_num() * 2654435761u);

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            int value = (int)(rand_r(&seed) % 1000000);
            int k     = (int)(rand_r(&seed) % K);

            /*
             * Cada lista tem seu proprio lock: inserir na lista k
             * bloqueia apenas quem tambem quer inserir na lista k.
             * Insercoes em listas diferentes ocorrem em paralelo.
             */
            omp_set_lock(&locks[k]);
            list_insert(&lists[k], value);
            omp_unset_lock(&locks[k]);
        }
    }

    double elapsed = omp_get_wtime() - t0;

    /* calcula total e monta string de contagens */
    long total = 0;
    for (int k = 0; k < K; k++) total += lists[k].count;

    /* imprime contagens separadas por virgula */
    char counts_buf[MAX_LISTS * 16];
    int  pos = 0;
    for (int k = 0; k < K; k++) {
        pos += snprintf(counts_buf + pos, sizeof(counts_buf) - pos,
                        "%s%ld", k ? "," : "", lists[k].count);
    }

    printf("CONFIG program=lock n=%ld lists=%d threads=%d\n",
           N, K, threads_used);
    printf("SUMMARY total=%ld list_counts=%s elapsed=%.6f\n",
           total, counts_buf, elapsed);

    /* libera recursos */
    for (int k = 0; k < K; k++) {
        omp_destroy_lock(&locks[k]);
        list_free(&lists[k]);
    }
    free(lists);
    free(locks);
    return 0;
}
