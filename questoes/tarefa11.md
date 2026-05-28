## Tarefa 11 - Escalonamento de tarefas com a equação Navier-Stokes

Escreva um código que simule o movimento de um fluido ao longo do tempo usando a equação de Navier-Stokes, considerando apenas os efeitos da viscosidade.
Desconsidere a pressão e quaisquer forças externas. Utilize diferenças finitas para discretizar o espaço e simule a evolução da velocidade do fluido no tempo.
Inicialize o fluido parado ou com velocidade constante e verifique se o campo permanece estável.
Em seguida, crie uma pequena perturbação e observe se ela se difunde suavemente.como

Após validar o código, paralelize-o com OpenMP e explore o impacto das cláusulas schedule e collapse no desempenho da execução paralela.


srun --partition=intel-128 --nodes=1 --ntasks=1 --cpus-per-task=4 --time=00:10:00 bash -lc 'OMP_NUM_THREADS=4 OMP_PROC_BIND=close OMP_PLACES=cores ./navier_scaling --mode omp-region --nx 1024 --ny 1024 --steps 200 --schedule static --collapse 1'