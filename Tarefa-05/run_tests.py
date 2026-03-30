import subprocess
import re
import statistics
import matplotlib.pyplot as plt

def compile_code():
    print("Compilando arquivos C...")
    # Atenção: usa gcc. Se for rodar no windows, talvez você precise configurar, mas no Linux/WSL isso vai direto.
    subprocess.run(["gcc", "-o", "seq", "primo_sequencial.c"], check=True)
    subprocess.run(["gcc", "-o", "par", "primos_parallel.c", "-fopenmp"], check=True)
    print("Compilação concluída com sucesso.\n")

def run_test(executable, num_runs=5):
    times = []
    print(f"Executando o programa '{executable}' {num_runs} vezes...")
    for i in range(num_runs):
        # Executa e captura a string plotada no C. O "./" indica executável estilo unix/linux.
        result = subprocess.run([f"./{executable}"], capture_output=True, text=True)
        
        # Expressão regular para encontrar o valor numérico que está nos prints ("Tempo de execucao: X.XXXX segundos")
        match = re.search(r"Tempo de execucao:\s*([\d\.]+)\s*segundos", result.stdout)
        
        if match:
            time_taken = float(match.group(1))
            times.append(time_taken)
            print(f"  [Rodada {i+1}] Tempo: {time_taken:.4f} s")
        else:
            print(f"  [Rodada {i+1}] Erro ao ler a saída: \n{result.stdout}")
            
    if times:
        avg_time = statistics.mean(times)
        print(f"-> Média do '{executable}': {avg_time:.4f} s\n")
    return times

def main():
    try:
        compile_code()
    except Exception as e:
        print(f"Falha ao compilar: {e}")
        return

    # Quantas vezes cada programa será rodado para tirar uma média mais justa
    runs = 10 
    
    times_seq = run_test("seq", runs)
    times_par = run_test("par", runs)
    
    if times_seq and times_par:
        print("Gerando gráfico de comparação...")
        labels = ['Sequencial', 'Paralelo (OpenMP)']
        means = [statistics.mean(times_seq), statistics.mean(times_par)]
        
        plt.figure(figsize=(8, 6))
        bars = plt.bar(labels, means, color=['#e74c3c', '#2ecc71'])
        
        # Adiciona rótulos nos eixos
        plt.ylabel('Tempo Médio de Execução (segundos)')
        plt.title(f'Comparação de Desempenho (Média de {runs} execuções)')
        
        # Adiciona os valores (em segundos) no topo de cada barra para visualização mais fácil
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + (yval * 0.02), f'{yval:.4f}s', ha='center', va='bottom', fontweight='bold')
            
        # Opcional: Adiciona marca d'água de speedup
        speedup = means[0] / means[1]
        plt.text(1.3, max(means)*0.9, f"Speedup: {speedup:.2f}x", fontsize=12, bbox=dict(facecolor='white', alpha=0.5))

        # Salva a imagem no repositório local
        plt.savefig('comparacao_tempo.png', format='png', dpi=300)
        print("Gráfico salvo como 'comparacao_tempo.png' com sucesso!")

if __name__ == "__main__":
    main()
