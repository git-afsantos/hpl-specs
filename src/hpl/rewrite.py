# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import List, Tuple, TypeVar, Union

from typeguard import typechecked

from hpl.ast.expressions import (
    And,
    BinaryOperatorDefinition,
    Forall,
    HplBinaryOperator,
    HplExpression,
    HplFunctionCall,
    HplLiteral,
    HplQuantifier,
    HplThisMessage,
    HplUnaryOperator,
    HplVarReference,
    Implies,
    Not,
    Or,
    is_self_reference,
    is_var_reference,
)
from hpl.ast.predicates import (
    HplContradiction,
    HplPredicate,
    HplPredicateExpression,
    HplVacuousTruth,
    predicate_from_expression,
)
from hpl.ast.properties import HplProperty, HplScope

###############################################################################
# Constants
###############################################################################

P = TypeVar('P', HplPredicate, HplExpression)

###############################################################################
# Formula Rewriting
###############################################################################


@typechecked
def replace_this_with_var(predicate_or_expression: P, alias: str) -> P:
    var = HplVarReference(f'@{alias}')
    if predicate_or_expression.is_expression:
        if is_self_reference(predicate_or_expression):
            return var
    return predicate_or_expression.replace_self_reference(var)


@typechecked
def replace_var_with_this(predicate_or_expression: P, alias: str) -> P:
    this = HplThisMessage()
    if predicate_or_expression.is_expression:
        if is_var_reference(predicate_or_expression, alias=alias):
            return this
    return predicate_or_expression.replace_var_reference(alias, this)


@typechecked
def refactor_reference(predicate_or_expression: P, alias: str) -> Tuple[P, P]:
    if predicate_or_expression.is_predicate:
        return _refactor_ref_pred(predicate_or_expression, alias)
    else:
        return _refactor_ref_expr(predicate_or_expression, alias)


@typechecked
def canonical_form(property: HplProperty) -> List[HplProperty]:
    if property.pattern.is_safety:
        return _canonical_form_safety(property)
    assert property.pattern.is_liveness
    return _canonical_form_liveness(property)


@typechecked
def split_and(predicate_or_expression: P) -> List[HplExpression]:
    if predicate_or_expression.is_predicate:
        assert isinstance(predicate_or_expression, HplPredicate)
        return _split_and_expr(predicate_or_expression.condition)
    assert isinstance(predicate_or_expression, HplExpression)
    return _split_and_expr(predicate_or_expression)


@typechecked
def simplify(predicate_or_expression: P) -> P:
    if predicate_or_expression.is_predicate:
        assert isinstance(predicate_or_expression, HplPredicate)
        if predicate_or_expression.is_vacuous:
            return predicate_or_expression
        expr: HplExpression = _simplify(predicate_or_expression.condition)
        if is_true(expr):
            return HplVacuousTruth()
        if is_false(expr):
            return HplContradiction()
        return HplPredicateExpression(expr)
    assert isinstance(predicate_or_expression, HplExpression)
    return _simplify(predicate_or_expression)


###############################################################################
# Formula Rewriting - Helper Functions
###############################################################################


@typechecked
def _refactor_ref_pred(phi: HplPredicate, alias: str) -> Tuple[HplPredicate, HplPredicate]:
    if phi.is_vacuous:
        return (phi, HplVacuousTruth())
    expr1, expr2 = _refactor_ref_expr(phi.condition, alias)
    return (predicate_from_expression(expr1), predicate_from_expression(expr2))


@typechecked
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
        return _split_ref_quantifier(expr, alias)
    if expr.is_operator:
        return _split_ref_operator(expr, alias)
    raise TypeError(f'unknown expression type: {expr!r}')


@typechecked
def _split_ref_quantifier(quant: HplQuantifier, alias: str) -> Tuple[HplExpression, HplExpression]:
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


@typechecked
def _split_ref_operator(
    op: Union[HplUnaryOperator, HplBinaryOperator], alias: str
) -> Tuple[HplExpression, HplExpression]:
    if op.arity == 1:
        assert isinstance(op, HplUnaryOperator)
        assert op.operator.is_not
        return _split_ref_negation(op, alias)
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


@typechecked
def _split_ref_negation(neg: HplUnaryOperator, alias: str) -> Tuple[HplExpression, HplExpression]:
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
            return _split_ref_quantifier(expr, alias)
        # TODO optimize for other (harder) cases
        return (true(), neg)
    if expr.is_operator:
        if is_not(expr):
            # ~~p  ==  p
            return _refactor_ref_expr(expr.operand, alias)
        if is_implies(expr):
            # ~(a -> b)  ==  ~(~a | b)  ==  a & ~b
            expr = And(expr.a, Not(expr.b))
            return _split_ref_operator(expr, alias)
        if is_or(expr):
            # ~(a | b)  ==  ~a & ~b
            expr = And(Not(expr.a), Not(expr.b))
            return _split_ref_operator(expr, alias)
        # cannot split into two parts
        return (true(), neg)
    raise TypeError(f'unknown expression type: {expr!r}')


