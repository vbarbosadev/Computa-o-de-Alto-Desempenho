NVC ?= nvc

.PHONY: all clean

all: vadd_cpu vadd_gpu

vadd_cpu: vadd_cpu.c
	$(NVC) -fast -mp vadd_cpu.c -o vadd_cpu -lm

vadd_gpu: vadd_gpu.c
	$(NVC) -fast -mp=gpu vadd_gpu.c -o vadd_gpu -lm

clean:
	rm -f vadd_cpu vadd_gpu *.o
