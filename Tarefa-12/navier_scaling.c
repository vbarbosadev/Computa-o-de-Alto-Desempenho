#include <math.h>
#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int nx;
    int ny;
    int steps;
    double nu;
    double dt;
    const char *mode;
    const char *init;
    const char *schedule_name;
    int chunk;
    int collapse;
    double u0;
} Config;

typedef struct {
    double min;
    double max;
    double l2;
    double sum;
} Stats;

static int idx(int i, int j, int ny) {
    return i * ny + j;
}

static void set_defaults(Config *cfg) {
    cfg->nx = 1024;
    cfg->ny = 1024;
    cfg->steps = 1000;
    cfg->nu = 0.1;
    cfg->dt = 0.1;
    cfg->mode = "omp-region";
    cfg->init = "perturb";
    cfg->schedule_name = "static";
    cfg->chunk = 0;
    cfg->collapse = 1;
    cfg->u0 = 1.0;
}

static void usage(const char *prog) {
    printf("Uso: %s [opcoes]\n", prog);
    printf("  --mode seq|omp-basic|omp-region\n");
    printf("  --nx <int> --ny <int> --steps <int>\n");
    printf("  --nu <double> --dt <double>\n");
    printf("  --init zero|uniform|perturb --u0 <double>\n");
    printf("  --schedule static|dynamic|guided|auto --chunk <int>\n");
    printf("  --collapse 1|2\n");
}

static int parse_int(const char *s, int *out) {
    char *end = NULL;
    long v = strtol(s, &end, 10);
    if (end == s || *end != '\0') return 0;
    *out = (int)v;
    return 1;
}

static int parse_double(const char *s, double *out) {
    char *end = NULL;
    double v = strtod(s, &end);
    if (end == s || *end != '\0') return 0;
    *out = v;
    return 1;
}

static int parse_args(int argc, char **argv, Config *cfg) {
    int i;
    for (i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--mode") == 0 && i + 1 < argc) {
            cfg->mode = argv[++i];
        } else if (strcmp(argv[i], "--nx") == 0 && i + 1 < argc) {
            if (!parse_int(argv[++i], &cfg->nx)) return 0;
        } else if (strcmp(argv[i], "--ny") == 0 && i + 1 < argc) {
            if (!parse_int(argv[++i], &cfg->ny)) return 0;
        } else if (strcmp(argv[i], "--steps") == 0 && i + 1 < argc) {
            if (!parse_int(argv[++i], &cfg->steps)) return 0;
        } else if (strcmp(argv[i], "--nu") == 0 && i + 1 < argc) {
            if (!parse_double(argv[++i], &cfg->nu)) return 0;
        } else if (strcmp(argv[i], "--dt") == 0 && i + 1 < argc) {
            if (!parse_double(argv[++i], &cfg->dt)) return 0;
        } else if (strcmp(argv[i], "--init") == 0 && i + 1 < argc) {
            cfg->init = argv[++i];
        } else if (strcmp(argv[i], "--u0") == 0 && i + 1 < argc) {
            if (!parse_double(argv[++i], &cfg->u0)) return 0;
        } else if (strcmp(argv[i], "--schedule") == 0 && i + 1 < argc) {
            cfg->schedule_name = argv[++i];
        } else if (strcmp(argv[i], "--chunk") == 0 && i + 1 < argc) {
            if (!parse_int(argv[++i], &cfg->chunk)) return 0;
        } else if (strcmp(argv[i], "--collapse") == 0 && i + 1 < argc) {
            if (!parse_int(argv[++i], &cfg->collapse)) return 0;
        } else {
            return 0;
        }
    }
    return 1;
}

