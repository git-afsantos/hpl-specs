# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hypothesis import HealthCheck, assume, given, settings, strategies as st
from hypothesis.extra.lark import from_lark
from lark import Lark

from hpl.ast import HplAstObject, HplExpression
from hpl.parser import expression_parser

from .grammar import HPL_GRAMMAR

###############################################################################
# Predicate Examples
###############################################################################


def expressions():
    g = Lark(
        HPL_GRAMMAR,
        parser='lalr',
        start='hpl_expression',
        maybe_placeholders=True,
        debug=True,
    )
    return from_lark(g, start='hpl_expression')


###############################################################################
# Test Code
###############################################################################

parser = expression_parser()


@given(expressions())
@settings(suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow])
def test_valid_expressions(text: str):
    try:
        ast = parser.parse(text)
        assert isinstance(ast, HplAstObject)
        assert ast.is_expression
        assert isinstance(ast, HplExpression)
    except TypeError:
        assume(False)
