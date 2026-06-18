# Tarefa 21 - Otimizacao de transferencia GPU/CPU no heat

## Objetivo

Fazer o exercicio de transferencia de calor do slide 102 do tutorial de GPU com
OpenMP, reduzindo a movimentacao de dados entre CPU e GPU para evitar que as copias
dominem a execucao.

## Referencia usada

A versao otimizada foi alinhada com `heat_target_map_opt.c` do repositorio
`UoB-HPC/openmp-tutorial`: os arrays entram no ambiente de dados do dispositivo com
`target enter data map(to: u[0:n*n], u_tmp[0:n*n])`, os kernels usam `target` sem
remapear os arrays a cada passo, e ao final apenas o array da solucao volta com
`target exit data map(from: u[0:n*n])`.

## Implementacao preparada

A pasta `Tarefa-21/` foi criada com tres versoes comparaveis:

- `heat_cpu.c`: referencia CPU.
- `heat_target_baseline.c`: baseline GPU equivalente a Tarefa 20, com `map(tofrom)`
  na regiao de calculo.
- `heat_target_resident.c`: versao otimizada, com `target enter data` antes dos
  passos de tempo e `target exit data` ao final, mantendo `u` e `u_tmp` residentes
  no dispositivo durante a simulacao.

A versao otimizada transfere `u` e `u_tmp` para o ambiente de dados da GPU uma vez,
roda os passos temporais com os dados residentes e copia de volta apenas o vetor
final. Isso e o ponto central da Tarefa 21: reduzir transferencias repetidas e
deixar a GPU menos ociosa.

## Validacao local

Como nao ha GPU/NVHPC/`nsys` no ambiente local, a validacao feita foi apenas de
sintaxe e fallback host:

```bash
python3 -m py_compile Tarefa-21/comparar_resultados.py
bash -n Tarefa-21/run_npad.sbatch
bash -n Tarefa-21/run_nsys_npad.sbatch
gcc -O2 -fopenmp Tarefa-21/heat_cpu.c -o /tmp/t21_heat_cpu -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_baseline.c -o /tmp/t21_heat_baseline -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_resident.c -o /tmp/t21_heat_resident -lm
/tmp/t21_heat_cpu 100 10
OMP_TARGET_OFFLOAD=DISABLED /tmp/t21_heat_baseline 100 10
OMP_TARGET_OFFLOAD=DISABLED /tmp/t21_heat_resident 100 10
```

As tres execucoes locais retornaram `Error (L2norm): 4.015950E-09` para `N=100` e
`nsteps=10`. Isso confirma consistencia numerica basica no host, mas nao valida o
offload real para GPU.

## Como rodar no NPAD

Da raiz do repositorio:

```bash
sbatch Tarefa-21/run_npad.sbatch
```

Depois que o job terminar:

```bash
cd Tarefa-21
python3 comparar_resultados.py
```

Para perfilar com Nsight Systems:

```bash
sbatch Tarefa-21/run_nsys_npad.sbatch
```

Para comparar baseline e residente no mesmo perfil:

```bash
PROFILE_VARIANT=both N=2000 NSTEPS=20 sbatch Tarefa-21/run_nsys_npad.sbatch
```

## Artefatos esperados apos NPAD

- `Tarefa-21/resultados/heat_resultados_<job_id>.csv`
- `Tarefa-21/resultados/comparacao_heat_resumo.csv`
- `Tarefa-21/resultados/comparacao_heat.md`
- `Tarefa-21/resultados/perfis/nsys_heat_baseline_*.nsys-rep`
- `Tarefa-21/resultados/perfis/nsys_heat_resident_*.nsys-rep`
- resumo textual `Tarefa-21/resultados/nsys-<job_id>.out`

## README operacional


# Tarefa 21 - heat com dados residentes na GPU

Esta pasta prepara a Tarefa 21 para execucao no NPAD, sem incluir resultados
fabricados.

## Arquivos

- `heat_cpu.c`: versao CPU sequencial usada como referencia.
- `heat_target_baseline.c`: versao GPU base da Tarefa 20, com
  `map(tofrom: u[0:n*n], u_tmp[0:n*n])` dentro de `solve()`.
- `heat_target_resident.c`: versao GPU otimizada para a Tarefa 21. Ela usa
`target enter data` antes do laco temporal e `target exit data` depois,
seguindo a estrutura da solucao `heat_target_map_opt.c` do tutorial
`UoB-HPC/openmp-tutorial`, mantendo `u` e `u_tmp` residentes no dispositivo
durante os passos.
- `run_npad.sbatch`: compila com NVHPC e roda CPU, GPU baseline e GPU
  otimizada, gravando CSV em `resultados/`.
- `run_nsys_npad.sbatch`: gera perfil Nsight Systems da versao otimizada e,
  opcionalmente, da baseline.
