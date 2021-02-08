# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from __future__ import unicode_literals
from past.builtins import basestring

from .ast import (
    And, Forall, Or, Not, T_MSG,
    HplBinaryOperator, HplContradiction, HplFunctionCall, HplLiteral,
    HplPredicate, HplThisMessage, HplVacuousTruth, HplVarReference
)

###############################################################################
# Constants
###############################################################################

OP_NOT = "not"
OP_AND = "and"
OP_OR = "or"
OP_IMPLIES = "implies"
OP_IFF = "iff"


###############################################################################
# Formula Rewriting
###############################################################################

def replace_this_with_var(predicate_or_expression, alias):
    if (not predicate_or_expression.is_predicate
            and not predicate_or_expression.is_expression):
        raise TypeError("expected HplPredicate or HplExpression: "
                        + repr(predicate_or_expression))
    if not isinstance(alias, basestring):
        raise TypeError("expected string alias: " + repr(alias))
    if predicate_or_expression.is_predicate:
        if predicate_or_expression.is_vacuous:
            return
        expr = predicate_or_expression.condition
    else:
        expr = predicate_or_expression
    for obj in expr.iterate():
        assert obj.is_expression
        if obj.is_accessor:
            if obj.is_field and obj.message.is_value:
                if obj.message.is_this_msg:
                    msg = HplVarReference("@" + alias)
                    msg.ros_type = obj.message.ros_type
                    obj.message = msg
                    obj._type_check(msg, T_MSG)

def replace_var_with_this(predicate_or_expression, alias):
    if (not predicate_or_expression.is_predicate
            and not predicate_or_expression.is_expression):
        raise TypeError("expected HplPredicate or HplExpression: "
                        + repr(predicate_or_expression))
    if not isinstance(alias, basestring):
        raise TypeError("expected string alias: " + repr(alias))
    if predicate_or_expression.is_predicate:
        if predicate_or_expression.is_vacuous:
            return
        expr = predicate_or_expression.condition
    else:
        expr = predicate_or_expression
    for obj in expr.iterate():
        assert obj.is_expression
        if obj.is_accessor:
            if obj.is_field and obj.message.is_value:
                if obj.message.is_variable and obj.message.name == alias:
                    msg = HplThisMessage()
                    msg.ros_type = obj.message.ros_type
                    obj.message = msg
                    obj._type_check(msg, T_MSG)


def refactor_reference(predicate_or_expression, alias):
    if (not predicate_or_expression.is_predicate
            and not predicate_or_expression.is_expression):
        raise TypeError("expected HplPredicate or HplExpression: "
                        + repr(predicate_or_expression))
    if not isinstance(alias, basestring):
        raise TypeError("expected string alias: " + repr(alias))
    if predicate_or_expression.is_predicate:
        return _refactor_ref_pred(predicate_or_expression, alias)
    else:
        return _refactor_ref_expr(predicate_or_expression, alias)

###############################################################################
# Formula Rewriting - Helper Functions
###############################################################################

def _refactor_ref_pred(phi, alias):
    if phi.is_vacuous:
        return (phi, HplVacuousTruth())
    expressions = _refactor_ref_expr(phi.condition, alias)
    predicates = []
    for expr in expressions:
        assert expr.can_be_bool
        if expr.is_value and expr.is_literal:
            assert isinstance(expr.value, bool)
            if expr.value:
                psi = HplVacuousTruth()
            else:
                psi = HplContradiction()
        else:
            psi = HplPredicate(expr)
        predicates.append(psi)
    return tuple(predicates)

def _refactor_ref_expr(expr, alias):
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
    assert False, "unknown expression type: " + repr(expr)

def _split_quantifier(quant, alias):
    var = quant.variable
    dom = quant.domain
    if dom.contains_reference(alias):
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
                    qa = Forall(var, dom.clone(), expr.a, shadow=True)
                else:
                    qa = Or(empty_test(dom.clone()), expr.a)
                if vb:
                    qb = Forall(var, dom, expr.b, shadow=True)
                else:
                    qb = Or(empty_test(dom), expr.b)
                return (qb, qa)
            if b and not a:
                if va:
                    qa = Forall(var, dom, expr.a, shadow=True)
                else:
                    qa = Or(empty_test(dom), expr.a)
                if vb:
                    qb = Forall(var, dom.clone(), expr.b, shadow=True)
                else:
                    qb = Or(empty_test(dom.clone()), expr.b)
                return (qa, qb)
            assert a and b
        # move everything
        return (true(), quant)
    if quant.is_existential:
        # (E x: p -> q)  ==  (E x: ~p | q)
        # (E x: p | q)  ==  ((E x: p) | (E x: q))
        # move everything, not worth splitting disjunctions
        return (true(), quant)
    assert False, "unknown quantifier: " + quant.quantifier

def _split_operator(op, alias):
    if op.arity == 1:
        assert op.operator == OP_NOT
        return _split_negation(op, alias)
    else:
        assert op.arity == 2
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

def _split_negation(neg, alias):
    expr = neg.operand
    assert expr.can_be_bool and expr.contains_reference(alias)
    if expr.is_value or expr.is_accessor or expr.is_function_call:
        # cannot split into two parts
        return (true(), neg)
    if expr.is_quantifier:
        if expr.is_existential:
            # (~E x: p)  ==  (A x: ~p)
            p = Not(expr.condition)
            assert p.contains_reference(expr.variable)
            expr = Forall(expr.variable, expr.domain, p, shadow=True)
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
    assert False, "unknown expression type: " + repr(expr)


###############################################################################
# Convenience Logic Tests
###############################################################################

def is_not(expr):
    return expr.is_operator and expr.arity == 1 and expr.operator == OP_NOT

def is_and(expr):
    return expr.is_operator and expr.arity == 2 and expr.operator == OP_AND

def is_or(expr):
    return expr.is_operator and expr.arity == 2 and expr.operator == OP_OR

def is_implies(expr):
    return expr.is_operator and expr.arity == 2 and expr.operator == OP_IMPLIES

def is_iff(expr):
    return expr.is_operator and expr.arity == 2 and expr.operator == OP_IFF

def is_true(expr):
    return expr.is_value and expr.is_literal and expr.value is True

def is_false(expr):
    return expr.is_value and expr.is_literal and expr.value is False

def empty_test(expr):
    a = HplFunctionCall("len", (expr,))
    b = HplLiteral("0", 0)
    return HplBinaryOperator("=", a, b)

def true():
    return HplLiteral("True", True)

def false():
    return HplLiteral("False", False)
