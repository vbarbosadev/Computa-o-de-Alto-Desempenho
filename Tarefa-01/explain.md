# Multiplicação de Matrizes e Localidade de Memória

## 1. Por que o algoritmo de multiplicação por linhas é mais lento?

**Atenção:** Na verdade, ocorre quase sempre o exato **oposto** em linguagens como C e C++. A multiplicação por **linhas** (onde o laço mais externo ou o caminhar da memória favorece as linhas) costuma ser **muito mais rápida**, enquanto avançar por **colunas** costuma ser **mais lento**. 

Se você observar os comentários que existem nos códigos do seu projeto:
- Em `mult_por_linha.c`: *"Favorece a localidade de cache, visto que C armazena as coisas Row-Major."*
- Em `mult_por_coluna.c`: *"Desfavorece a localidade de cache, saltando endereços de memória distantes."*

Caso você tenha rodado o código localmente e a versão por linhas demorou mais, isso foi provavelmente uma anomalia isolada (interferência do Sistema Operacional, configurações de otimização pesada do compilador que inverteram as ordens sozinhas, ou flutuações da CPU). O comportamento normal e esperado pela arquitetura é que **iterar pelas linhas seja sempre o mais veloz**.

Para entender o porquê, temos que compreender como os processadores lidam com dados usando a **Localidade Espacial** e a **Localidade Temporal**.

---

## 2. O que é Localidade Espacial e Temporal?

Os processadores modernos são extremamente rápidos, enquanto a Memória Principal (RAM) é comparativamente muito lenta. Para resolver esse estrangulamento de velocidade, foram criadas as memórias submersas no processador chamadas **Caches (L1, L2, L3)** — minúsculas, porém rapidíssimas. 

Sempre que a CPU precisa de um valor, ela primeiro checa o cache. Para que o cache tenha uma alta taxa de acertos (Cache Hits), tenta-se prever o comportamento humano utilizando os seguintes princípios:

### Localidade Espacial (Espaço e Vizinhança)
É a forte tendência geométrica do seu programa em acessar endereços de memória que estão **fisicamente muito próximos** aos recém-acessados. 
- A prova disso nos hardwares é que toda vez que você pede à RAM para ler um Byte, a CPU **nunca busca apenas aquele único Byte**. Ela busca um bloco inteiro de dezenas de Bytes (chamado de *Cache Line*, geralmente de 64 bytes). 
- Se a próxima variável que o seu código precisar estiver "espacialmente vizinha" da primeira, a leitura subsequente será **instantânea**, pois a vizinha "pegou carona" para o Cache durante a busca do primeiro dado.

### Localidade Temporal (Tempo e Repetição)
É a forte tendência do seu programa em **reutilizar as mesmas variáveis e endereços de memória** em um intervalo curtíssimo de tempo.
- Se você lê ou manipula uma variável agora (dentro de um `while` ou `for`), é altissimamente provável que precise consultá-la novamente nas rodadas seguintes. 
- O Cache evita destruir os dados mais recentes justamente por apostar na Localidade Temporal.

---

## 3. O Problema da Matriz: Row-Major Order

Na linguagem C, as matrizes bidimensionais não são fisicamente bidimensionais. Por baixo dos panos, uma matriz gigante é apenas um longo "barbante" esticado de itens na memória contígua. Mas como eles são guardados num barbante linear? Na organização **Row-Major** (orientada por linha).
- Isso significa que `A[0][0]` está grudado organicamente ao lado de `A[0][1]`. A vizinhança na memória física reflete a mesma estrutura lógica da linha (**Perfeita Localidade Espacial**).
- No entanto, o `A[0][0]` está separadíssimo de `A[1][0]`. Para ler os dados da mesma coluna, você precisa dar saltos de arranques de N posições por toda a memória (no seu caso, `N=1500`, saltos de quase 12.000 bytes!). Ninguém pega "carona" nesses pulos (**Péssima Localidade Espacial**).

### Aplicando no Seu Algoritmo (C = A * B)

No laço principal do cerne do seu processamento computacional:
`C[i][j] += A[i][k] * B[k][j];`

#### 1. Por Linha (`mult_por_linha.c`):
- O algoritmo é desenhado variando-se o `j` enquanto mantém o `i` constante. 
- Ao escrever na matriz limite `C[i][j]`, a CPU caminha elegantemente, de celazinha a celazinha vizinha, enchendo os blocos do próprio *cache line*.
- Na mesma pegada, a CPU repete dezenas de vezes a mesma leitura sobre as vizinhanças horizontais da primeira matriz e reaproveita dados temporais já trazidos ao cache. Tudo isso se encaixa de forma simbiótica com as otimizações L1, gerando altíssimo retorno e velocidade.

#### 2. Por Coluna (`mult_por_coluna.c`):
- O algoritmo ignora tudo isso: ele prefere manter a coluna `j` inteiramente fixa enquanto muda a linha `i`. 
- Ao gravar valores, escreve em `C[0][0]`, depois toma um salto gigante para escrever em `C[1][0]`, e assim por diante. Cada salto exige buscar posições completamente não-associadas na dolorosa RAM.
- Na leitura, ele tenta trazer blocos colossais não coligados, que frequentemente não cabem integralmente no L1 cache para reaproveitamento limpo. Essas constantes lutas com as amarras físicas originam atrasos microscópicos que, multiplicados por milhões no cerne do Loop, culminam numa diferença colossal até terminar os repasses de dados de tempo da máquina.
