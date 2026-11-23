%code requires {
#include "ast.h"
}

%{
#include <stdio.h>
#include <stdlib.h>
#include "ast.h"

extern int yylex(void);
extern int yylineno;
void yyerror(const char *s);
%}

%define parse.error verbose

%union {
    ASTNode *node;
    char *str_val;
    int bool_val;
}

%token <str_val> ID NUM STR
%token <bool_val> BOOL
%token LE GE EQ NE

%type <node> PROGRAM STMT_LIST STMT ASSIGN TARGET EXPR PRIMARY CALL VECTOR OPT_ARGS ARG_LIST

/* on parse error, free stranded lexemes / partial AST; omit PROGRAM to avoid double-free with ast_root */
%destructor { free($$); } ID NUM STR
%destructor { ast_free($$); } STMT_LIST STMT ASSIGN TARGET EXPR PRIMARY CALL VECTOR OPT_ARGS ARG_LIST

%left '<' '>' LE GE EQ NE
%left '+' '-'
%left '*' '/'
/* UMINUS is not a token: precedence label so unary '-' binds tighter than binary '-' */
%right UMINUS
%right '^'

%%

PROGRAM
    : STMT_LIST {
        ast_root = ast_new_program($1, yylineno);
        $$ = ast_root;
    }
    ;

STMT_LIST
    : /* empty */ { $$ = NULL; }
    | STMT_LIST STMT { $$ = ast_append_node($1, $2); }
    ;

STMT
    : ASSIGN ';' { $$ = $1; }
    | EXPR ';' { $$ = ast_new_expr_stmt($1, yylineno); }
    ;

ASSIGN
    : TARGET '=' EXPR { $$ = ast_new_assign($1, $3, yylineno); }
    ;

TARGET
    : ID { $$ = ast_new_id($1, yylineno); }
    | TARGET '.' ID { $$ = ast_new_attr($1, $3, yylineno); }
    | TARGET '[' EXPR ']' { $$ = ast_new_index($1, $3, yylineno); }
    ;

EXPR
    : EXPR '+' EXPR { $$ = ast_new_binop(OP_ADD, $1, $3, yylineno); }
    | EXPR '-' EXPR { $$ = ast_new_binop(OP_SUB, $1, $3, yylineno); }
    | EXPR '*' EXPR { $$ = ast_new_binop(OP_MUL, $1, $3, yylineno); }
    | EXPR '/' EXPR { $$ = ast_new_binop(OP_DIV, $1, $3, yylineno); }
    | EXPR '^' EXPR { $$ = ast_new_binop(OP_POW, $1, $3, yylineno); }
    | EXPR '>' EXPR { $$ = ast_new_binop(OP_GT, $1, $3, yylineno); }
    | EXPR '<' EXPR { $$ = ast_new_binop(OP_LT, $1, $3, yylineno); }
    | EXPR LE EXPR { $$ = ast_new_binop(OP_LE, $1, $3, yylineno); }
    | EXPR GE EXPR { $$ = ast_new_binop(OP_GE, $1, $3, yylineno); }
    | EXPR EQ EXPR { $$ = ast_new_binop(OP_EQ, $1, $3, yylineno); }
    | EXPR NE EXPR { $$ = ast_new_binop(OP_NE, $1, $3, yylineno); }
    | '-' EXPR %prec UMINUS { $$ = ast_new_unop(OP_NEG, $2, yylineno); }
    | PRIMARY { $$ = $1; }
    ;

PRIMARY
    : NUM { $$ = ast_new_num($1, yylineno); }
    | STR { $$ = ast_new_str($1, yylineno); }
    | BOOL { $$ = ast_new_bool($1, yylineno); }
    | TARGET { $$ = $1; }
    | CALL { $$ = $1; }
    | VECTOR { $$ = $1; }
    | '(' EXPR ')' { $$ = ast_new_paren($2, yylineno); }
    ;

CALL
    : ID '(' OPT_ARGS ')' { $$ = ast_new_call($1, $3, yylineno); }
    ;

VECTOR
    : '[' OPT_ARGS ']' { $$ = ast_new_vector($2, yylineno); }
    ;

OPT_ARGS
    : /* empty */ { $$ = NULL; }
    | ARG_LIST { $$ = $1; }
    ;

ARG_LIST
    : EXPR { $$ = $1; }
    | ARG_LIST ',' EXPR { $$ = ast_append_node($1, $3); }
    ;

%%

/* report syntax error with exact 1-based line number */
void yyerror(const char *s) {
    fprintf(stderr, "[Vektor Syntax Error] Line %d: %s\n", yylineno, s);
}
