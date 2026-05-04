/*
 * Compatibilidade para ambientes onde rand_r() nao esta disponivel
 * (como algumas distribuicoes MinGW no Windows).
 */

#ifndef TAREFA10_PORTABLE_RAND_R_H
#define TAREFA10_PORTABLE_RAND_R_H

#if defined(_WIN32)
static unsigned int portable_rand_r(unsigned int *seed) {
    *seed = (*seed * 1103515245u) + 12345u;
    return (*seed / 65536u) % 32768u;
}

#define rand_r portable_rand_r
#endif

#endif
