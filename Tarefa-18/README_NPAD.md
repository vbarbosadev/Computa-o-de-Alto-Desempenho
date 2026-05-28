# Tarefa 18

Produto matriz-vetor com distribuicao por colunas usando tipos derivados MPI.

## Execucao local

```bash
python3 Tarefa-18/coletar_mpi.py
python3 Tarefa-18/gerar_relatorio.py
```

O script compila:

- `Tarefa-17/matvec_seq.c`, usado como base sequencial;
- `Tarefa-18/matvec_cols_vector.c`;
- `Tarefa-18/matvec_cols_resized.c`.

Resultados:

```text
Tarefa-18/resultados/tarefa18_resultados.csv
Tarefa-18/resultados/speedup.png
Tarefa-18/resultados/tempo_*.png
Tarefa-18/resultados/relatorio_tarefa18.md
```

## Execucao no NPAD

```bash
sbatch Tarefa-18/run_npad.sbatch
```
