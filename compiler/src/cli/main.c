#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include "ast.h"
#include "codegen.h"

// flex and bison external entry points
extern FILE *yyin;
extern int yyparse(void);
extern int yylex_destroy(void);

// print command-line usage instructions
static void print_usage(FILE *stream, const char *prog_name) {
    fprintf(
        stream,
        "usage: %s [--emit-only] [--dump-ast] [-o <output.py>] [-h|--help] <input.vk>\n",
        prog_name
    );
}

// build default output path "output/<stem>.py" from an input file path
static char *build_default_output_path(const char *input_path) {
    const char *slash = strrchr(input_path, '/');
    const char *base = slash != NULL ? slash + 1 : input_path;
    size_t base_len = strlen(base);

    // strip trailing .vk extension when present
    if (base_len > 3 && strcmp(base + base_len - 3, ".vk") == 0) {
        base_len -= 3;
    }

    const char *stem = base;
    size_t stem_len = base_len;
    if (stem_len == 0) {
        stem = "out";
        stem_len = 3;
    }

    const char *prefix = "output/";
    const char *suffix = ".py";
    size_t total_len = strlen(prefix) + stem_len + strlen(suffix) + 1;
    char *path = malloc(total_len);
    if (path == NULL) {
        fprintf(stderr, "[Vektor Fatal Error] out of memory building output path\n");
        return NULL;
    }

    memcpy(path, prefix, strlen(prefix));
    memcpy(path + strlen(prefix), stem, stem_len);
    memcpy(path + strlen(prefix) + stem_len, suffix, strlen(suffix) + 1);
    return path;
}

// invoke uv run python <output_path> via fork and execvp without a shell
static int run_generated_script(char *output_path) {
    char *exec_argv[] = {"uv", "run", "python", output_path, NULL};
    pid_t pid = fork();
    if (pid < 0) {
        fprintf(stderr, "[Vektor Runtime Error] fork failed: %s\n", strerror(errno));
        return 1;
    }
    if (pid == 0) {
        execvp("uv", exec_argv);
        fprintf(stderr, "[Vektor Runtime Error] failed to execute uv: %s\n", strerror(errno));
        _exit(127);
    }

    int status = 0;
    pid_t waited;
    do {
        waited = waitpid(pid, &status, 0);
    } while (waited < 0 && errno == EINTR);

    if (waited < 0) {
        fprintf(stderr, "[Vektor Runtime Error] waitpid failed: %s\n", strerror(errno));
        return 1;
    }

    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}

// parse cli arguments, transpile input .vk to python, and optionally execute it
int main(int argc, char **argv) {
    int emit_only = 0;
    int dump_ast = 0;
    char *output_path = NULL;
    char *allocated_output = NULL;
    const char *input_path = NULL;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(stdout, argv[0]);
            return 0;
        }
        if (strcmp(argv[i], "--emit-only") == 0) {
            emit_only = 1;
            continue;
        }
        if (strcmp(argv[i], "--dump-ast") == 0) {
            dump_ast = 1;
            continue;
        }
        if (strcmp(argv[i], "-o") == 0) {
            if (i + 1 >= argc || argv[i + 1][0] == '\0') {
                fprintf(stderr, "[Vektor CLI Error] missing output path after -o\n");
                print_usage(stderr, argv[0]);
                return 1;
            }
            output_path = argv[++i];
            continue;
        }
        if (argv[i][0] == '-') {
            fprintf(stderr, "[Vektor CLI Error] unrecognized option '%s'\n", argv[i]);
            print_usage(stderr, argv[0]);
            return 1;
        }
        if (input_path != NULL) {
            fprintf(stderr, "[Vektor CLI Error] unexpected extra input file '%s'\n", argv[i]);
            print_usage(stderr, argv[0]);
            return 1;
        }
        input_path = argv[i];
    }

    if (input_path == NULL) {
        fprintf(stderr, "[Vektor CLI Error] missing input .vk file\n");
        print_usage(stderr, argv[0]);
        return 1;
    }

    // open input stream directly without stat/fseek so process substitution works
    FILE *input_file = fopen(input_path, "r");
    if (input_file == NULL) {
        fprintf(stderr, "[Vektor IO Error] cannot open input file '%s': %s\n", input_path, strerror(errno));
        return 1;
    }

    ast_root = NULL;
    yyin = input_file;
    int parse_status = yyparse();
    fclose(input_file);
    yyin = NULL;

    // abort cleanly before creating or truncating any output file on parse error
    if (parse_status != 0 || ast_root == NULL) {
        ast_free(ast_root);
        ast_root = NULL;
        yylex_destroy();
        return 1;
    }

    if (dump_ast) {
        ast_dump(ast_root, 0);
        // exit cleanly after dumping ast unless python output emission was also requested
        if (!emit_only && output_path == NULL) {
            ast_free(ast_root);
            ast_root = NULL;
            yylex_destroy();
            return 0;
        }
    }

    if (output_path == NULL) {
        if (mkdir("output", 0755) != 0 && errno != EEXIST) {
            fprintf(stderr, "[Vektor IO Error] cannot create output directory 'output': %s\n", strerror(errno));
            ast_free(ast_root);
            ast_root = NULL;
            yylex_destroy();
            return 1;
        }
        allocated_output = build_default_output_path(input_path);
        if (allocated_output == NULL) {
            ast_free(ast_root);
            ast_root = NULL;
            yylex_destroy();
            return 1;
        }
        output_path = allocated_output;
    }

    FILE *output_file = fopen(output_path, "w");
    if (output_file == NULL) {
        fprintf(stderr, "[Vektor IO Error] cannot open output file '%s': %s\n", output_path, strerror(errno));
        ast_free(ast_root);
        ast_root = NULL;
        yylex_destroy();
        free(allocated_output);
        return 1;
    }

    int emit_status = codegen_emit_python(ast_root, output_file);
    int close_status = fclose(output_file);
    ast_free(ast_root);
    ast_root = NULL;
    yylex_destroy();

    if (emit_status != 0 || close_status != 0) {
        fprintf(stderr, "[Vektor Codegen Error] failed writing python output to '%s'\n", output_path);
        free(allocated_output);
        return 1;
    }

    if (emit_only) {
        free(allocated_output);
        return 0;
    }

    int run_status = run_generated_script(output_path);
    free(allocated_output);
    return run_status;
}