- `comparar_resultados.py`: le CSVs reais de `resultados/` e gera
  `comparacao_heat_resumo.csv` e `comparacao_heat.md`.

## Ideia da otimizacao

O exercicio pede reduzir movimentacao CPU-GPU. A baseline chama `solve()` a cada
passo, e dentro de `solve()` ha um `target map(tofrom: ...)`, o que pode copiar
os dois arrays em cada iteracao temporal.

Na versao `heat_target_resident.c`, a sequencia e:

```c
#pragma omp target enter data map(to: u[0:n*n], u_tmp[0:n*n])
for (int t = 0; t < nsteps; ++t) {
  solve(...);
  troca_de_ponteiros_no_host;
}
#pragma omp target exit data map(from: u[0:n*n])
```

Assim, `u` e `u_tmp` entram uma vez no ambiente de dados do dispositivo, e apenas
o array que contem a solucao final volta para o host. A troca de ponteiros continua
funcionando porque os valores dos ponteiros sao copiados para cada regiao `target`,
enquanto as associacoes de memoria ja existem no ambiente de dados do dispositivo.

## Submeter no NPAD

Execute a partir da raiz do repositorio:

```bash
sbatch Tarefa-21/run_npad.sbatch
```

A particao padrao no script e `gpu-4-a100`. Para sobrescrever na submissao:

```bash
sbatch --partition=gpu-8-v100 Tarefa-21/run_npad.sbatch
```

Configuracao padrao:

```text
CASES="1000:10 2000:20 4000:40"
REPEATS=3
OMP_TARGET_OFFLOAD=MANDATORY
```

Cada caso usa o formato `N:nsteps`. Para alterar casos ou repeticoes:

```bash
CASES="1000:10 2000:50 4000:100" REPEATS=5 sbatch Tarefa-21/run_npad.sbatch
```

## Saidas geradas

O job cria arquivos em `Tarefa-21/resultados/`:

```text
heat_resultados_<job_id>.csv
tarefa21-<job_id>.out
tarefa21-<job_id>.err
raw_cpu_*.log
raw_gpu_baseline_*.log
raw_gpu_resident_*.log
```

O CSV contem uma linha por variante, tamanho e repeticao. As variantes sao:

```text
cpu
gpu_baseline
gpu_resident
```

## Gerar relatorio

Depois que houver pelo menos um CSV real:

```bash
cd Tarefa-21
python3 comparar_resultados.py
```

Saidas:

```text
resultados/comparacao_heat_resumo.csv
resultados/comparacao_heat.md
```

Tambem e possivel passar CSVs especificos:

```bash
python3 comparar_resultados.py resultados/heat_resultados_<job_id>.csv
```

## Perfil com Nsight Systems

Por padrao, o perfil roda a versao otimizada:

```bash
sbatch Tarefa-21/run_nsys_npad.sbatch
```

Configuracao padrao:

```text
PROFILE_VARIANT=resident
N=2000
NSTEPS=20
```

Para perfilar baseline e otimizada no mesmo job:

```bash
PROFILE_VARIANT=both N=2000 NSTEPS=20 sbatch Tarefa-21/run_nsys_npad.sbatch
```

Perfis gerados:

```text
Tarefa-21/resultados/perfis/nsys_heat_baseline_*.nsys-rep
Tarefa-21/resultados/perfis/nsys_heat_resident_*.nsys-rep
```

No resumo do `nsys`, a expectativa e que a baseline mostre mais atividade de
copia associada aos passos temporais, enquanto a versao residente concentre as
transferencias no inicio e no fim da execucao.

## Validacao local

Localmente, use `gcc` apenas para checar sintaxe e fallback host. Isso nao valida
offload real para GPU:

```bash
mkdir -p Tarefa-21/bin
gcc -O2 -fopenmp Tarefa-21/heat_cpu.c -o Tarefa-21/bin/heat_cpu_gcc -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_baseline.c -o Tarefa-21/bin/heat_gpu_baseline_gcc -lm
gcc -O2 -fopenmp Tarefa-21/heat_target_resident.c -o Tarefa-21/bin/heat_gpu_resident_gcc -lm
Tarefa-21/bin/heat_cpu_gcc 100 10
OMP_TARGET_OFFLOAD=DISABLED Tarefa-21/bin/heat_gpu_baseline_gcc 100 10
OMP_TARGET_OFFLOAD=DISABLED Tarefa-21/bin/heat_gpu_resident_gcc 100 10
```

<!-- codigos-fonte-c-inicio -->
## Codigos fonte C usados nos testes

### `Tarefa-21/heat_cpu.c`