@typechecked
def _canonical_form_safety(property: HplProperty) -> List[HplProperty]:
    scopes = _canonical_form_scopes(property.scope)
    pattern = property.pattern
    patterns = [pattern.but(behaviour=event) for event in pattern.behaviour.simple_events()]
    if len(scopes) == 1 and len(patterns) == 1:
        # nothing changed
        return [property]
    return [property.but(scope=scope, pattern=pattern) for scope in scopes for pattern in patterns]


@typechecked
def _canonical_form_liveness(property: HplProperty) -> List[HplProperty]:
    scopes = _canonical_form_scopes(property.scope)
    if property.pattern.is_existence:
        patterns = [property.pattern]  # no splits
    else:
        assert property.pattern.is_response, f'pattern: {property.pattern}'
        trigger = property.pattern.trigger
        assert trigger is not None
        patterns = [property.pattern.but(trigger=event) for event in trigger.simple_events()]
    if len(scopes) == 1 and len(patterns) == 1:
        # nothing changed
        return [property]
    return [property.but(scope=scope, pattern=pattern) for scope in scopes for pattern in patterns]


@typechecked
def _canonical_form_scopes(scope: HplScope) -> List[HplScope]:
    if scope.is_after:  # after or after-until
        assert scope.activator is not None
        return [scope.but(activator=event) for event in scope.activator.simple_events()]
    assert scope.is_global or scope.is_until
    return [scope]


@typechecked
def _split_and_expr(phi: HplExpression) -> List[HplExpression]:
    conditions: List[HplExpression] = []
    stack: List[HplExpression] = [phi]
    while stack:
        expr: HplExpression = stack.pop()
        # preprocessing
        if is_true(expr):
            continue
        if is_false(expr):
            raise ValueError(f'unsatisfiable: {phi}')
        expr = _and_presplit_transform(expr)
        # expr should be either an And or something undivisible
        # splits
        if is_and(expr):
            assert isinstance(expr, HplBinaryOperator)
            stack.append(expr.a)
            stack.append(expr.b)
        else:
            conditions.append(expr)
    return conditions


@typechecked
def _and_presplit_transform(phi: HplExpression) -> HplExpression:
    # This should not need a loop any longer
    # previous = None
    # while phi is not previous:
    #     previous = phi
    #     if is_not(phi):
    #         phi = _split_and_not(phi)
    #     elif phi.is_quantifier:
    #         phi = _split_and_quantifier(phi)

    if is_not(phi):
        return _split_and_not(phi)
    if phi.is_quantifier:
        return _split_and_quantifier(phi)
    return phi  # atomic


@typechecked
def _split_and_not(neg: HplUnaryOperator) -> HplExpression:
    """
    Transform a Negation into either an And or something undivisible
    """
    phi: HplExpression = neg.operand
    if is_not(phi):
        # ~~p  ==  p
        assert isinstance(phi, HplUnaryOperator)
        return _and_presplit_transform(phi.operand)
    if is_or(phi):
        # ~(a | b)  ==  ~a & ~b
        assert isinstance(phi, HplBinaryOperator)
        return And(Not(phi.a), Not(phi.b))
    if is_implies(phi):
        # ~(a -> b)  ==  ~(~a | b)  ==  a & ~b
        return And(phi.a, Not(phi.b))
    if phi.is_quantifier:
        assert isinstance(phi, HplQuantifier)
        if phi.is_existential:
            # (~E x: p)  ==  (A x: ~p)
            p = Not(phi.condition)
            assert p.contains_reference(phi.variable)
            phi = Forall(phi.variable, phi.domain, p)
            return _split_and_quantifier(phi)
    return neg


@typechecked
def _split_and_quantifier(quant: HplQuantifier) -> HplExpression:
    """
    Transform a Quantifier into either an And or something undivisible
    """
    var: str = quant.variable
    phi: HplExpression = quant.condition
    if quant.is_universal:
        # (A x: p & q)  ==  ((A x: p) & (A x: q))
        phi = _and_presplit_transform(phi)
        if is_and(phi):
            assert isinstance(phi, HplBinaryOperator)
            if phi.a.contains_reference(var):
                qa = Forall(var, quant.domain, phi.a)
            else:
                qa = Or(empty_test(quant.domain), phi.a)
            if phi.b.contains_reference(var):
                qb = Forall(var, quant.domain, phi.b)
            else:
                qb = Or(empty_test(quant.domain), phi.b)
            return And(qa, qb)
    elif quant.is_existential:
        # (E x: p -> q)  ==  (E x: ~p | q)
        # (E x: p | q)  ==  ((E x: p) | (E x: q))
        pass  # not worth splitting disjunctions
    return quant  # nothing to do


