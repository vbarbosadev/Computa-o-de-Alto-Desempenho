# Repository Guidelines

## Project Structure & Module Organization

This repository contains CAD/high-performance computing coursework organized by assignment. `Tarefa-01/` through `Tarefa-12/`, `Tarefa-extra/`, and `Aula-06/` hold C programs, mostly OpenMP experiments. `scripts/` contains shared runners for early assignments. Several task folders include local `run_tests.py` or `run_tests.sh` scripts. `dados/` stores CSV inputs/results, `analise/` contains Python analysis code and generated graphs, `questoes/` stores assignment prompts, and `relatorios/` stores Markdown/PDF reports plus exported PNG charts. Course reference PDFs live in `conteudos/` and at the repository root.

## Build, Test, and Development Commands

- `bash scripts/run_tests.sh`: compile and run Tarefas 1-3, producing CSV files in `dados/`.
- `bash scripts/run_tarefa3.sh`: rerun only the Leibniz PI benchmark for Tarefa 3.
- `python3 Tarefa-10/run_tests.py`: compile, benchmark, and report Tarefa 10 results.
- `python3 analise/analise.py`: regenerate analysis graphs from CSV files in `dados/`.
- `gcc -O2 -fopenmp Tarefa-06/pi_parallel_for.c -o Tarefa-06/pi_parallel_for -lm`: example manual build for an OpenMP C program.

Run task-local scripts from the repository root unless the script documents another working directory.

## Coding Style & Naming Conventions

Use C99-compatible C unless a task requires otherwise. Keep OpenMP pragmas close to the loop or region they control, and compile OpenMP code with `-fopenmp`. Follow the existing naming style: task folders use `Tarefa-NN/`, C files use lowercase descriptive names such as `pi_randr_reduction.c`, and generated plots/results use task-specific names. Python scripts should use `pathlib` or explicit repository-relative paths and keep generated outputs under `dados/`, `resultados/`, `relatorios/`, or `analise/graficos/`.

## Testing Guidelines

There is no single project-wide test framework. Validation is script-based: use each task's `run_tests.py` or `run_tests.sh` when present, then inspect generated CSV, JSON, PNG, and Markdown outputs. For new tasks, include a reproducible runner that compiles required C sources, records command parameters, and writes results to a task-local `dados/` or `resultados/` directory.

## Commit & Pull Request Guidelines

The local `git` executable is unavailable, so repository commit history could not be inspected. Use concise imperative commit messages, for example `Add Tarefa 12 scaling report`. Pull requests should list changed task folders, commands run, generated artifacts updated, and any environment assumptions such as compiler, Python packages, thread count, or SLURM/NPAD usage.

## Agent-Specific Instructions

Do not overwrite generated reports or benchmark outputs unless the requested task requires regeneration. Before editing, check whether a task already has a local runner and follow its output conventions.