```c

/*
** PROGRAM: heat equation solve
**
** PURPOSE: This program will explore use of an explicit
**          finite difference method to solve the heat
**          equation under a method of manufactured solution (MMS)
**          scheme. The solution has been set to be a simple 
**          function based on exponentials and trig functions.
**
**          A finite difference scheme is used on a 1000x1000 cube.
**          A total of 0.5 units of time are simulated.
**
**          The MMS solution has been adapted from
**          G.W. Recktenwald (2011). Finite difference approximations
**          to the Heat Equation. Portland State University.
**
**
** USAGE:   Run with two arguments:
**          First is the number of cells.
**          Second is the number of timesteps.
**
**          For example, with 100x100 cells and 10 steps:
**
**          ./heat 100 10
**
**
** HISTORY: Written by Tom Deakin, Oct 2018
**
*/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <omp.h>

// Key constants used in this program
#define PI acos(-1.0) // Pi
#define LINE "--------------------\n" // A line for fancy output

// Function definitions
void initial_value(const int n, const double dx, const double length, double * restrict u);
void zero(const int n, double * restrict u);
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp);
double solution(const double t, const double x, const double y, const double alpha, const double length);
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length);

// Main function
int main(int argc, char *argv[]) {

  // Start the total program runtime timer
  double start = omp_get_wtime();

  // Problem size, forms an nxn grid
  int n = 1000;

  // Number of timesteps
  int nsteps = 10;


  // Check for the correct number of arguments
  // Print usage and exits if not correct
  if (argc == 3) {

    // Set problem size from first argument
    n = atoi(argv[1]);
    if (n < 0) {
      fprintf(stderr, "Error: n must be positive\n");
      exit(EXIT_FAILURE);
    }

    // Set number of timesteps from second argument
    nsteps = atoi(argv[2]);
    if (nsteps < 0) {
      fprintf(stderr, "Error: nsteps must be positive\n");
      exit(EXIT_FAILURE);
    }
  }


  //
  // Set problem definition
  //
  double alpha = 0.1;          // heat equation coefficient
  double length = 1000.0;      // physical size of domain: length x length square
  double dx = length / (n+1);  // physical size of each cell (+1 as don't simulate boundaries as they are given)
  double dt = 0.5 / nsteps;    // time interval (total time of 0.5s)


  // Stability requires that dt/(dx^2) <= 0.5,
  double r = alpha * dt / (dx * dx);

  // Print message detailing runtime configuration
  printf("\n");
  printf(" MMS heat equation\n\n");
  printf(LINE);
  printf("Problem input\n\n");
  printf(" Grid size: %d x %d\n", n, n);
  printf(" Cell width: %E\n", dx);
  printf(" Grid length: %lf x %lf\n", length, length);
  printf("\n");
  printf(" Alpha: %E\n", alpha);
  printf("\n");
  printf(" Steps: %d\n", nsteps);
  printf(" Total time: %E\n", dt*(double)nsteps);
  printf(" Time step: %E\n", dt);
  printf(LINE);

  // Stability check
  printf("Stability\n\n");
  printf(" r value: %lf\n", r);
  if (r > 0.5)
    printf(" Warning: unstable\n");
  printf(LINE);


  // Allocate two nxn grids
  double *u     = malloc(sizeof(double)*n*n);
  double *u_tmp = malloc(sizeof(double)*n*n);
  double *tmp;

  // Set the initial value of the grid under the MMS scheme
  initial_value(n, dx, length, u);
  zero(n, u_tmp);

  //
  // Run through timesteps under the explicit scheme
  //

  // Start the solve timer
  double tic = omp_get_wtime();
  for (int t = 0; t < nsteps; ++t) {

    // Call the solve kernel
    // Computes u_tmp at the next timestep
    // given the value of u at the current timestep
    solve(n, alpha, dx, dt, u, u_tmp);

    // Pointer swap
    tmp = u;
    u = u_tmp;
    u_tmp = tmp;
  }
  // Stop solve timer
  double toc = omp_get_wtime();

  //
  // Check the L2-norm of the computed solution
  // against the *known* solution from the MMS scheme
  //
  double norm = l2norm(n, u, nsteps, dt, alpha, dx, length);

  // Stop total timer
  double stop = omp_get_wtime();

  // Print results
  printf("Results\n\n");
  printf("Error (L2norm): %E\n", norm);
  printf("Solve time (s): %lf\n", toc-tic);
  printf("Total time (s): %lf\n", stop-start);
  printf(LINE);

  // Free the memory
  free(u);
  free(u_tmp);

}


// Sets the mesh to an initial value, determined by the MMS scheme
void initial_value(const int n, const double dx, const double length, double * restrict u) {

  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx; // Physical x position
    for (int i = 0; i < n; ++i) {
      u[i+j*n] = sin(PI * x / length) * sin(PI * y / length);
      x += dx;
    }
    y += dx; // Physical y position
  }

}


// Zero the array u
void zero(const int n, double * restrict u) {

  for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {
      u[i+j*n] = 0.0;
    }
  }

}


// Compute the next timestep, given the current timestep
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp) {

  // Finite difference constant multiplier
  const double r = alpha * dt / (dx * dx);
  const double r2 = 1.0 - 4.0*r;

  // Loop over the nxn grid
  for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {

      // Update the 5-point stencil, using boundary conditions on the edges of the domain.
      // Boundaries are zero because the MMS solution is zero there.
      u_tmp[i+j*n] =  r2 * u[i+j*n] +
      r * ((i < n-1) ? u[i+1+j*n] : 0.0) +
      r * ((i > 0)   ? u[i-1+j*n] : 0.0) +
      r * ((j < n-1) ? u[i+(j+1)*n] : 0.0) +
      r * ((j > 0)   ? u[i+(j-1)*n] : 0.0);
    }
  }
}


// True answer given by the manufactured solution
double solution(const double t, const double x, const double y, const double alpha, const double length) {

  return exp(-2.0*alpha*PI*PI*t/(length*length)) * sin(PI*x/length) * sin(PI*y/length);

}


// Computes the L2-norm of the computed grid and the MMS known solution
// The known solution is the same as the boundary function.
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length) {

  // Final (real) time simulated
  double time = dt * (double)nsteps;

  // L2-norm error
  double l2norm = 0.0;

  // Loop over the grid and compute difference of computed and known solutions as an L2-norm
  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx;
    for (int i = 0; i < n; ++i) {
      double answer = solution(time, x, y, alpha, length);
      l2norm += (u[i+j*n] - answer) * (u[i+j*n] - answer);

      x += dx;
    }
    y += dx;
  }

  return sqrt(l2norm);

}
```

