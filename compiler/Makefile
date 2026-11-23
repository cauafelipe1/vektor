# build configuration for the vektor c11 transpiler
CC = gcc
CFLAGS = -Wall -Wextra -Werror -std=c11 -g -D_POSIX_C_SOURCE=200809L -Iinclude -Ibuild
FLEX = flex
BISON = bison
BUILD_DIR = build
TARGET = vektor

OBJS = $(BUILD_DIR)/parser.tab.o $(BUILD_DIR)/lex.yy.o $(BUILD_DIR)/ast.o $(BUILD_DIR)/codegen.o $(BUILD_DIR)/main.o

.PHONY: all clean test

# default target builds the vektor compiler binary
all: $(TARGET)

# link all compiler object files into the vektor binary
$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS)

# generate bison parser source and header with counterexample diagnostics
$(BUILD_DIR)/parser.tab.c $(BUILD_DIR)/parser.tab.h &: src/frontend/parser.y include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(BISON) -d -Wcounterexamples -o $(BUILD_DIR)/parser.tab.c src/frontend/parser.y

# generate flex lexer source after parser token header exists
$(BUILD_DIR)/lex.yy.c: src/frontend/lexer.l $(BUILD_DIR)/parser.tab.h include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(FLEX) -o $(BUILD_DIR)/lex.yy.c src/frontend/lexer.l

# compile bison-generated parser with strict warnings
$(BUILD_DIR)/parser.tab.o: $(BUILD_DIR)/parser.tab.c include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $(BUILD_DIR)/parser.tab.c -o $(BUILD_DIR)/parser.tab.o

# compile flex-generated lexer relaxing only sign-compare for flex 2.6.4 + gcc 15
$(BUILD_DIR)/lex.yy.o: $(BUILD_DIR)/lex.yy.c $(BUILD_DIR)/parser.tab.h include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -Wno-sign-compare -c $(BUILD_DIR)/lex.yy.c -o $(BUILD_DIR)/lex.yy.o

# compile ast implementation
$(BUILD_DIR)/ast.o: src/ir/ast.c include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c src/ir/ast.c -o $(BUILD_DIR)/ast.o

# compile python code generator
$(BUILD_DIR)/codegen.o: src/backend/codegen.c include/codegen.h include/ast.h
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c src/backend/codegen.c -o $(BUILD_DIR)/codegen.o

# compile cli driver
$(BUILD_DIR)/main.o: src/cli/main.c include/ast.h include/codegen.h
	@mkdir -p $(BUILD_DIR)
	$(CC) $(CFLAGS) -c src/cli/main.c -o $(BUILD_DIR)/main.o

# remove compiled binary and build directory artifacts
clean:
	rm -rf $(TARGET) $(BUILD_DIR)

# run smoke ast text dump and transpilation check when reference example is present
test: $(TARGET)
	@if [ -f ../examples/solar_system.vk ]; then \
		./$(TARGET) --dump-ast-text ../examples/solar_system.vk > /dev/null && \
		./$(TARGET) --emit-only -o /tmp/vektor_smoke.py ../examples/solar_system.vk && \
		rm -f /tmp/vektor_smoke.py; \
	fi