@typechecked
def _simplify(phi: HplExpression) -> HplExpression:
    if is_not(phi):
        assert isinstance(phi, HplUnaryOperator)
        psi: HplExpression = phi.operand
        # ~T == F
        if is_true(psi):
            return false()
        # ~F == T
        if is_false(psi):
            return true()
        # ~~p  ==  p
        if is_not(psi):
            assert isinstance(psi, HplUnaryOperator)
            return _simplify(psi.operand)

    elif is_iff(phi):
        assert isinstance(phi, HplBinaryOperator)
        # (p == p) == T
        p: HplExpression = _simplify(phi.operand1)
        q: HplExpression = _simplify(phi.operand2)
        if p == q:
            return true()
        # (p == q) == ((p -> q) & (q -> p))
        return _simplify(And(Implies(p, q), Implies(q, p)))

    elif is_implies(phi):
        assert isinstance(phi, HplBinaryOperator)
        # p -> p == T
        p: HplExpression = _simplify(phi.operand1)
        q: HplExpression = _simplify(phi.operand2)
        if p == q:
            return true()
        # p -> q == ~p | q
        return _simplify(Or(Not(p), q))

    elif is_and(phi):
        assert isinstance(phi, HplBinaryOperator)
        p: HplExpression = _simplify(phi.operand1)
        q: HplExpression = _simplify(phi.operand2)
        # F & q == F
        if is_false(p):
            return p
        # p & F == F
        if is_false(q):
            return q
        # T & q == q
        if is_true(p):
            return q
        # p & T == p
        if is_true(q):
            return p
        # p & p == p
        if p == q:
            return p
        # ~p & p == F
        if is_not(p):
            assert isinstance(p, HplUnaryOperator)
            if p.operand == q:
                return false()
        # p & ~p == F
        if is_not(q):
            assert isinstance(q, HplUnaryOperator)
            if q.operand == p:
                return false()
        return phi if p is phi.operand1 and q is phi.operand2 else And(p, q)

    elif is_or(phi):
        assert isinstance(phi, HplBinaryOperator)
        p: HplExpression = _simplify(phi.operand1)
        q: HplExpression = _simplify(phi.operand2)
        # T | q == T
        if is_true(p):
            return p
        # p | T == T
        if is_true(q):
            return q
        # F | q == q
        if is_false(p):
            return q
        # p | F == p
        if is_false(q):
            return p
        # p | p == p
        if p == q:
            return p
        # ~p | p == T
        if is_not(p):
            assert isinstance(p, HplUnaryOperator)
            if p.operand == q:
                return true()
        # p | ~p == T
        if is_not(q):
            assert isinstance(q, HplUnaryOperator)
            if q.operand == p:
                return true()
        return phi if p is phi.operand1 and q is phi.operand2 else Or(p, q)

    elif is_comparison(phi):
        assert isinstance(phi, HplBinaryOperator)
        if is_self_or_field(phi.operand2) and not is_self_or_field(phi.operand1):
            if phi.operator.commutative:
                return phi.but(operand1=phi.operand2, operand2=phi.operand1)
            op: BinaryOperatorDefinition = inverse_operator(phi.operator)
            return HplBinaryOperator(op, phi.operand2, phi.operand1)

    return phi


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


def is_inclusion(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_inclusion


def is_comparison(expr: HplExpression) -> bool:
    return expr.is_operator and expr.arity == 2 and expr.operator.is_comparison


def is_true(expr: HplExpression) -> bool:
    return expr.is_value and expr.is_literal and expr.value is True


def is_false(expr: HplExpression) -> bool:
    return expr.is_value and expr.is_literal and expr.value is False


def is_self_or_field(expr: HplExpression) -> bool:
    if is_self_reference(expr):
        return True
    if expr.is_accessor and is_self_reference(expr.object):
        return True
    return False


def empty_test(expr: HplExpression) -> HplBinaryOperator:
    a = HplFunctionCall('len', (expr,))
    b = HplLiteral('0', 0)
    return HplBinaryOperator('=', a, b)


def inverse_operator(op: BinaryOperatorDefinition) -> BinaryOperatorDefinition:
    if op.commutative:
        return op
    if op.is_less_than:
        return BinaryOperatorDefinition.greater_than_eq()
    if op.is_less_than_eq:
        return BinaryOperatorDefinition.greater_than()
    if op.is_greater_than:
        return BinaryOperatorDefinition.less_than_eq()
    if op.is_greater_than_eq:
        return BinaryOperatorDefinition.less_than()
    raise ValueError(f'operator {op!r} does not have an inverse')


def true() -> HplLiteral:
    return HplLiteral('True', True)


def false() -> HplLiteral:
    return HplLiteral('False', False)