### `Tarefa-21/heat_target_baseline.c`

```c

/*
** PROGRAM: heat equation solve
**
** PURPOSE: This program will explore use of an explicit
**          finite difference method to solve the heat
**          equation under a method of manufactured solution (MMS)
**          scheme. The solution has been set to be a simple 
**          function based on exponentials and trig functions.
**
**          A finite difference scheme is used on a 1000x1000 cube.
**          A total of 0.5 units of time are simulated.
**
**          The MMS solution has been adapted from
**          G.W. Recktenwald (2011). Finite difference approximations
**          to the Heat Equation. Portland State University.
**
**
** USAGE:   Run with two arguments:
**          First is the number of cells.
**          Second is the number of timesteps.
**
**          For example, with 100x100 cells and 10 steps:
**
**          ./heat 100 10
**
**
** HISTORY: Written by Tom Deakin, Oct 2018
**
*/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <omp.h>

// Key constants used in this program
#define PI acos(-1.0) // Pi
#define LINE "--------------------\n" // A line for fancy output

// Function definitions
void initial_value(const int n, const double dx, const double length, double * restrict u);
void zero(const int n, double * restrict u);
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp);
double solution(const double t, const double x, const double y, const double alpha, const double length);
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length);

// Main function
int main(int argc, char *argv[]) {

  // Start the total program runtime timer
  double start = omp_get_wtime();

  // Problem size, forms an nxn grid
  int n = 1000;

  // Number of timesteps
  int nsteps = 10;


  // Check for the correct number of arguments
  // Print usage and exits if not correct
  if (argc == 3) {

    // Set problem size from first argument
    n = atoi(argv[1]);
    if (n < 0) {
      fprintf(stderr, "Error: n must be positive\n");
      exit(EXIT_FAILURE);
    }

    // Set number of timesteps from second argument
    nsteps = atoi(argv[2]);
    if (nsteps < 0) {
      fprintf(stderr, "Error: nsteps must be positive\n");
      exit(EXIT_FAILURE);
    }
  }


  //
  // Set problem definition
  //
  double alpha = 0.1;          // heat equation coefficient
  double length = 1000.0;      // physical size of domain: length x length square
  double dx = length / (n+1);  // physical size of each cell (+1 as don't simulate boundaries as they are given)
  double dt = 0.5 / nsteps;    // time interval (total time of 0.5s)


  // Stability requires that dt/(dx^2) <= 0.5,
  double r = alpha * dt / (dx * dx);

  // Print message detailing runtime configuration
  printf("\n");
  printf(" MMS heat equation\n\n");
  printf(LINE);
  printf("Problem input\n\n");
  printf(" Grid size: %d x %d\n", n, n);
  printf(" Cell width: %E\n", dx);
  printf(" Grid length: %lf x %lf\n", length, length);
  printf("\n");
  printf(" Alpha: %E\n", alpha);
  printf("\n");
  printf(" Steps: %d\n", nsteps);
  printf(" Total time: %E\n", dt*(double)nsteps);
  printf(" Time step: %E\n", dt);
  printf(LINE);

  // Stability check
  printf("Stability\n\n");
  printf(" r value: %lf\n", r);
  if (r > 0.5)
    printf(" Warning: unstable\n");
  printf(LINE);


  // Allocate two nxn grids
  double *u     = malloc(sizeof(double)*n*n);
  double *u_tmp = malloc(sizeof(double)*n*n);
  double *tmp;

  // Set the initial value of the grid under the MMS scheme
  initial_value(n, dx, length, u);
  zero(n, u_tmp);

  //
  // Run through timesteps under the explicit scheme
  //

  // Start the solve timer
  double tic = omp_get_wtime();
  for (int t = 0; t < nsteps; ++t) {

    // Call the solve kernel
    // Computes u_tmp at the next timestep
    // given the value of u at the current timestep
    solve(n, alpha, dx, dt, u, u_tmp);

    // Pointer swap
    tmp = u;
    u = u_tmp;
    u_tmp = tmp;
  }
  // Stop solve timer
  double toc = omp_get_wtime();

  //
  // Check the L2-norm of the computed solution
  // against the *known* solution from the MMS scheme
  //
  double norm = l2norm(n, u, nsteps, dt, alpha, dx, length);

  // Stop total timer
  double stop = omp_get_wtime();

  // Print results
  printf("Results\n\n");
  printf("Error (L2norm): %E\n", norm);
  printf("Solve time (s): %lf\n", toc-tic);
  printf("Total time (s): %lf\n", stop-start);
  printf(LINE);

  // Free the memory
  free(u);
  free(u_tmp);

}


// Sets the mesh to an initial value, determined by the MMS scheme
void initial_value(const int n, const double dx, const double length, double * restrict u) {

  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx; // Physical x position
    for (int i = 0; i < n; ++i) {
      u[i+j*n] = sin(PI * x / length) * sin(PI * y / length);
      x += dx;
    }
    y += dx; // Physical y position
  }
}


// Zero the array u
void zero(const int n, double * restrict u) {
  for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {
      u[i+j*n] = 0.0;
    }
  }
}


// Compute the next timestep, given the current timestep
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp) {

  // Finite difference constant multiplier
  const double r = alpha * dt / (dx * dx);
  const double r2 = 1.0 - 4.0*r;

  // Loop over the nxn grid
  #pragma omp target map(tofrom: u[0:n*n], u_tmp[0:n*n])
  #pragma omp loop collapse(2)
  for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {

      // Update the 5-point stencil, using boundary conditions on the edges of the domain.
      // Boundaries are zero because the MMS solution is zero there.
      u_tmp[i+j*n] =  r2 * u[i+j*n] +
      r * ((i < n-1) ? u[i+1+j*n] : 0.0) +
      r * ((i > 0)   ? u[i-1+j*n] : 0.0) +
      r * ((j < n-1) ? u[i+(j+1)*n] : 0.0) +
      r * ((j > 0)   ? u[i+(j-1)*n] : 0.0);
    }
  }
}


// True answer given by the manufactured solution
double solution(const double t, const double x, const double y, const double alpha, const double length) {

  return exp(-2.0*alpha*PI*PI*t/(length*length)) * sin(PI*x/length) * sin(PI*y/length);

}


// Computes the L2-norm of the computed grid and the MMS known solution
// The known solution is the same as the boundary function.
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length) {

  // Final (real) time simulated
  double time = dt * (double)nsteps;

  // L2-norm error
  double l2norm = 0.0;

  // Loop over the grid and compute difference of computed and known solutions as an L2-norm
  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx;
    for (int i = 0; i < n; ++i) {
      double answer = solution(time, x, y, alpha, length);
      l2norm += (u[i+j*n] - answer) * (u[i+j*n] - answer);

      x += dx;
    }
    y += dx;
  }

  return sqrt(l2norm);

}
```

