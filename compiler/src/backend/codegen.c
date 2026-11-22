#include <stdio.h>
#include "codegen.h"

// mandatory runtime import header and implicit simulation instance
static const char *const VEKTOR_PY_HEADER =
    "from library import Simulation, planet, star, satellite, particle_group, rings, orbit, random, simulate\n"
    "\n"
    "sim = Simulation()\n";

// return operator precedence matching the vektor grammar and python
static int codegen_op_precedence(ASTOp op) {
    switch (op) {
        case OP_LT:
        case OP_GT:
        case OP_LE:
        case OP_GE:
        case OP_EQ:
        case OP_NE:
            return 1;
        case OP_ADD:
        case OP_SUB:
            return 2;
        case OP_MUL:
        case OP_DIV:
            return 3;
        case OP_NEG:
            return 4;
        case OP_POW:
            return 5;
    }
    return 0;
}

// map binary ast operator to its target python operator string
static const char *codegen_binop_str(ASTOp op) {
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
    return "";
}

// determine whether a left child of a binary operator requires parentheses
static int codegen_needs_left_parens(ASTOp parent_op, const ASTNode *left) {
    if (left == NULL) {
        return 0;
    }
    if (parent_op == OP_POW && left->type == NODE_UNOP) {
        return 1;
    }
    if (left->type != NODE_BINOP) {
        return 0;
    }
    int parent_prec = codegen_op_precedence(parent_op);
    int left_prec = codegen_op_precedence(left->data.binop.op);
    if (left_prec < parent_prec) {
        return 1;
    }
    if (left_prec == parent_prec) {
        // wrap right-associative power or relational left child to preserve ast grouping
        if (parent_op == OP_POW || parent_prec == 1) {
            return 1;
        }
    }
    return 0;
}

// determine whether a right child of a binary operator requires parentheses
static int codegen_needs_right_parens(ASTOp parent_op, const ASTNode *right) {
    if (right == NULL || right->type != NODE_BINOP) {
        return 0;
    }
    int parent_prec = codegen_op_precedence(parent_op);
    int right_prec = codegen_op_precedence(right->data.binop.op);
    if (right_prec < parent_prec) {
        return 1;
    }
    if (right_prec == parent_prec) {
        // prevent chained comparisons in python when nesting relational operators
        if (parent_prec == 1) {
            return 1;
        }
        // wrap right-side same-precedence child for non-associative or mixed left-assoc ops
        if (parent_op == OP_SUB || parent_op == OP_DIV ||
            (parent_op != OP_POW && right->data.binop.op != parent_op)) {
            return 1;
        }
    }
    return 0;
}

// forward declaration for mutually recursive expression emission
static int codegen_emit_expr(const ASTNode *node, FILE *out);

// emit a comma-separated list of expression nodes
static int codegen_emit_expr_list(const ASTNode *head, FILE *out) {
    const ASTNode *curr = head;
    while (curr != NULL) {
        if (codegen_emit_expr(curr, out) != 0) {
            return -1;
        }
        if (curr->next != NULL) {
            if (fputs(", ", out) == EOF) {
                return -1;
            }
        }
        curr = curr->next;
    }
    return 0;
}

