# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Tuple, TypeVar, Union

from hpl.ast.expressions import (
    And,
    Forall,
    HplBinaryOperator,
    HplExpression,
    HplFunctionCall,
    HplLiteral,
    HplQuantifier,
    HplThisMessage,
    HplUnaryOperator,
    HplVarReference,
    Not,
    Or,
    is_self_reference,
    is_var_reference,
)
from hpl.ast.predicates import HplPredicate, HplVacuousTruth, predicate_from_expression
from hpl.errors import invalid_type

###############################################################################
# Constants
###############################################################################

P = TypeVar('P', HplPredicate, HplExpression)

###############################################################################
# Formula Rewriting
###############################################################################


def replace_this_with_var(predicate_or_expression: P, alias: str) -> P:
    if not predicate_or_expression.is_predicate and not predicate_or_expression.is_expression:
        raise invalid_type('HplPredicate or HplExpression', predicate_or_expression)
    if not isinstance(alias, str):
        raise invalid_type('string', alias)
    var = HplVarReference(f'@{alias}')
    if predicate_or_expression.is_expression:
        if is_self_reference(predicate_or_expression):
            return var
    return predicate_or_expression.replace_self_reference(var)


def replace_var_with_this(predicate_or_expression: P, alias: str) -> P:
    if not predicate_or_expression.is_predicate and not predicate_or_expression.is_expression:
        raise invalid_type('HplPredicate or HplExpression', predicate_or_expression)
    if not isinstance(alias, str):
        raise invalid_type('string', alias)
    this = HplThisMessage()
    if predicate_or_expression.is_expression:
        if is_var_reference(predicate_or_expression, alias=alias):
            return this
    return predicate_or_expression.replace_var_reference(alias, this)


def refactor_reference(predicate_or_expression: P, alias: str) -> Tuple[P, P]:
    if not predicate_or_expression.is_predicate and not predicate_or_expression.is_expression:
        raise invalid_type('HplPredicate or HplExpression', predicate_or_expression)
    if not isinstance(alias, str):
        raise invalid_type('string', alias)
    if predicate_or_expression.is_predicate:
        return _refactor_ref_pred(predicate_or_expression, alias)
    else:
        return _refactor_ref_expr(predicate_or_expression, alias)


###############################################################################
# Formula Rewriting - Helper Functions
###############################################################################


def _refactor_ref_pred(phi: HplPredicate, alias: str) -> Tuple[HplPredicate, HplPredicate]:
    if phi.is_vacuous:
        return (phi, HplVacuousTruth())
    expr1, expr2 = _refactor_ref_expr(phi.condition, alias)
    return (predicate_from_expression(expr1), predicate_from_expression(expr2))


def _refactor_ref_expr(expr: HplExpression, alias: str) -> Tuple[HplExpression, HplExpression]:
    if not expr.contains_reference(alias):
        return (expr, true())
    if not expr.can_be_bool:
        # move the whole expression
        return (true(), expr)
    if expr.is_value or expr.is_accessor or expr.is_function_call:
        # cannot split into two parts
        return (true(), expr)
    if expr.is_quantifier:
        return _split_quantifier(expr, alias)
    if expr.is_operator:
        return _split_operator(expr, alias)
    raise TypeError(f'unknown expression type: {expr!r}')


