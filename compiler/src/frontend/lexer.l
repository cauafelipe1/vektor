/* single file, track lines; suppress unused Flex helpers under -Werror */
%option noyywrap yylineno nounput noinput

%{
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ast.h"
#include "parser.tab.h"

/* yytext is reused on the next token; copy the lexeme to the heap (abort on OOM) */
static char *lex_strdup(const char *text) {
    char *copy = strdup(text);
    if (copy == NULL) {
        fprintf(stderr, "[Vektor Fatal Error] Line %d: out of memory\n", yylineno);
        exit(EXIT_FAILURE);
    }
    return copy;
}
%}

%%

%[^\n]*                                 { /* ignore single-line comment */ }
[ \t\r\n]+                              { /* ignore whitespace */ }

"true"                                  { yylval.bool_val = 1; return BOOL; }
"false"                                 { yylval.bool_val = 0; return BOOL; }

"<="                                    { return LE; }
">="                                    { return GE; }
"=="                                    { return EQ; }
"!="                                    { return NE; }

[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?     { yylval.str_val = lex_strdup(yytext); return NUM; }
\"([^\"\\\n]|\\.)*\"                    { yylval.str_val = lex_strdup(yytext); return STR; }
\"([^\"\\\n]|\\.)*                      {
                                            /* missing closing quote; YYerror hands control to the parser */
                                            fprintf(stderr, "[Vektor Lexical Error] Line %d: unterminated string literal\n", yylineno);
                                            return YYerror;
                                        }
[a-zA-Z_][a-zA-Z0-9_]*                  { yylval.str_val = lex_strdup(yytext); return ID; }

[=+\-*/^<>()\[\],;.]                    { return yytext[0]; }

.                                       {
                                            fprintf(stderr, "[Vektor Lexical Error] Line %d: unexpected character '%s'\n", yylineno, yytext);
                                            return YYerror;
                                        }

%%
