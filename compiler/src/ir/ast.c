#include <stdio.h>
#include <stdlib.h>
#include <string.h>
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

// write a json string with escaped quotes and control characters
static int ast_json_write_string(FILE *out, const char *text) {
    if (fputc('"', out) == EOF) {
        return -1;
    }
    if (text != NULL) {
        for (const unsigned char *p = (const unsigned char *)text; *p != '\0'; p++) {
            unsigned char c = *p;
            if (c == '"' || c == '\\') {
                if (fputc('\\', out) == EOF || fputc((int)c, out) == EOF) {
                    return -1;
                }
            } else if (c == '\n') {
                if (fputs("\\n", out) == EOF) {
                    return -1;
                }
            } else if (c == '\r') {
                if (fputs("\\r", out) == EOF) {
                    return -1;
                }
            } else if (c == '\t') {
                if (fputs("\\t", out) == EOF) {
                    return -1;
                }
            } else if (c < 0x20) {
                if (fprintf(out, "\\u%04x", c) < 0) {
                    return -1;
                }
            } else if (fputc((int)c, out) == EOF) {
                return -1;
            }
        }
    }
    if (fputc('"', out) == EOF) {
        return -1;
    }
    return 0;
}

// map an ast node type to a stable json type name
static const char *ast_type_name(ASTNodeType type) {
    switch (type) {
        case NODE_PROGRAM:
            return "PROGRAM";
        case NODE_ASSIGN:
            return "ASSIGN";
        case NODE_EXPR_STMT:
            return "EXPR_STMT";
        case NODE_BINOP:
            return "BINOP";
        case NODE_UNOP:
            return "UNOP";
        case NODE_CALL:
            return "CALL";
        case NODE_VECTOR:
            return "VECTOR";
        case NODE_ATTR:
            return "ATTR";
        case NODE_INDEX:
            return "INDEX";
        case NODE_ID:
            return "ID";
        case NODE_NUM:
            return "NUM";
        case NODE_STR:
            return "STR";
        case NODE_BOOL:
            return "BOOL";
        case NODE_PAREN:
            return "PAREN";
    }
    return "UNKNOWN";
}

// build the display label for one node (matches textual ast_dump style)
static void ast_format_label(const ASTNode *node, char *buf, size_t buf_size) {
    switch (node->type) {
        case NODE_PROGRAM:
            snprintf(buf, buf_size, "PROGRAM");
            break;
        case NODE_ASSIGN:
            snprintf(buf, buf_size, "ASSIGN");
            break;
        case NODE_EXPR_STMT:
            snprintf(buf, buf_size, "EXPR_STMT");
            break;
        case NODE_BINOP:
            snprintf(buf, buf_size, "BINOP(%s)", ast_op_str(node->data.binop.op));
            break;
        case NODE_UNOP:
            snprintf(buf, buf_size, "UNOP(%s)", ast_op_str(node->data.unop.op));
            break;
        case NODE_CALL:
            snprintf(
                buf,
                buf_size,
                "CALL(%s)",
                node->data.call.callee != NULL ? node->data.call.callee : ""
            );
            break;
        case NODE_VECTOR:
            snprintf(buf, buf_size, "VECTOR");
            break;
        case NODE_ATTR:
            snprintf(
                buf,
                buf_size,
                "ATTR(.%s)",
                node->data.attr.attr_name != NULL ? node->data.attr.attr_name : ""
            );
            break;
        case NODE_INDEX:
            snprintf(buf, buf_size, "INDEX");
            break;
        case NODE_ID:
            snprintf(
                buf,
                buf_size,
                "ID(%s)",
                node->data.literal.str_val != NULL ? node->data.literal.str_val : ""
            );
            break;
        case NODE_NUM:
            snprintf(
                buf,
                buf_size,
                "NUM(%s)",
                node->data.literal.str_val != NULL ? node->data.literal.str_val : ""
            );
            break;
        case NODE_STR:
            snprintf(
                buf,
                buf_size,
                "STR(%s)",
                node->data.literal.str_val != NULL ? node->data.literal.str_val : ""
            );
            break;
        case NODE_BOOL:
            snprintf(buf, buf_size, "BOOL(%s)", node->data.boolean.bool_val ? "true" : "false");
            break;
        case NODE_PAREN:
            snprintf(buf, buf_size, "PAREN");
            break;
    }
}

static int ast_dump_json_node(const ASTNode *node, FILE *out);
static int ast_dump_json_siblings(const ASTNode *node, FILE *out);

