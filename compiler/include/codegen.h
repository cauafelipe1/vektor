#ifndef VEKTOR_CODEGEN_H
#define VEKTOR_CODEGEN_H

#include <stdio.h>
#include "ast.h"

// emit python 3 source code from the parsed ast into out
int codegen_emit_python(const ASTNode *root, FILE *out);

#endif
