# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hpl.ast import HplAstObject
from hpl.parser import predicate_parser

###############################################################################
# Predicate Examples
###############################################################################

GOOD_PREDICATES = [
    "a + b < c",
    "forall x in xs: @x",
    "a implies iff iff iff",
    "not a + b < c",
    "a + b * c ** d = e ** -(f - g) / h",
    "(not ((a or b) implies c) and d)",
    "a[1] = a[@i + 1]",
    "f.int in [0 to 10]",
    "f.int in ![0 to 10]",
    "f.int in [0 to 10]!",
    "f.int in ![0 to len(array)]!",
    "not array[0] in {0, 1, 2}",
    "a[1][2]",
    "a implies forall x in xs: @x",
]


###############################################################################
# Test Code
###############################################################################


def test_valid_predicates():
    parser = predicate_parser()
    for test_str in GOOD_PREDICATES:
        ast = parser.parse(test_str)
        assert isinstance(ast, HplAstObject)
        assert ast.is_predicate