// emit any expression ast node as valid python 3 syntax
static int codegen_emit_expr(const ASTNode *node, FILE *out) {
    if (node == NULL) {
        return -1;
    }

    switch (node->type) {
        case NODE_ID:
        case NODE_NUM:
        case NODE_STR:
            if (node->data.literal.str_val == NULL) {
                return -1;
            }
            return fputs(node->data.literal.str_val, out) == EOF ? -1 : 0;

        case NODE_BOOL:
            return fputs(node->data.boolean.bool_val ? "True" : "False", out) == EOF ? -1 : 0;

        case NODE_ATTR:
            if (codegen_emit_expr(node->data.attr.object, out) != 0) {
                return -1;
            }
            if (node->data.attr.attr_name == NULL) {
                return -1;
            }
            return fprintf(out, ".%s", node->data.attr.attr_name) < 0 ? -1 : 0;

        case NODE_INDEX:
            // emit native 0-based index directly without offset conversion
            if (codegen_emit_expr(node->data.index.target, out) != 0) {
                return -1;
            }
            if (fputc('[', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(node->data.index.index, out) != 0) {
                return -1;
            }
            return fputc(']', out) == EOF ? -1 : 0;

        case NODE_CALL:
            if (node->data.call.callee == NULL) {
                return -1;
            }
            if (fprintf(out, "%s(", node->data.call.callee) < 0) {
                return -1;
            }
            if (codegen_emit_expr_list(node->data.call.args, out) != 0) {
                return -1;
            }
            return fputc(')', out) == EOF ? -1 : 0;

        case NODE_VECTOR:
            if (fputc('[', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr_list(node->data.vector.elements, out) != 0) {
                return -1;
            }
            return fputc(']', out) == EOF ? -1 : 0;

        case NODE_PAREN:
            if (fputc('(', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(node->data.paren.expr, out) != 0) {
                return -1;
            }
            return fputc(')', out) == EOF ? -1 : 0;

        case NODE_UNOP: {
            const ASTNode *operand = node->data.unop.operand;
            int wrap = 0;
            if (operand != NULL) {
                if (operand->type == NODE_UNOP) {
                    wrap = 1;
                } else if (operand->type == NODE_BINOP && operand->data.binop.op != OP_POW) {
                    wrap = 1;
                }
            }
            if (fputc('-', out) == EOF) {
                return -1;
            }
            if (wrap && fputc('(', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(operand, out) != 0) {
                return -1;
            }
            if (wrap && fputc(')', out) == EOF) {
                return -1;
            }
            return 0;
        }

        case NODE_BINOP: {
            ASTOp op = node->data.binop.op;
            const ASTNode *left = node->data.binop.left;
            const ASTNode *right = node->data.binop.right;
            int wrap_left = codegen_needs_left_parens(op, left);
            int wrap_right = codegen_needs_right_parens(op, right);

            if (wrap_left && fputc('(', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(left, out) != 0) {
                return -1;
            }
            if (wrap_left && fputc(')', out) == EOF) {
                return -1;
            }

            if (fprintf(out, " %s ", codegen_binop_str(op)) < 0) {
                return -1;
            }

            if (wrap_right && fputc('(', out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(right, out) != 0) {
                return -1;
            }
            if (wrap_right && fputc(')', out) == EOF) {
                return -1;
            }
            return 0;
        }

        case NODE_PROGRAM:
        case NODE_ASSIGN:
        case NODE_EXPR_STMT:
            return -1;
    }

    return -1;
}

// emit a single top-level statement followed by a newline
static int codegen_emit_stmt(const ASTNode *stmt, FILE *out) {
    if (stmt == NULL) {
        return -1;
    }

    switch (stmt->type) {
        case NODE_ASSIGN:
            if (codegen_emit_expr(stmt->data.assign.target, out) != 0) {
                return -1;
            }
            if (fputs(" = ", out) == EOF) {
                return -1;
            }
            if (codegen_emit_expr(stmt->data.assign.value, out) != 0) {
                return -1;
            }
            return fputc('\n', out) == EOF ? -1 : 0;

        case NODE_EXPR_STMT:
            if (codegen_emit_expr(stmt->data.expr_stmt.expr, out) != 0) {
                return -1;
            }
            return fputc('\n', out) == EOF ? -1 : 0;

        default:
            return -1;
    }
}

// emit python 3 source code from the parsed ast into out
int codegen_emit_python(const ASTNode *root, FILE *out) {
    if (root == NULL || out == NULL || root->type != NODE_PROGRAM) {
        return -1;
    }

    if (fputs(VEKTOR_PY_HEADER, out) == EOF) {
        return -1;
    }

    const ASTNode *stmt = root->data.program.statements;
    while (stmt != NULL) {
        if (codegen_emit_stmt(stmt, out) != 0) {
            return -1;
        }
        stmt = stmt->next;
    }

    return ferror(out) != 0 ? -1 : 0;
}