### `Tarefa-21/heat_target_resident.c`

```c

/*
** PROGRAM: heat equation solve
**
** PURPOSE: This program will explore use of an explicit
**          finite difference method to solve the heat
**          equation under a method of manufactured solution (MMS)
**          scheme. The solution has been set to be a simple 
**          function based on exponentials and trig functions.
**
**          A finite difference scheme is used on a 1000x1000 cube.
**          A total of 0.5 units of time are simulated.
**
**          The MMS solution has been adapted from
**          G.W. Recktenwald (2011). Finite difference approximations
**          to the Heat Equation. Portland State University.
**
**
** USAGE:   Run with two arguments:
**          First is the number of cells.
**          Second is the number of timesteps.
**
**          For example, with 100x100 cells and 10 steps:
**
**          ./heat 100 10
**
**
** HISTORY: Written by Tom Deakin, Oct 2018
**
*/

#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include <omp.h>

// Key constants used in this program
#define PI acos(-1.0) // Pi
#define LINE "--------------------\n" // A line for fancy output

// Function definitions
void initial_value(const int n, const double dx, const double length, double * restrict u);
void zero(const int n, double * restrict u);
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp);
double solution(const double t, const double x, const double y, const double alpha, const double length);
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length);

// Main function
int main(int argc, char *argv[]) {

  // Start the total program runtime timer
  double start = omp_get_wtime();

  // Problem size, forms an nxn grid
  int n = 1000;

  // Number of timesteps
  int nsteps = 10;


  // Check for the correct number of arguments
  // Print usage and exits if not correct
  if (argc == 3) {

    // Set problem size from first argument
    n = atoi(argv[1]);
    if (n < 0) {
      fprintf(stderr, "Error: n must be positive\n");
      exit(EXIT_FAILURE);
    }

    // Set number of timesteps from second argument
    nsteps = atoi(argv[2]);
    if (nsteps < 0) {
      fprintf(stderr, "Error: nsteps must be positive\n");
      exit(EXIT_FAILURE);
    }
  }


  //
  // Set problem definition
  //
  double alpha = 0.1;          // heat equation coefficient
  double length = 1000.0;      // physical size of domain: length x length square
  double dx = length / (n+1);  // physical size of each cell (+1 as don't simulate boundaries as they are given)
  double dt = 0.5 / nsteps;    // time interval (total time of 0.5s)


  // Stability requires that dt/(dx^2) <= 0.5,
  double r = alpha * dt / (dx * dx);

  // Print message detailing runtime configuration
  printf("\n");
  printf(" MMS heat equation\n\n");
  printf(LINE);
  printf("Problem input\n\n");
  printf(" Grid size: %d x %d\n", n, n);
  printf(" Cell width: %E\n", dx);
  printf(" Grid length: %lf x %lf\n", length, length);
  printf("\n");
  printf(" Alpha: %E\n", alpha);
  printf("\n");
  printf(" Steps: %d\n", nsteps);
  printf(" Total time: %E\n", dt*(double)nsteps);
  printf(" Time step: %E\n", dt);
  printf(LINE);

  // Stability check
  printf("Stability\n\n");
  printf(" r value: %lf\n", r);
  if (r > 0.5)
    printf(" Warning: unstable\n");
  printf(LINE);


  // Allocate two nxn grids
  double *u     = malloc(sizeof(double)*n*n);
  double *u_tmp = malloc(sizeof(double)*n*n);
  double *tmp;

  // Set the initial value of the grid under the MMS scheme
  initial_value(n, dx, length, u);
  zero(n, u_tmp);

  //
  // Run through timesteps under the explicit scheme
  //

  // Start the solve timer
  double tic = omp_get_wtime();
  #pragma omp target enter data map(to: u[0:n*n], u_tmp[0:n*n])

  for (int t = 0; t < nsteps; ++t) {

    // Call the solve kernel
    // Computes u_tmp at the next timestep
    // given the value of u at the current timestep
    solve(n, alpha, dx, dt, u, u_tmp);

    // Pointer swap
    tmp = u;
    u = u_tmp;
    u_tmp = tmp;
  }

  #pragma omp target exit data map(from: u[0:n*n])
  // Stop solve timer
  double toc = omp_get_wtime();

  //
  // Check the L2-norm of the computed solution
  // against the *known* solution from the MMS scheme
  //
  double norm = l2norm(n, u, nsteps, dt, alpha, dx, length);

  // Stop total timer
  double stop = omp_get_wtime();

  // Print results
  printf("Results\n\n");
  printf("Error (L2norm): %E\n", norm);
  printf("Solve time (s): %lf\n", toc-tic);
  printf("Total time (s): %lf\n", stop-start);
  printf(LINE);

  // Free the memory
  free(u);
  free(u_tmp);

}


// Sets the mesh to an initial value, determined by the MMS scheme
void initial_value(const int n, const double dx, const double length, double * restrict u) {

  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx; // Physical x position
    for (int i = 0; i < n; ++i) {
      u[i+j*n] = sin(PI * x / length) * sin(PI * y / length);
      x += dx;
    }
    y += dx; // Physical y position
  }
}


// Zero the array u
void zero(const int n, double * restrict u) {
  for (int j = 0; j < n; ++j) {
    for (int i = 0; i < n; ++i) {
      u[i+j*n] = 0.0;
    }
  }
}


// Compute the next timestep, given the current timestep
void solve(const int n, const double alpha, const double dx, const double dt, const double * restrict u, double * restrict u_tmp) {

  // Finite difference constant multiplier
  const double r = alpha * dt / (dx * dx);
  const double r2 = 1.0 - 4.0*r;

  // Loop over the nxn grid
  #pragma omp target
  #pragma omp loop collapse(2)
  for (int j = 0; j < n; ++j) {
    for (int i = 0; i < n; ++i) {

      // Update the 5-point stencil, using boundary conditions on the edges of the domain.
      // Boundaries are zero because the MMS solution is zero there.
      u_tmp[i+j*n] =  r2 * u[i+j*n] +
      r * ((i < n-1) ? u[i+1+j*n] : 0.0) +
      r * ((i > 0)   ? u[i-1+j*n] : 0.0) +
      r * ((j < n-1) ? u[i+(j+1)*n] : 0.0) +
      r * ((j > 0)   ? u[i+(j-1)*n] : 0.0);
    }
  }
}


// True answer given by the manufactured solution
double solution(const double t, const double x, const double y, const double alpha, const double length) {

  return exp(-2.0*alpha*PI*PI*t/(length*length)) * sin(PI*x/length) * sin(PI*y/length);

}


// Computes the L2-norm of the computed grid and the MMS known solution
// The known solution is the same as the boundary function.
double l2norm(const int n, const double * restrict u, const int nsteps, const double dt, const double alpha, const double dx, const double length) {

  // Final (real) time simulated
  double time = dt * (double)nsteps;

  // L2-norm error
  double l2norm = 0.0;

  // Loop over the grid and compute difference of computed and known solutions as an L2-norm
  double y = dx;
  for (int j = 0; j < n; ++j) {
    double x = dx;
    for (int i = 0; i < n; ++i) {
      double answer = solution(time, x, y, alpha, length);
      l2norm += (u[i+j*n] - answer) * (u[i+j*n] - answer);

      x += dx;
    }
    y += dx;
  }

  return sqrt(l2norm);

}
```

