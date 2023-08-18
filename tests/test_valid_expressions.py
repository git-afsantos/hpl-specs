# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hypothesis import assume, given, settings

from hpl.ast import HplAstObject, HplExpression
from hpl.parser import expression_parser

from .strategies import expressions

###############################################################################
# Test Code
###############################################################################

parser = expression_parser()


@given(expressions())
@settings(max_examples=500)
# @settings(suppress_health_check=[HealthCheck.filter_too_much, HealthCheck.too_slow])
def test_valid_expressions(text: str):
    try:
        ast = parser.parse(text)
        assert isinstance(ast, HplAstObject)
        assert ast.is_expression
        assert isinstance(ast, HplExpression)
    except TypeError:
        assume(False)
