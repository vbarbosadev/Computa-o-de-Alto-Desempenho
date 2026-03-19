# Tarefa 2 — Dependências entre instruções e o efeito da otimização do compilador

## Objetivo

Observar como a **dependência entre uma iteração e a próxima** afeta o tempo de execução de um laço, e entender o que acontece quando o compilador é autorizado a otimizar o código.

---

## O que foi implementado

Três laços operando sobre um vetor de 100 milhões de números inteiros:

**Laço 1** — apenas inicializa o vetor (não foi medido, serve só de preparação):
```c
for (int i = 0; i < N; i++)
    A[i] = i + 2;
```

**Laço 2** — soma todos os elementos em uma única variável:
```c
long long soma = 0;
for (int i = 0; i < N; i++)
    soma += A[i];
```

**Laço 3** — soma os elementos em múltiplas variáveis independentes:
```c
// exemplo com 4 variáveis
long long soma1 = 0, soma2 = 0, soma3 = 0, soma4 = 0;
for (int i = 0; i < N; i += 4) {
    soma1 += A[i];
    soma2 += A[i + 1];
    soma3 += A[i + 2];
    soma4 += A[i + 3];
}
```

Variantes do laço 3 foram testadas com **2, 4, 8, 12 e 16 variáveis** acumuladoras.

Cada versão foi compilada de três formas: **sem otimização (-O0)**, com **otimização moderada (-O2)** e com **otimização máxima (-O3)**.

---

## Resultados

| Laço | Variáveis | -O0 (s) | -O2 (s) | -O3 (s) |
| --- | --- | --- | --- | --- |
| laco2 | 1 | **0.1764** | 0.0225 | 0.0256 |
| laco3_2 | 2 | 0.0863 | 0.0278 | 0.0272 |
| laco3_4 | 4 | 0.0514 | 0.0274 | 0.0279 |
| laco3_8 | 8 | 0.0504 | **0.0223** | 0.0277 |
| laco3_12 | 12 | **0.0455** | 0.0276 | 0.0277 |
| laco3_16 | 16 | 0.0527 | 0.0242 | **0.0259** |

---

## Análise

### Sem otimização (-O0): por que uma variável é mais lenta

No laço 2, cada soma depende do resultado da soma anterior: para calcular `soma` na iteração 5, o processador precisa que a iteração 4 já tenha terminado. Não tem como fazer as duas ao mesmo tempo — é uma fila de espera obrigatória.

O processador moderno consegue executar várias operações ao mesmo tempo quando elas são independentes, como uma linha de montagem. Mas quando há uma dependência — uma operação que obrigatoriamente precisa esperar a anterior terminar — essa linha de montagem trava. Com 100 milhões de iterações esperando uma pela outra, o tempo acumula: **0.1764s**.

O laço 3 resolve isso dividindo o trabalho em múltiplas variáveis que não dependem umas das outras. `soma1` e `soma2` podem ser calculadas ao mesmo tempo, pois nunca interferem entre si. O resultado:

| Variáveis | Tempo -O0 (s) | Quantas vezes mais rápido que laco2 |
| --- | --- | --- |
| 1 (laco2) | 0.1764 | referência |
| 2 | 0.0863 | 2.0× |
| 4 | 0.0514 | 3.4× |
| 8 | 0.0504 | 3.5× |
| 12 | 0.0455 | 3.9× |
| 16 | 0.0527 | 3.3× |

O ganho cresce até 12 variáveis e depois começa a regredir. Isso acontece porque o processador tem uma quantidade limitada de "espaço de trabalho" interno para guardar variáveis ativas ao mesmo tempo. Com 16 variáveis simultâneas sem otimização, esse espaço esgota e o programa começa a usar a memória RAM como rascunho extra, o que é mais lento.

### Com otimização (-O2 e -O3): o compilador faz o trabalho

Com otimização ativada, todos os laços ficam com tempos parecidos (~0.022–0.028s). Isso acontece porque o compilador é inteligente o suficiente para identificar que o laço 2 é uma simples soma de todos os elementos, e transforma o código automaticamente para executar várias somas ao mesmo tempo — exatamente o que o laço 3 fazia manualmente.

O resultado mais expressivo é o do próprio laço 2: sem otimização ele levava 0.1764s, com otimização passou para 0.0225s — **8 vezes mais rápido**, sem mudar uma linha do código-fonte.

Os laços 3 também melhoram com otimização, mas menos (em torno de 3×), porque já estavam mais próximos do ideal. O compilador tinha menos margem de melhoria em código com mais variáveis e estrutura mais complexa.

### Resumo dos ganhos

| O que comparamos | Resultado |
| --- | --- |
| laco2 sem vs. com otimização | **8× mais rápido** — compilador resolve a dependência |
| laco2 vs. laco3_2 sem otimização | **2× mais rápido** — divisão básica do trabalho |
| laco2 vs. laco3_12 sem otimização | **3.9× mais rápido** — melhor resultado manual |
| laco2 vs. laco3_12 com otimização | **igual** — compilador chega no mesmo lugar |

---

## Conclusão

Quando não há otimização, dependências entre iterações criam gargalos reais e visíveis — o mesmo laço rodando quase 4× mais lento só por usar uma variável em vez de várias. No entanto, com otimização ativada, o compilador identifica esse padrão e resolve sozinho, igualando o desempenho de todos os laços.

Isso mostra que **compilar com otimização** é sempre o primeiro passo, e que mudanças manuais no código só fazem sentido quando há evidência de que o compilador não conseguiu otimizar por conta própria.