<!-- codigos-fonte-c-fim -->

<!-- scripts-sbatch-npad-inicio -->
## Scripts sbatch do NPAD

### `Tarefa-21/run_npad.sbatch`

```bash
#!/bin/bash
#SBATCH --partition=gpu-4-a100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:40:00
#SBATCH --job-name=t21-heat
#SBATCH --output=tarefa21-%j.slurm.out
#SBATCH --error=tarefa21-%j.slurm.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/Tarefa-21" ]]; then
    cd "${ROOT}/Tarefa-21"
else
    cd "$(dirname "$0")"
fi

mkdir -p bin resultados

JOB_ID="${SLURM_JOB_ID:-local}"
exec > >(tee -a "resultados/tarefa21-${JOB_ID}.out")
exec 2> >(tee -a "resultados/tarefa21-${JOB_ID}.err" >&2)

module load compilers/nvidia/nvhpc/24.11

NVC="${NVC:-nvc}"
CPU_FLAGS="${CPU_FLAGS:--fast -mp=multicore}"
GPU_FLAGS="${GPU_FLAGS:--fast -mp=gpu}"

echo "Compilador:"
"${NVC}" --version
echo

echo "Compilando CPU..."
"${NVC}" ${CPU_FLAGS} heat_cpu.c -o bin/heat_cpu -lm

echo "Compilando GPU baseline com map(tofrom) por passo..."
"${NVC}" ${GPU_FLAGS} heat_target_baseline.c -o bin/heat_gpu_baseline -lm

echo "Compilando GPU otimizada com dados residentes..."
"${NVC}" ${GPU_FLAGS} heat_target_resident.c -o bin/heat_gpu_resident -lm

CSV="resultados/heat_resultados_${JOB_ID}.csv"
CASES="${CASES:-1000:10 2000:20 4000:40}"
REPEATS="${REPEATS:-3}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-1}}"
export OMP_TARGET_OFFLOAD="${OMP_TARGET_OFFLOAD:-MANDATORY}"

printf "job_id,variant,executable,n,nsteps,repeat,status,error_l2,solve_time_s,total_time_s,omp_threads,omp_devices,offload_policy\n" > "${CSV}"

run_case() {
    local variant="$1"
    local executable="$2"
    local n="$3"
    local nsteps="$4"
    local repeat="$5"
    local raw="resultados/raw_${variant}_n${n}_steps${nsteps}_r${repeat}_${JOB_ID}.log"

    echo "Executando ${variant}: n=${n}, nsteps=${nsteps}, repeat=${repeat}"

    set +e
    output="$("${executable}" "${n}" "${nsteps}" 2>&1)"
    status="$?"
    set -e

    printf "%s\n" "${output}" > "${raw}"

    error_l2="$(printf "%s\n" "${output}" | awk -F: '/Error \(L2norm\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"
    solve_time="$(printf "%s\n" "${output}" | awk -F: '/Solve time \(s\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"
    total_time="$(printf "%s\n" "${output}" | awk -F: '/Total time \(s\)/ {gsub(/[ \t]/, "", $2); print $2; exit}')"

    printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
        "${JOB_ID}" \
        "${variant}" \
        "${executable}" \
        "${n}" \
        "${nsteps}" \
        "${repeat}" \
        "${status}" \
        "${error_l2}" \
        "${solve_time}" \
        "${total_time}" \
        "${OMP_NUM_THREADS}" \
        "${OMP_NUM_DEVICES:-unknown}" \
        "${OMP_TARGET_OFFLOAD}" >> "${CSV}"

    if [[ "${status}" -ne 0 ]]; then
        echo "Falha em ${variant} n=${n} nsteps=${nsteps}. Veja ${raw}." >&2
        return "${status}"
    fi
}

echo "Configuracao:"
echo "  CASES=${CASES}"
echo "  REPEATS=${REPEATS}"
echo "  OMP_NUM_THREADS=${OMP_NUM_THREADS}"
echo "  OMP_TARGET_OFFLOAD=${OMP_TARGET_OFFLOAD}"
echo "  CSV=${CSV}"
echo

for case_spec in ${CASES}; do
    IFS=: read -r n nsteps <<< "${case_spec}"
    for repeat in $(seq 1 "${REPEATS}"); do
        run_case "cpu" "./bin/heat_cpu" "${n}" "${nsteps}" "${repeat}"
        run_case "gpu_baseline" "./bin/heat_gpu_baseline" "${n}" "${nsteps}" "${repeat}"
        run_case "gpu_resident" "./bin/heat_gpu_resident" "${n}" "${nsteps}" "${repeat}"
    done
done

echo
echo "Resultados gravados em ${CSV}"
echo "Para gerar o relatorio:"
echo "  cd Tarefa-21"
echo "  python3 comparar_resultados.py"
```

