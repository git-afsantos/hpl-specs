# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pytest import raises

from hpl.ast.predicates import HplPredicateExpression
from hpl.errors import HplSanityError, HplSyntaxError
from hpl.parser import condition_parser

###############################################################################
# Test Code
###############################################################################

parser = condition_parser()


def test_addition_is_not_bool():
    with raises(TypeError):
        parser.parse('a + b + c')


def test_set_is_not_bool():
    with raises(TypeError):
        parser.parse('{1} and [2 to f.g.h]')


def test_number_is_not_bool():
    with raises(TypeError):
        parser.parse('(1 and 2) + (not x)')


def test_forall_var_should_be_name():
    with raises(HplSyntaxError):
        parser.parse('forall 42 in D: phi')


def test_forall_domain_should_be_set():
    with raises(TypeError):
        parser.parse('forall x in 42: phi')


def test_forall_condition_should_be_bool():
    with raises(TypeError):
        parser.parse('forall x in D: 42')


def test_bad_syntax_two_binops():
    with raises(HplSyntaxError):
        parser.parse('a implies iff b')


def test_bool_binop_arg_should_be_bool():
    with raises(TypeError):
        parser.parse('a implies 42')


def test_negation_arg_should_be_bool():
    with raises(TypeError):
        parser.parse('not 42')


def test_number_binop_arg_should_be_number():
    with raises(TypeError):
        parser.parse('not a + b')


def test_minus_arg_should_be_number():
    with raises(TypeError):
        parser.parse('-(a and b)')


def test_relational_op_arg_should_be_number():
    with raises(HplSyntaxError):
        parser.parse('a < b < c')
    with raises(TypeError):
        parser.parse('(a < b) < c')


def test_set_is_not_number():
    with raises(TypeError):
        parser.parse('x = -{1,2,3}')


def test_forall_condition_should_include_var_ref():
    with raises(HplSanityError):
        parser.parse('a implies forall x in xs: b')


def test_all_eq_refs_have_same_type():
    with raises(TypeError):
        parser.parse('(a + 1) > 0 and a')
    with raises(TypeError):
        parser.parse('exists x in xs: (a[@x] implies @x)')


def test_at_least_one_self_ref():
    with raises(HplSanityError):
        p = parser.parse('---42 = -42')
        assert isinstance(p, HplPredicateExpression)
        p.check_some_self_references()


def test_unknown_function():
    with raises(ValueError):
        parser.parse('f(x) > 0')
