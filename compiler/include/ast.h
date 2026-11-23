#ifndef VEKTOR_AST_H
#define VEKTOR_AST_H

// represent ast node categories for the vektor grammar
typedef enum {
    NODE_PROGRAM,
    NODE_ASSIGN,
    NODE_EXPR_STMT,
    NODE_BINOP,
    NODE_UNOP,
    NODE_CALL,
    NODE_VECTOR,
    NODE_ATTR,
    NODE_INDEX,
    NODE_ID,
    NODE_NUM,
    NODE_STR,
    NODE_BOOL,
    NODE_PAREN
} ASTNodeType;

// represent binary and unary operator kinds
typedef enum {
    OP_ADD,
    OP_SUB,
    OP_MUL,
    OP_DIV,
    OP_POW,
    OP_LT,
    OP_GT,
    OP_LE,
    OP_GE,
    OP_EQ,
    OP_NE,
    OP_NEG
} ASTOp;

// represent a node in the vektor abstract syntax tree
typedef struct ASTNode {
    ASTNodeType type;
    int lineno;
    struct ASTNode *next;
    union {
        struct {
            struct ASTNode *statements;
        } program;
        struct {
            struct ASTNode *target;
            struct ASTNode *value;
        } assign;
        struct {
            struct ASTNode *expr;
        } expr_stmt;
        struct {
            ASTOp op;
            struct ASTNode *left;
            struct ASTNode *right;
        } binop;
        struct {
            ASTOp op;
            struct ASTNode *operand;
        } unop;
        struct {
            char *callee;
            struct ASTNode *args;
        } call;
        struct {
            struct ASTNode *elements;
        } vector;
        struct {
            struct ASTNode *object;
            char *attr_name;
        } attr;
        struct {
            struct ASTNode *target;
            struct ASTNode *index;
        } index;
        struct {
            char *str_val;
        } literal;
        struct {
            int bool_val;
        } boolean;
        struct {
            struct ASTNode *expr;
        } paren;
    } data;
} ASTNode;

// global root populated by bison after parsing succeeds
extern ASTNode *ast_root;

// ast node constructors (take ownership of heap strings)
ASTNode *ast_new_program(ASTNode *statements, int lineno);
ASTNode *ast_new_assign(ASTNode *target, ASTNode *value, int lineno);
ASTNode *ast_new_expr_stmt(ASTNode *expr, int lineno);
ASTNode *ast_new_binop(ASTOp op, ASTNode *left, ASTNode *right, int lineno);
ASTNode *ast_new_unop(ASTOp op, ASTNode *operand, int lineno);
ASTNode *ast_new_call(char *callee, ASTNode *args, int lineno);
ASTNode *ast_new_vector(ASTNode *elements, int lineno);
ASTNode *ast_new_attr(ASTNode *object, char *attr_name, int lineno);
ASTNode *ast_new_index(ASTNode *target, ASTNode *index, int lineno);
ASTNode *ast_new_id(char *str_val, int lineno);
ASTNode *ast_new_num(char *str_val, int lineno);
ASTNode *ast_new_str(char *str_val, int lineno);
ASTNode *ast_new_bool(int bool_val, int lineno);
ASTNode *ast_new_paren(ASTNode *expr, int lineno);

// list, debug printing, and memory management helpers
ASTNode *ast_append_node(ASTNode *list, ASTNode *item);
void ast_dump(const ASTNode *node, int indent);
int ast_dump_json(const ASTNode *node, FILE *out);
void ast_free(ASTNode *node);

#endif