### `Tarefa-21/run_nsys_npad.sbatch`

```bash
#!/bin/bash
#SBATCH --partition=gpu-4-a100
#SBATCH --gpus-per-node=1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --job-name=t21-heat-nsys
#SBATCH --output=nsys-tarefa21-%j.slurm.out
#SBATCH --error=nsys-tarefa21-%j.slurm.err

set -euo pipefail

ROOT="${SLURM_SUBMIT_DIR:-$(pwd)}"
if [[ -d "${ROOT}/Tarefa-21" ]]; then
    cd "${ROOT}/Tarefa-21"
else
    cd "$(dirname "$0")"
fi

mkdir -p bin resultados/perfis

JOB_ID="${SLURM_JOB_ID:-local}"
exec > >(tee -a "resultados/nsys-${JOB_ID}.out")
exec 2> >(tee -a "resultados/nsys-${JOB_ID}.err" >&2)

module load compilers/nvidia/nvhpc/24.11

if ! command -v nsys >/dev/null 2>&1; then
    module load nsight-systems 2>/dev/null || true
fi

if ! command -v nsys >/dev/null 2>&1; then
    echo "Erro: comando nsys nao encontrado. Verifique os modulos disponiveis com: module avail nsight" >&2
    exit 1
fi

NVC="${NVC:-nvc}"
GPU_FLAGS="${GPU_FLAGS:--fast -mp=gpu}"
N="${N:-2000}"
NSTEPS="${NSTEPS:-20}"
PROFILE_VARIANT="${PROFILE_VARIANT:-resident}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-${SLURM_CPUS_PER_TASK:-1}}"
export OMP_TARGET_OFFLOAD="${OMP_TARGET_OFFLOAD:-MANDATORY}"

echo "Configuracao do perfil:"
echo "  PROFILE_VARIANT=${PROFILE_VARIANT}"
echo "  N=${N}"
echo "  NSTEPS=${NSTEPS}"
echo "  OMP_NUM_THREADS=${OMP_NUM_THREADS}"
echo "  OMP_TARGET_OFFLOAD=${OMP_TARGET_OFFLOAD}"
echo

echo "Compilador:"
"${NVC}" --version
echo

echo "Nsight Systems:"
nsys --version
echo

profile_variant() {
    local variant="$1"
    local source="$2"
    local executable="bin/heat_${variant}"
    local output="resultados/perfis/nsys_heat_${variant}_n${N}_s${NSTEPS}_${JOB_ID}"

    echo "Compilando ${variant}..."
    "${NVC}" ${GPU_FLAGS} "${source}" -o "${executable}" -lm

    echo "Gerando perfil ${variant} em ${output}.nsys-rep"
    nsys profile \
        --trace=cuda,nvtx,osrt \
        --stats=true \
        --force-overwrite=true \
        -o "${output}" \
        "./${executable}" "${N}" "${NSTEPS}"

    echo
    echo "Resumo ${variant}:"
    nsys stats "${output}.nsys-rep"
}

case "${PROFILE_VARIANT}" in
    resident|optimized|otimizada)
        profile_variant "resident" "heat_target_resident.c"
        ;;
    baseline)
        profile_variant "baseline" "heat_target_baseline.c"
        ;;
    both)
        profile_variant "baseline" "heat_target_baseline.c"
        profile_variant "resident" "heat_target_resident.c"
        ;;
    *)
        echo "Erro: PROFILE_VARIANT deve ser resident, baseline ou both." >&2
        exit 2
        ;;
esac

echo
echo "Perfis gerados em Tarefa-21/resultados/perfis/"
```

<!-- scripts-sbatch-npad-fim -->
