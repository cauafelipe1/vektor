#include <stdio.h>
#include <stdlib.h>
#include "ast.h"

// global root populated by bison after parsing succeeds
ASTNode *ast_root = NULL;

// allocate and zero-initialize an ast node, aborting on out-of-memory
static ASTNode *ast_alloc_node(ASTNodeType type, int lineno) {
    ASTNode *node = calloc(1, sizeof(ASTNode));
    if (node == NULL) {
        fprintf(stderr, "[Vektor Fatal Error] Line %d: out of memory allocating ast node\n", lineno);
        exit(EXIT_FAILURE);
    }
    node->type = type;
    node->lineno = lineno;
    return node;
}

// construct a program root node holding a linked list of statements
ASTNode *ast_new_program(ASTNode *statements, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_PROGRAM, lineno);
    node->data.program.statements = statements;
    return node;
}

// construct an assignment statement node
ASTNode *ast_new_assign(ASTNode *target, ASTNode *value, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_ASSIGN, lineno);
    node->data.assign.target = target;
    node->data.assign.value = value;
    return node;
}

// construct an expression statement node
ASTNode *ast_new_expr_stmt(ASTNode *expr, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_EXPR_STMT, lineno);
    node->data.expr_stmt.expr = expr;
    return node;
}

// construct a binary operator expression node
ASTNode *ast_new_binop(ASTOp op, ASTNode *left, ASTNode *right, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_BINOP, lineno);
    node->data.binop.op = op;
    node->data.binop.left = left;
    node->data.binop.right = right;
    return node;
}

// construct a unary operator expression node
ASTNode *ast_new_unop(ASTOp op, ASTNode *operand, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_UNOP, lineno);
    node->data.unop.op = op;
    node->data.unop.operand = operand;
    return node;
}

// construct a function call expression node (takes ownership of callee)
ASTNode *ast_new_call(char *callee, ASTNode *args, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_CALL, lineno);
    node->data.call.callee = callee;
    node->data.call.args = args;
    return node;
}

// construct a vector literal expression node
ASTNode *ast_new_vector(ASTNode *elements, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_VECTOR, lineno);
    node->data.vector.elements = elements;
    return node;
}

// construct an attribute access node (takes ownership of attr_name)
ASTNode *ast_new_attr(ASTNode *object, char *attr_name, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_ATTR, lineno);
    node->data.attr.object = object;
    node->data.attr.attr_name = attr_name;
    return node;
}

// construct an index access node
ASTNode *ast_new_index(ASTNode *target, ASTNode *index, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_INDEX, lineno);
    node->data.index.target = target;
    node->data.index.index = index;
    return node;
}

// construct an identifier node (takes ownership of str_val)
ASTNode *ast_new_id(char *str_val, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_ID, lineno);
    node->data.literal.str_val = str_val;
    return node;
}

// construct a numeric literal node (takes ownership of str_val)
ASTNode *ast_new_num(char *str_val, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_NUM, lineno);
    node->data.literal.str_val = str_val;
    return node;
}

// construct a string literal node (takes ownership of str_val)
ASTNode *ast_new_str(char *str_val, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_STR, lineno);
    node->data.literal.str_val = str_val;
    return node;
}

// construct a boolean literal node
ASTNode *ast_new_bool(int bool_val, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_BOOL, lineno);
    node->data.boolean.bool_val = bool_val;
    return node;
}

// construct an explicitly parenthesized expression node
ASTNode *ast_new_paren(ASTNode *expr, int lineno) {
    ASTNode *node = ast_alloc_node(NODE_PAREN, lineno);
    node->data.paren.expr = expr;
    return node;
}

// append an item node to the tail of a sibling linked list
ASTNode *ast_append_node(ASTNode *list, ASTNode *item) {
    if (item == NULL) {
        return list;
    }
    if (list == NULL) {
        return item;
    }
    ASTNode *curr = list;
    while (curr->next != NULL) {
        curr = curr->next;
    }
    curr->next = item;
    return list;
}

// map an ast operator enum to its printable symbol
static const char *ast_op_str(ASTOp op) {
    switch (op) {
        case OP_ADD:
            return "+";
        case OP_SUB:
            return "-";
        case OP_MUL:
            return "*";
        case OP_DIV:
            return "/";
        case OP_POW:
            return "**";
        case OP_LT:
            return "<";
        case OP_GT:
            return ">";
        case OP_LE:
            return "<=";
        case OP_GE:
            return ">=";
        case OP_EQ:
            return "==";
        case OP_NE:
            return "!=";
        case OP_NEG:
            return "-";
    }
    return "?";
}

