# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hpl.ast.expressions import HplExpression
from hpl.ast.predicates import HplContradiction, HplPredicate, HplPredicateExpression, HplVacuousTruth
from hpl.parser import condition_parser
from hpl.rewrite import (
    is_true,
    refactor_reference,
    replace_this_with_var,
    replace_var_with_this,
    simplify,
    split_and,
)

###############################################################################
# Predicate Examples
###############################################################################

# Tests will try to move predicate from @A to @B.

NO_REFS = [
    'a + b < c',
    'forall x in xs: @x',
    'not a + b < c',
    '(not ((a or b) implies c) and d)',
    'f.int in [0 to 10]',
    'not array[0] in {0, 1, 2}',
    'x < @Y.y',
    'x = y',
]

REF_BUT_NO_SPLITS = [
    'forall x in @B.xs: xs[@x]',  # reference in domain
    'exists x in xs: @B.x < @x',  # existential quantifier
    'forall x in xs: (@x or @B.x)',  # disjunction
    'forall x in xs: (@x implies @B.x)',  # implication
    'forall x in xs: (@x iff @B.x)',  # equivalence
    'forall x in xs: (not @B.x = @x)',  # negation
    'forall x in xs: (@B.x < @x and @B.y > @x)',  # ref on both sides
    'not forall x in xs: (@x and @B.x)',  # universal quantifier
    'not exists x in xs: (@x and @B.x)',  # negated conjunction
    'not (x < @B.x implies y > @B.y)',  # ref on both sides
    'not (x < @B.x or y > @B.y)',  # ref on both sides
    'not (x and @B.x)',  # negated conjunction
    'x or @B.x',  # disjunction
    'x implies @B.x',  # implication
    'x iff @B.x',  # equivalence
    'x < @B.x and y > @B.y',  # ref on both sides
]

REF_WITH_SPLITS = [
    'x and y > @B.y',  # ref on one side
    'x < @B.x and y',  # ref on one side
    'not (not (x and y > @B.y))',  # double negation
    'not (x or @B.x)',  # negated disjunction
    'not (x implies @B.x)',  # negated implication
    'not exists x in xs: (@x or @B.x)',  # negated disjunction
    'forall x in xs: (@x and @B.x)',  # ref on one side
    'forall x in xs: not (@x or @B.x)',  # ref on one side
    'forall x in xs: (@x >= 0 and @B.x < @x)',  # ref on one side
]

###############################################################################
# Test Code
###############################################################################

parser = condition_parser()


def test_refactor_but_no_references():
    for test_str in NO_REFS:
        predicate: HplPredicate = parser.parse(test_str)
        phi, psi = refactor_reference(predicate.condition, 'B')
        assert phi.is_expression
        assert psi.is_expression
        assert phi is predicate.condition
        assert is_true(psi)


def test_refactor_references_but_no_splits():
    for test_str in REF_BUT_NO_SPLITS:
        predicate: HplPredicate = parser.parse(test_str)
        phi, psi = refactor_reference(predicate.condition, 'B')
        assert phi.is_expression
        assert psi.is_expression
        # assert psi is predicate.condition
        assert is_true(phi)


def test_refactor_references_with_splits():
    for test_str in REF_WITH_SPLITS:
        predicate: HplPredicate = parser.parse(test_str)
        phi, psi = refactor_reference(predicate.condition, 'B')
        assert phi.is_expression
        assert psi.is_expression
        assert phi != predicate.condition
        assert psi != predicate.condition
        assert not is_true(phi)
        assert not is_true(psi)


def test_replace_this_msg_but_no_splits():
    for test_str in REF_BUT_NO_SPLITS:
        predicate: HplPredicate = parser.parse(test_str)
        phi, psi = refactor_reference(predicate.condition, 'B')
        assert is_true(phi)
        replace_this_with_var(psi, 'A')
        replace_var_with_this(psi, 'B')


def test_replace_this_msg_with_splits():
    for test_str in REF_WITH_SPLITS:
        predicate: HplPredicate = parser.parse(test_str)
        phi, psi = refactor_reference(predicate.condition, 'B')
        assert isinstance(phi, HplExpression)
        assert isinstance(psi, HplExpression)
        assert not is_true(phi)
        assert not is_true(psi)
        replace_this_with_var(psi, 'A')
        replace_var_with_this(psi, 'B')