def _split_quantifier(quant: HplQuantifier, alias: str) -> Tuple[HplExpression, HplExpression]:
    var = quant.variable
    if quant.domain.contains_reference(alias):
        # move the whole expression
        return (true(), quant)
    expr = quant.condition
    assert expr.contains_reference(alias)
    # TODO optimize for nested quantifiers
    if quant.is_universal:
        # (A x: p & q)  ==  ((A x: p) & (A x: q))
        if is_not(expr) and is_or(expr.operand):
            expr = And(Not(expr.operand.a), Not(expr.operand.b))
        if is_and(expr):
            a = expr.a.contains_reference(alias)
            b = expr.b.contains_reference(alias)
            va = expr.a.contains_reference(var)
            vb = expr.b.contains_reference(var)
            if a and not b:
                if va:
                    qa = Forall(var, quant.domain, expr.a)
                else:
                    qa = Or(empty_test(quant.domain), expr.a)
                if vb:
                    qb = Forall(var, quant.domain, expr.b)
                else:
                    qb = Or(empty_test(quant.domain), expr.b)
                return (qb, qa)
            if b and not a:
                if va:
                    qa = Forall(var, quant.domain, expr.a)
                else:
                    qa = Or(empty_test(quant.domain), expr.a)
                if vb:
                    qb = Forall(var, quant.domain, expr.b)
                else:
                    qb = Or(empty_test(quant.domain), expr.b)
                return (qa, qb)
            assert a and b
        # move everything
        return (true(), quant)
    if quant.is_existential:
        # (E x: p -> q)  ==  (E x: ~p | q)
        # (E x: p | q)  ==  ((E x: p) | (E x: q))
        # move everything, not worth splitting disjunctions
        return (true(), quant)
    raise TypeError(f'unknown quantifier type: {quant!r}')


def _split_operator(
    op: Union[HplUnaryOperator, HplBinaryOperator], alias: str
) -> Tuple[HplExpression, HplExpression]:
    if op.arity == 1:
        assert isinstance(op, HplUnaryOperator)
        assert op.operator.is_not
        return _split_negation(op, alias)
    else:
        assert op.arity == 2
        assert isinstance(op, HplBinaryOperator)
        if is_and(op):
            a = op.a.contains_reference(alias)
            b = op.b.contains_reference(alias)
            if a and not b:
                return (op.b, op.a)
            if b and not a:
                return (op.a, op.b)
            assert a and b
        # cannot split into two parts
        return (true(), op)


def _split_negation(neg: HplUnaryOperator, alias: str) -> Tuple[HplExpression, HplExpression]:
    expr = neg.operand
    assert expr.can_be_bool and expr.contains_reference(alias)
    if expr.is_value or expr.is_accessor or expr.is_function_call:
        # cannot split into two parts
        return (true(), neg)
    if expr.is_quantifier:
        assert isinstance(expr, HplQuantifier)
        if expr.is_existential:
            # (~E x: p)  ==  (A x: ~p)
            p = Not(expr.condition)
            assert p.contains_reference(expr.variable)
            expr = Forall(expr.variable, expr.domain, p)
            return _split_quantifier(expr, alias)
        # TODO optimize for other (harder) cases
        return (true(), neg)
    if expr.is_operator:
        if is_not(expr):
            # ~~p  ==  p
            return _refactor_ref_expr(expr.operand, alias)
        if is_implies(expr):
            # ~(a -> b)  ==  ~(~a | b)  ==  a & ~b
            expr = And(expr.a, Not(expr.b))
            return _split_operator(expr, alias)
        if is_or(expr):
            # ~(a | b)  ==  ~a & ~b
            expr = And(Not(expr.a), Not(expr.b))
            return _split_operator(expr, alias)
        # cannot split into two parts
        return (true(), neg)
    raise TypeError(f'unknown expression type: {expr!r}')


###############################################################################
# Convenience Logic Tests
###############################################################################


def is_not(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 1 and expr.operator.is_not


def is_and(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_and


def is_or(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_or


def is_implies(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_implies


def is_iff(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_iff


def is_true(expr: HplExpression) -> bool:
    return expr.is_value and expr.is_literal and expr.value is True


def is_false(expr: HplExpression) -> bool:
    return expr.is_value and expr.is_literal and expr.value is False


def empty_test(expr: HplExpression) -> HplBinaryOperator:
    a = HplFunctionCall('len', (expr,))
    b = HplLiteral('0', 0)
    return HplBinaryOperator('=', a, b)


def true() -> HplLiteral:
    return HplLiteral('True', True)


def false() -> HplLiteral:
    return HplLiteral('False', False)