// write two spaces per indentation depth level
static void ast_print_indent(int indent) {
    for (int i = 0; i < indent; i++) {
        fputs("  ", stdout);
    }
}

// recursively print an ast node and its sibling chain to stdout
void ast_dump(const ASTNode *node, int indent) {
    while (node != NULL) {
        ast_print_indent(indent);
        switch (node->type) {
            case NODE_PROGRAM:
                printf("PROGRAM\n");
                ast_dump(node->data.program.statements, indent + 1);
                break;
            case NODE_ASSIGN:
                printf("ASSIGN (line %d)\n", node->lineno);
                ast_dump(node->data.assign.target, indent + 1);
                ast_dump(node->data.assign.value, indent + 1);
                break;
            case NODE_EXPR_STMT:
                printf("EXPR_STMT (line %d)\n", node->lineno);
                ast_dump(node->data.expr_stmt.expr, indent + 1);
                break;
            case NODE_BINOP:
                printf("BINOP(%s)\n", ast_op_str(node->data.binop.op));
                ast_dump(node->data.binop.left, indent + 1);
                ast_dump(node->data.binop.right, indent + 1);
                break;
            case NODE_UNOP:
                printf("UNOP(%s)\n", ast_op_str(node->data.unop.op));
                ast_dump(node->data.unop.operand, indent + 1);
                break;
            case NODE_CALL:
                printf("CALL(%s)\n", node->data.call.callee != NULL ? node->data.call.callee : "");
                ast_dump(node->data.call.args, indent + 1);
                break;
            case NODE_VECTOR:
                printf("VECTOR\n");
                ast_dump(node->data.vector.elements, indent + 1);
                break;
            case NODE_ATTR:
                printf("ATTR(.%s)\n", node->data.attr.attr_name != NULL ? node->data.attr.attr_name : "");
                ast_dump(node->data.attr.object, indent + 1);
                break;
            case NODE_INDEX:
                printf("INDEX\n");
                ast_dump(node->data.index.target, indent + 1);
                ast_dump(node->data.index.index, indent + 1);
                break;
            case NODE_ID:
                printf("ID(%s)\n", node->data.literal.str_val != NULL ? node->data.literal.str_val : "");
                break;
            case NODE_NUM:
                printf("NUM(%s)\n", node->data.literal.str_val != NULL ? node->data.literal.str_val : "");
                break;
            case NODE_STR:
                printf("STR(%s)\n", node->data.literal.str_val != NULL ? node->data.literal.str_val : "");
                break;
            case NODE_BOOL:
                printf("BOOL(%s)\n", node->data.boolean.bool_val ? "true" : "false");
                break;
            case NODE_PAREN:
                printf("PAREN\n");
                ast_dump(node->data.paren.expr, indent + 1);
                break;
        }
        node = node->next;
    }
}

// recursively free an ast node and its sibling chain iteratively
void ast_free(ASTNode *node) {
    while (node != NULL) {
        ASTNode *next = node->next;
        switch (node->type) {
            case NODE_PROGRAM:
                ast_free(node->data.program.statements);
                break;
            case NODE_ASSIGN:
                ast_free(node->data.assign.target);
                ast_free(node->data.assign.value);
                break;
            case NODE_EXPR_STMT:
                ast_free(node->data.expr_stmt.expr);
                break;
            case NODE_BINOP:
                ast_free(node->data.binop.left);
                ast_free(node->data.binop.right);
                break;
            case NODE_UNOP:
                ast_free(node->data.unop.operand);
                break;
            case NODE_CALL:
                free(node->data.call.callee);
                ast_free(node->data.call.args);
                break;
            case NODE_VECTOR:
                ast_free(node->data.vector.elements);
                break;
            case NODE_ATTR:
                ast_free(node->data.attr.object);
                free(node->data.attr.attr_name);
                break;
            case NODE_INDEX:
                ast_free(node->data.index.target);
                ast_free(node->data.index.index);
                break;
            case NODE_ID:
            case NODE_NUM:
            case NODE_STR:
                free(node->data.literal.str_val);
                break;
            case NODE_BOOL:
                break;
            case NODE_PAREN:
                ast_free(node->data.paren.expr);
                break;
        }
        free(node);
        node = next;
    }
}
