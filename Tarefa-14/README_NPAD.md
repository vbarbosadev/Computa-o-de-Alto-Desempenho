# Tarefa 14 - Como rodar no NPAD

## 1. Enviar a pasta para o NPAD

Na maquina local, a partir da raiz do repositorio:

```bash
scp -r Tarefa-14 usuario@servidor-do-npad:~/atividades-aula/
```

Substitua `usuario` e `servidor-do-npad` pelos dados do seu acesso.

## 2. Entrar no NPAD

```bash
ssh usuario@servidor-do-npad
cd ~/atividades-aula/Tarefa-14
```

## 3. Carregar MPI

Se o NPAD usar modules, carregue uma implementacao MPI e o compilador:

```bash
module avail openmpi
module load openmpi
module load gcc
```

Confirme que os comandos existem:

```bash
which mpicc
which mpirun
```

## 4. Teste rapido em ambiente interativo

```bash
mpicc -O3 -Wall -Wextra mpi_send.c -o mpi_send
mpirun -np 2 ./mpi_send --bytes 1024 --iteracoes 1000
```

Se esse comando imprimir `RESULT metodo=MPI_Send ...`, o ambiente MPI esta pronto.

## 5. Rodar coleta completa sem Slurm

Use apenas em um no liberado para execucao interativa:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib

python coletar_mpi.py \
  --repeats 3 \
  --sizes 8 16 32 64 128 256 512 1024 4096 16384 65536 262144 1048576

python gerar_relatorio.py
```

## 6. Rodar com Slurm

Edite `run_npad.sbatch` se precisar trocar particao, tempo, modulo MPI ou numero de
nos. Depois submeta:

```bash
sbatch run_npad.sbatch
```

Consultar fila:

```bash
squeue -u $USER
```

Quando terminar, os arquivos ficarao em:

```bash
Tarefa-14/resultados/tarefa14_resultados.csv
Tarefa-14/resultados/tempo_por_tamanho.png
Tarefa-14/resultados/largura_banda.png
Tarefa-14/resultados/relatorio_tarefa14.md
Tarefa-14/resultados/slurm-*.out
Tarefa-14/resultados/slurm-*.err
```

## 7. Baixar resultados para a maquina local

Na maquina local:

```bash
scp -r usuario@servidor-do-npad:~/atividades-aula/Tarefa-14/resultados ./Tarefa-14/
```

## 8. O que analisar no relatorio

- Mensagens pequenas: faixa em que a latencia domina e o tempo muda pouco com o
  tamanho da mensagem.
- Mensagens grandes: faixa em que o tempo cresce com o tamanho e a largura de banda
  passa a dominar.
- Diferencas entre `MPI_Send`, `MPI_Bsend`, `MPI_Rsend` e `MPI_Ssend`.
- Custo extra do protocolo usado em `MPI_Rsend`, necessario para garantir que o
  recebimento ja foi postado antes do envio ready.
