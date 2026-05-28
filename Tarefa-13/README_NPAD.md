# Tarefa 13 - Como rodar no NPAD

Esta tarefa reaproveita o codigo de Navier-Stokes da Tarefa 12 e mede o impacto de
afinidade de threads em escalabilidade forte.

## 1. Enviar a pasta para o NPAD

Na maquina local, a partir da raiz do repositorio:

```bash
scp -r Tarefa-13 usuario@servidor-do-npad:~/atividades-aula/
```

Substitua `usuario` e `servidor-do-npad` pelos dados do seu acesso.

## 2. Entrar no NPAD

```bash
ssh usuario@servidor-do-npad
cd ~/atividades-aula/Tarefa-13
```

## 3. Teste rapido em ambiente interativo

```bash
gcc -O3 -march=native -fopenmp navier_scaling.c -lm -o navier_affinity
OMP_NUM_THREADS=4 OMP_PROC_BIND=spread OMP_PLACES=cores \
  ./navier_affinity --mode omp-region --nx 1024 --ny 1024 --steps 200 \
  --schedule static --collapse 1
```

Se esse comando imprimir `RESULT elapsed=...`, o codigo esta pronto para a coleta.

## 4. Rodar coleta completa sem Slurm

Use apenas em um no de computacao liberado para execucao interativa:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_afinidade.py \
  --max-threads 32 \
  --repeats 3 \
  --steps 1000 \
  --n 2048 \
  --mode omp-region \
  --schedule static \
  --collapse 1 \
  --affinities all

python gerar_relatorio.py
```

## 5. Rodar com Slurm

Edite `run_npad.sbatch` se precisar trocar particao, tempo ou numero de CPUs.
Depois submeta:

```bash
sbatch run_npad.sbatch
```

Consultar fila:

```bash
squeue -u $USER
```

Quando terminar, os arquivos ficarao em:

```bash
Tarefa-13/resultados/tarefa13_afinidade.csv
Tarefa-13/resultados/affinity_elapsed.png
Tarefa-13/resultados/affinity_speedup.png
Tarefa-13/resultados/relatorio_tarefa13.md
Tarefa-13/resultados/slurm-*.out
Tarefa-13/resultados/slurm-*.err
```

## 6. O que analisar

- Se `sem_bind` e pior que as politicas com `OMP_PROC_BIND`, ha indicio de custo de
  migracao de threads ou perda de localidade.
- Se `close_cores` e melhor, a localidade de cache provavelmente ajuda o stencil.
- Se `spread_cores` e melhor, distribuir threads pelo no provavelmente reduz disputa
  por caches, nucleos fisicos ou banda de memoria.
- Se `threads` for pior que `cores`, o uso de hyperthreading provavelmente nao ajuda
  este kernel limitado por memoria.
