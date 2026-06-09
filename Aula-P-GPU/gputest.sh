#!/bin/bash
#SBATCH --partition gpu-8-v100 
#SBATCH --gpus-per-node=1   # Número GPUs por nó
#SBATCH --nodes 1
#SBATCH --time 00:02:00
#SBATCH --job-name gputest
#SBATCH --output gputest-%j.out

ulimit -s unlimited
module load compilers/nvidia/nvhpc/24.11
./a.out