// write a sibling-linked list as a json array of node objects
static int ast_dump_json_siblings(const ASTNode *node, FILE *out) {
    if (fputc('[', out) == EOF) {
        return -1;
    }
    int first = 1;
    while (node != NULL) {
        if (!first && fputc(',', out) == EOF) {
            return -1;
        }
        first = 0;
        if (ast_dump_json_node(node, out) != 0) {
            return -1;
        }
        node = node->next;
    }
    if (fputc(']', out) == EOF) {
        return -1;
    }
    return 0;
}

// write one ast node object; sibling chain is handled by the caller
static int ast_dump_json_node(const ASTNode *node, FILE *out) {
    char label[512];
    ast_format_label(node, label, sizeof(label));

    if (fputc('{', out) == EOF) {
        return -1;
    }
    if (fputs("\"type\":", out) == EOF || ast_json_write_string(out, ast_type_name(node->type)) != 0) {
        return -1;
    }
    if (fputs(",\"label\":", out) == EOF || ast_json_write_string(out, label) != 0) {
        return -1;
    }
    if (fprintf(out, ",\"lineno\":%d,\"children\":", node->lineno) < 0) {
        return -1;
    }

    switch (node->type) {
        case NODE_PROGRAM:
            if (ast_dump_json_siblings(node->data.program.statements, out) != 0) {
                return -1;
            }
            break;
        case NODE_ASSIGN:
            if (fputc('[', out) == EOF) {
                return -1;
            }
            if (node->data.assign.target != NULL) {
                if (ast_dump_json_node(node->data.assign.target, out) != 0) {
                    return -1;
                }
            }
            if (fputc(',', out) == EOF) {
                return -1;
            }
            if (node->data.assign.value != NULL) {
                if (ast_dump_json_node(node->data.assign.value, out) != 0) {
                    return -1;
                }
            }
            if (fputc(']', out) == EOF) {
                return -1;
            }
            break;
        case NODE_EXPR_STMT:
            if (ast_dump_json_siblings(node->data.expr_stmt.expr, out) != 0) {
                return -1;
            }
            break;
        case NODE_BINOP:
            if (fputc('[', out) == EOF) {
                return -1;
            }
            if (node->data.binop.left != NULL && ast_dump_json_node(node->data.binop.left, out) != 0) {
                return -1;
            }
            if (fputc(',', out) == EOF) {
                return -1;
            }
            if (node->data.binop.right != NULL && ast_dump_json_node(node->data.binop.right, out) != 0) {
                return -1;
            }
            if (fputc(']', out) == EOF) {
                return -1;
            }
            break;
        case NODE_UNOP:
            if (ast_dump_json_siblings(node->data.unop.operand, out) != 0) {
                return -1;
            }
            break;
        case NODE_CALL:
            if (ast_dump_json_siblings(node->data.call.args, out) != 0) {
                return -1;
            }
            break;
        case NODE_VECTOR:
            if (ast_dump_json_siblings(node->data.vector.elements, out) != 0) {
                return -1;
            }
            break;
        case NODE_ATTR:
            if (ast_dump_json_siblings(node->data.attr.object, out) != 0) {
                return -1;
            }
            break;
        case NODE_INDEX:
            if (fputc('[', out) == EOF) {
                return -1;
            }
            if (node->data.index.target != NULL && ast_dump_json_node(node->data.index.target, out) != 0) {
                return -1;
            }
            if (fputc(',', out) == EOF) {
                return -1;
            }
            if (node->data.index.index != NULL && ast_dump_json_node(node->data.index.index, out) != 0) {
                return -1;
            }
            if (fputc(']', out) == EOF) {
                return -1;
            }
            break;
        case NODE_PAREN:
            if (ast_dump_json_siblings(node->data.paren.expr, out) != 0) {
                return -1;
            }
            break;
        case NODE_ID:
        case NODE_NUM:
        case NODE_STR:
        case NODE_BOOL:
            if (fputs("[]", out) == EOF) {
                return -1;
            }
            break;
    }

    if (fputc('}', out) == EOF) {
        return -1;
    }
    return 0;
}

// serialize one ast root (and its nested children) as a single json object
int ast_dump_json(const ASTNode *node, FILE *out) {
    if (node == NULL || out == NULL) {
        return -1;
    }
    if (ast_dump_json_node(node, out) != 0) {
        return -1;
    }
    if (fputc('\n', out) == EOF) {
        return -1;
    }
    return 0;
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