def test_split_conjunction_but_no_splits():
    examples = [
        'a + b < c',  # atomic
        'forall x in xs: @x',  # atomic
        'not a + b < c',  # atomic
        'f.int in [0 to 10]',  # atomic
        'not array[0] in {0, 1, 2}',  # atomic
        'exists x in xs: @B.x < @x',  # existential quantifier
        'forall x in xs: (@x or @B.x)',  # disjunction
        'forall x in xs: (@x implies @B.x)',  # implication
        'forall x in xs: (@x iff @B.x)',  # equivalence
        'forall x in xs: (not @B.x = @x)',  # negation
        'not forall x in xs: (@x and @B.x)',  # negated universal quantifier
        'not exists x in xs: (@x and @B.x)',  # negated conjunction
        'not (x and @B.x)',  # negated conjunction
        'x or @B.x',  # disjunction
        'x implies @B.x',  # implication
        'x iff @B.x',  # equivalence
    ]
    for test_str in examples:
        predicate: HplPredicate = parser.parse(test_str)
        conditions = split_and(predicate.condition)
        assert isinstance(conditions, list)
        assert len(conditions) == 1
        phi = conditions[0]
        assert isinstance(phi, HplExpression)
        # expression must be equivalent, but not exactly equal
        # assert phi == predicate.condition


def test_split_conjunction_with_splits():
    examples = [
        'x < 0 and y > 0',  # conjunction
        'not (x < 0 or y > 0)',  # negated disjunction
        'not (x < 0 implies y > 0)',  # negated implication
        'not exists x in xs: (@x or @B.x)',  # negated existential
        'forall x in xs: (0 < @x and 2 > @x)',  # universal quantifier
        'forall x in xs: not (0 < @x or 2 > @x)',  # universal quantifier
        'forall x in xs: not (0 < @x implies 2 > @x)',  # universal quantifier
        'forall x in xs: forall y in ys: (@x < 0 and @y > 0)',  # nested universal
        'forall x in xs: forall y in ys: not (@x < 0 or @y > 0)',  # nested universal
    ]
    for test_str in examples:
        predicate: HplPredicate = parser.parse(test_str)
        conditions = split_and(predicate.condition)
        assert isinstance(conditions, list)
        assert len(conditions) > 1
        for phi in conditions:
            assert isinstance(phi, HplExpression)
            assert phi != predicate.condition


def test_simplify_vacuous():
    p: HplPredicate = HplVacuousTruth()
    q: HplPredicate = simplify(p)
    assert q is p
    p = HplContradiction()
    q = simplify(p)
    assert q is p
    p = parser.parse('True')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)


def test_simplify_double_negation():
    p: HplPredicate = parser.parse('not not True')
    q: HplPredicate = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('not not False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('not not a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == parser.parse('a')


def test_simplify_iff():
    p: HplPredicate = parser.parse('True iff True')
    q: HplPredicate = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('False iff False')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('a iff a')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('True iff False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('False iff True')
    q = simplify(p)
    assert isinstance(q, HplContradiction)


def test_simplify_implies():
    p: HplPredicate = parser.parse('True implies True')
    q: HplPredicate = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('False implies False')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('True implies False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('False implies True')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('a implies a')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('(not a) implies a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == parser.parse('a')


def test_simplify_and():
    p: HplPredicate = parser.parse('True and True')
    q: HplPredicate = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('True and False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('a and False')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('False and a')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('(not a) and a')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    p = parser.parse('a and (not a)')
    q = simplify(p)
    assert isinstance(q, HplContradiction)
    a: HplExpression = parser.parse('a')
    p = parser.parse('a and True')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a
    p = parser.parse('True and a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a
    p = parser.parse('a and a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a


def test_simplify_or():
    p: HplPredicate = parser.parse('True or True')
    q: HplPredicate = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('True or False')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('a or True')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('True or a')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('(not a) or a')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    p = parser.parse('a or (not a)')
    q = simplify(p)
    assert isinstance(q, HplVacuousTruth)
    a: HplExpression = parser.parse('a')
    p = parser.parse('a or False')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a
    p = parser.parse('False or a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a
    p = parser.parse('a or a')
    q = simplify(p)
    assert isinstance(q, HplPredicateExpression)
    assert q == a