static int validate_config(const Config *cfg) {
    if (cfg->nx < 3 || cfg->ny < 3 || cfg->steps < 0) return 0;
    if (cfg->nu <= 0.0 || cfg->dt <= 0.0) return 0;
    if (strcmp(cfg->mode, "seq") != 0 &&
        strcmp(cfg->mode, "omp-basic") != 0 &&
        strcmp(cfg->mode, "omp-region") != 0) return 0;
    if (strcmp(cfg->init, "zero") != 0 &&
        strcmp(cfg->init, "uniform") != 0 &&
        strcmp(cfg->init, "perturb") != 0) return 0;
    if (strcmp(cfg->schedule_name, "static") != 0 &&
        strcmp(cfg->schedule_name, "dynamic") != 0 &&
        strcmp(cfg->schedule_name, "guided") != 0 &&
        strcmp(cfg->schedule_name, "auto") != 0) return 0;
    if (cfg->chunk < 0) return 0;
    if (cfg->collapse != 1 && cfg->collapse != 2) return 0;
    return 1;
}

static int is_stable(const Config *cfg) {
    return cfg->dt * cfg->nu <= 0.25;
}

static omp_sched_t to_omp_sched(const char *name) {
    if (strcmp(name, "dynamic") == 0) return omp_sched_dynamic;
    if (strcmp(name, "guided") == 0) return omp_sched_guided;
    if (strcmp(name, "auto") == 0) return omp_sched_auto;
    return omp_sched_static;
}

static void apply_boundary_seq(double *u, int nx, int ny) {
    int i, j;
    for (j = 1; j < ny - 1; j++) {
        u[idx(0, j, ny)] = u[idx(1, j, ny)];
        u[idx(nx - 1, j, ny)] = u[idx(nx - 2, j, ny)];
    }
    for (i = 1; i < nx - 1; i++) {
        u[idx(i, 0, ny)] = u[idx(i, 1, ny)];
        u[idx(i, ny - 1, ny)] = u[idx(i, ny - 2, ny)];
    }
    u[idx(0, 0, ny)] = u[idx(1, 1, ny)];
    u[idx(0, ny - 1, ny)] = u[idx(1, ny - 2, ny)];
    u[idx(nx - 1, 0, ny)] = u[idx(nx - 2, 1, ny)];
    u[idx(nx - 1, ny - 1, ny)] = u[idx(nx - 2, ny - 2, ny)];
}

static void init_field(double *u, const Config *cfg) {
    int i, j;
    int cx = cfg->nx / 2;
    int cy = cfg->ny / 2;

    for (i = 0; i < cfg->nx; i++) {
        for (j = 0; j < cfg->ny; j++) {
            u[idx(i, j, cfg->ny)] = 0.0;
        }
    }

    if (strcmp(cfg->init, "uniform") == 0) {
        for (i = 0; i < cfg->nx; i++) {
            for (j = 0; j < cfg->ny; j++) {
                u[idx(i, j, cfg->ny)] = cfg->u0;
            }
        }
    } else if (strcmp(cfg->init, "perturb") == 0) {
        double sigma = 0.08 * (cfg->nx < cfg->ny ? cfg->nx : cfg->ny);
        if (sigma < 1.0) sigma = 1.0;
        for (i = 1; i < cfg->nx - 1; i++) {
            for (j = 1; j < cfg->ny - 1; j++) {
                double dx = (double)(i - cx);
                double dy = (double)(j - cy);
                double r2 = dx * dx + dy * dy;
                u[idx(i, j, cfg->ny)] = cfg->u0 * exp(-r2 / (2.0 * sigma * sigma));
            }
        }
        apply_boundary_seq(u, cfg->nx, cfg->ny);
    }
}

static void step_seq(const double *restrict u, double *restrict u_next, const Config *cfg) {
    int i, j;
    int ny = cfg->ny;
    double alpha = cfg->dt * cfg->nu;

    for (i = 1; i < cfg->nx - 1; i++) {
        for (j = 1; j < cfg->ny - 1; j++) {
            int p = idx(i, j, ny);
            double c = u[p];
            double lap = u[p - ny] + u[p + ny] + u[p - 1] + u[p + 1] - 4.0 * c;
            u_next[p] = c + alpha * lap;
        }
    }
    apply_boundary_seq(u_next, cfg->nx, cfg->ny);
}

