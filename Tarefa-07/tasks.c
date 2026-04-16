#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define DEFAULT_TOTAL_NODES 11

struct Node {
    int index;
    char file[30];
    struct Node *proximo;
};

static struct Node *criar_no(int index) {
    struct Node *novo_no = (struct Node *)malloc(sizeof(struct Node));
    if (novo_no == NULL) {
        fprintf(stderr, "Erro: falha ao alocar o no %d\n", index);
        exit(1);
    }

    novo_no->index = index;
    snprintf(novo_no->file, sizeof(novo_no->file), "file%d.txt", index);
    novo_no->proximo = NULL;
    return novo_no;
}

static struct Node *criar_lista(int total_nos) {
    struct Node *head = criar_no(0);
    struct Node *tail = head;

    for (int i = 1; i < total_nos; i++) {
        struct Node *novo_no = criar_no(i);
        tail->proximo = novo_no;
        tail = tail->proximo;
    }

    return head;
}

static void liberar_lista(struct Node *head) {
    struct Node *atual = head;
    while (atual != NULL) {
        struct Node *temp = atual;
        atual = atual->proximo;
        free(temp);
    }
}

int main(int argc, char *argv[]) {
    int total_nos = DEFAULT_TOTAL_NODES;
    if (argc > 1) {
        total_nos = atoi(argv[1]);
        if (total_nos <= 0) {
            fprintf(stderr, "Uso: %s [total_nos > 0]\n", argv[0]);
            return 1;
        }
    }

    struct Node *head = criar_lista(total_nos);

    printf("CONFIG total_nodes=%d requested_threads=%d\n",
           total_nos, omp_get_max_threads());

    double start = omp_get_wtime();

    #pragma omp parallel
    {
        #pragma omp single
        {
            struct Node *atual = head;
            while (atual != NULL) {
                struct Node *node = atual;

                #pragma omp task firstprivate(node)
                {
                    #pragma omp critical(output)
                    printf("PROCESS node=%d file=%s thread=%d\n",
                           node->index, node->file, omp_get_thread_num());
                }

                atual = atual->proximo;
            }

            #pragma omp taskwait
        }
    }

    printf("SUMMARY total_nodes=%d elapsed_seconds=%.6f\n",
           total_nos, omp_get_wtime() - start);

    liberar_lista(head);
    return 0;
}
