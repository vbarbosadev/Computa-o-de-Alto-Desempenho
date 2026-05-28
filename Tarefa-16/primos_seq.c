#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>

static int ler_inteiro(int argc, char **argv, const char *opcao, int padrao)
{
    for (int i = 1; i + 1 < argc; i++) {
        if (strcmp(argv[i], opcao) == 0) {
            return atoi(argv[i + 1]);
        }
    }
    return padrao;
}

static double tempo_agora(void)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return (double)tv.tv_sec + (double)tv.tv_usec * 0.000001;
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

int main(int argc, char **argv)
{
    int maximo = ler_inteiro(argc, argv, "--max", 1000000);
    int total = 0;

    double inicio = tempo_agora();
    for (int n = 2; n <= maximo; n++) {
        total += eh_primo(n);
    }
    double fim = tempo_agora();

    printf(
        "RESULT versao=seq max=%d primos=%d tempo=%.9f\n",
        maximo,
        total,
        fim - inicio
    );

    return 0;
}