static void simulate_seq(double **u_ptr, double **u_next_ptr, const Config *cfg) {
    int t;
    double *u = *u_ptr;
    double *u_next = *u_next_ptr;
    for (t = 0; t < cfg->steps; t++) {
        double *tmp;
        step_seq(u, u_next, cfg);
        tmp = u;
        u = u_next;
        u_next = tmp;
    }
    *u_ptr = u;
    *u_next_ptr = u_next;
}

static void step_omp_basic(const double *restrict u, double *restrict u_next, const Config *cfg) {
    int i, j;
    int ny = cfg->ny;
    double alpha = cfg->dt * cfg->nu;
    omp_set_schedule(to_omp_sched(cfg->schedule_name), cfg->chunk);

    if (cfg->collapse == 2) {
#pragma omp parallel for collapse(2) schedule(runtime)
        for (i = 1; i < cfg->nx - 1; i++) {
            for (j = 1; j < cfg->ny - 1; j++) {
                int p = idx(i, j, ny);
                double c = u[p];
                double lap = u[p - ny] + u[p + ny] + u[p - 1] + u[p + 1] - 4.0 * c;
                u_next[p] = c + alpha * lap;
            }
        }
    } else {
#pragma omp parallel for schedule(runtime)
        for (i = 1; i < cfg->nx - 1; i++) {
            for (j = 1; j < cfg->ny - 1; j++) {
                int p = idx(i, j, ny);
                double c = u[p];
                double lap = u[p - ny] + u[p + ny] + u[p - 1] + u[p + 1] - 4.0 * c;
                u_next[p] = c + alpha * lap;
            }
        }
    }
    apply_boundary_seq(u_next, cfg->nx, cfg->ny);
}

static void simulate_omp_basic(double **u_ptr, double **u_next_ptr, const Config *cfg) {
    int t;
    double *u = *u_ptr;
    double *u_next = *u_next_ptr;
    for (t = 0; t < cfg->steps; t++) {
        double *tmp;
        step_omp_basic(u, u_next, cfg);
        tmp = u;
        u = u_next;
        u_next = tmp;
    }
    *u_ptr = u;
    *u_next_ptr = u_next;
}

static void simulate_omp_region(double **u_ptr, double **u_next_ptr, const Config *cfg) {
    int nx = cfg->nx;
    int ny = cfg->ny;
    double alpha = cfg->dt * cfg->nu;
    double *u = *u_ptr;
    double *u_next = *u_next_ptr;

    omp_set_schedule(to_omp_sched(cfg->schedule_name), cfg->chunk);

#pragma omp parallel shared(u, u_next)
    {
        int i, j;
        int step;
        for (step = 0; step < cfg->steps; step++) {
            if (cfg->collapse == 2) {
#pragma omp for collapse(2) schedule(runtime)
                for (i = 1; i < nx - 1; i++) {
                    for (j = 1; j < ny - 1; j++) {
                        int p = idx(i, j, ny);
                        double c = u[p];
                        double lap = u[p - ny] + u[p + ny] + u[p - 1] + u[p + 1] - 4.0 * c;
                        u_next[p] = c + alpha * lap;
                    }
                }
            } else {
#pragma omp for schedule(runtime)
                for (i = 1; i < nx - 1; i++) {
                    for (j = 1; j < ny - 1; j++) {
                        int p = idx(i, j, ny);
                        double c = u[p];
                        double lap = u[p - ny] + u[p + ny] + u[p - 1] + u[p + 1] - 4.0 * c;
                        u_next[p] = c + alpha * lap;
                    }
                }
            }

#pragma omp for schedule(static)
            for (j = 1; j < ny - 1; j++) {
                u_next[idx(0, j, ny)] = u_next[idx(1, j, ny)];
                u_next[idx(nx - 1, j, ny)] = u_next[idx(nx - 2, j, ny)];
            }
#pragma omp for schedule(static)
            for (i = 1; i < nx - 1; i++) {
                u_next[idx(i, 0, ny)] = u_next[idx(i, 1, ny)];
                u_next[idx(i, ny - 1, ny)] = u_next[idx(i, ny - 2, ny)];
            }
#pragma omp single
            {
                double *tmp;
                u_next[idx(0, 0, ny)] = u_next[idx(1, 1, ny)];
                u_next[idx(0, ny - 1, ny)] = u_next[idx(1, ny - 2, ny)];
                u_next[idx(nx - 1, 0, ny)] = u_next[idx(nx - 2, 1, ny)];
                u_next[idx(nx - 1, ny - 1, ny)] = u_next[idx(nx - 2, ny - 2, ny)];

                tmp = u;
                u = u_next;
                u_next = tmp;
            }
        }
    }

    *u_ptr = u;
    *u_next_ptr = u_next;
}

