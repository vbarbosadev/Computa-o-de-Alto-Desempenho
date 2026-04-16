/*
 * Tarefa 9 - Parte 1: regioes criticas nomeadas em 2 listas encadeadas
 *
 * N threads realizam insercoes em duas listas encadeadas (lista_a e lista_b).
 * Cada thread escolhe aleatoriamente em qual lista inserir usando rand_r().
 *
 * Protecao com critical NOMEADO:
 *   #pragma omp critical(lista_a)  ->  so bloqueia quem tambem quer inserir em lista_a
 *   #pragma omp critical(lista_b)  ->  so bloqueia quem tambem quer inserir em lista_b
 *
 * Consequencia: insercoes nas duas listas ocorrem em paralelo — uma thread
 * inserindo em lista_a nao bloqueia outra thread que quer inserir em lista_b.
 * Isso e impossivel de generalizar para K listas dinamicas porque os nomes de
 * critical precisam ser literais conhecidos em tempo de compilacao.
 *
 * Compilar: gcc -O2 -fopenmp -o lists_critical lists_critical.c
 * Executar: ./lists_critical [N]
 */

#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define DEFAULT_N 1000000L

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
    if (argc > 1) {
        N = atol(argv[1]);
        if (N <= 0) { fprintf(stderr, "Uso: %s [N > 0]\n", argv[0]); return 1; }
    }

    struct List lista_a = {NULL, 0};
    struct List lista_b = {NULL, 0};
    int threads_used    = 0;

    double t0 = omp_get_wtime();

    #pragma omp parallel
    {
        /* seed privada por thread */
        unsigned int seed = (unsigned int)(time(NULL))
                          ^ (unsigned int)(omp_get_thread_num() * 2654435761u);

        #pragma omp single
        threads_used = omp_get_num_threads();

        #pragma omp for schedule(static)
        for (long i = 0; i < N; i++) {
            int value  = (int)(rand_r(&seed) % 1000000);
            int choice = (int)(rand_r(&seed) % 2);

            if (choice == 0) {
                /*
                 * critical NOMEADO: bloqueia apenas quem tambem quer
                 * acessar lista_a — quem quer acessar lista_b continua livre.
                 */
                #pragma omp critical(lista_a)
                list_insert(&lista_a, value);
            } else {
                #pragma omp critical(lista_b)
                list_insert(&lista_b, value);
            }
        }
    }

    double elapsed = omp_get_wtime() - t0;
    long total     = lista_a.count + lista_b.count;

    printf("CONFIG program=critical n=%ld lists=2 threads=%d\n",
           N, threads_used);
    printf("SUMMARY total=%ld list_counts=%ld,%ld elapsed=%.6f\n",
           total, lista_a.count, lista_b.count, elapsed);

    list_free(&lista_a);
    list_free(&lista_b);
    return 0;
}