static Stats field_stats(const double *u, int nx, int ny) {
    int i;
    int n = nx * ny;
    Stats s;
    double acc = 0.0;
    s.min = u[0];
    s.max = u[0];
    s.sum = 0.0;

    for (i = 0; i < n; i++) {
        if (u[i] < s.min) s.min = u[i];
        if (u[i] > s.max) s.max = u[i];
        acc += u[i] * u[i];
        s.sum += u[i];
    }
    s.l2 = sqrt(acc);
    return s;
}

int main(int argc, char **argv) {
    Config cfg;
    double *u = NULL;
    double *u_next = NULL;
    int n_cells;
    double t0, t1;
    Stats initial, final;

    set_defaults(&cfg);
    if (!parse_args(argc, argv, &cfg) || !validate_config(&cfg)) {
        usage(argv[0]);
        return 1;
    }

    if (!is_stable(&cfg)) {
        fprintf(stderr, "Aviso: dt*nu=%.6f excede 0.25 para dx=dy=1.\n", cfg.dt * cfg.nu);
    }

    n_cells = cfg.nx * cfg.ny;
    u = (double *)malloc((size_t)n_cells * sizeof(double));
    u_next = (double *)malloc((size_t)n_cells * sizeof(double));
    if (!u || !u_next) {
        fprintf(stderr, "Erro: falha de alocacao para %d celulas.\n", n_cells);
        free(u);
        free(u_next);
        return 1;
    }

    init_field(u, &cfg);
    init_field(u_next, &cfg);
    initial = field_stats(u, cfg.nx, cfg.ny);

    t0 = omp_get_wtime();
    if (strcmp(cfg.mode, "seq") == 0) {
        simulate_seq(&u, &u_next, &cfg);
    } else if (strcmp(cfg.mode, "omp-basic") == 0) {
        simulate_omp_basic(&u, &u_next, &cfg);
    } else {
        simulate_omp_region(&u, &u_next, &cfg);
    }
    t1 = omp_get_wtime();

    final = field_stats(u, cfg.nx, cfg.ny);

    printf("CONFIG mode=%s nx=%d ny=%d steps=%d nu=%.8f dt=%.8f init=%s u0=%.8f schedule=%s chunk=%d collapse=%d threads=%d stable=%s\n",
           cfg.mode, cfg.nx, cfg.ny, cfg.steps, cfg.nu, cfg.dt, cfg.init, cfg.u0,
           cfg.schedule_name, cfg.chunk, cfg.collapse, omp_get_max_threads(),
           is_stable(&cfg) ? "yes" : "no");
    printf("INITIAL min=%.12f max=%.12f l2=%.12f sum=%.12f\n",
           initial.min, initial.max, initial.l2, initial.sum);
    printf("RESULT elapsed=%.9f min=%.12f max=%.12f l2=%.12f sum=%.12f\n",
           t1 - t0, final.min, final.max, final.l2, final.sum);

    free(u);
    free(u_next);
    return 0;
}
