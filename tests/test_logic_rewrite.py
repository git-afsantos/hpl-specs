# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hpl.logic import (
    is_true, replace_this_with_var, replace_var_with_this, refactor_reference
)
from hpl.parser import predicate_parser

###############################################################################
# Predicate Examples
###############################################################################

# Tests will try to move predicate from @A to @B.

NO_REFS = [
    "a + b < c",
    "forall x in xs: @x",
    "not a + b < c",
    "(not ((a or b) implies c) and d)",
    "f.int in [0 to 10]",
    "not array[0] in {0, 1, 2}",
    "x < @Y.y",
    "x = y",
]

REF_BUT_NO_SPLITS = [
    "forall x in @B.xs: xs[@x]",                # reference in domain
    "exists x in xs: @B.x < @x",                # existential quantifier
    "forall x in xs: (@x or @B.x)",             # disjunction
    "forall x in xs: (@x implies @B.x)",        # implication
    "forall x in xs: (@x iff @B.x)",            # equivalence
    "forall x in xs: (not @B.x = @x)",          # negation
    "forall x in xs: (@B.x < @x and @B.y > @x)",# ref on both sides
    "not forall x in xs: (@x and @B.x)",        # universal quantifier
    "not exists x in xs: (@x and @B.x)",        # negated conjunction
    "not (x < @B.x implies y > @B.y)",          # ref on both sides
    "not (x < @B.x or y > @B.y)",               # ref on both sides
    "not (x and @B.x)",                         # negated conjunction
    "x or @B.x",                                # disjunction
    "x implies @B.x",                           # implication
    "x iff @B.x",                               # equivalence
    "x < @B.x and y > @B.y",                    # ref on both sides
]

REF_WITH_SPLITS = [
    "x and y > @B.y",                           # ref on one side
    "x < @B.x and y",                           # ref on one side
    "not (not (x and y > @B.y))",               # double negation
    "not (x or @B.x)",                          # negated disjunction
    "not (x implies @B.x)",                     # negated implication
    "not exists x in xs: (@x or @B.x)",         # negated disjunction
    "forall x in xs: (@x and @B.x)",            # ref on one side
    "forall x in xs: not (@x or @B.x)",         # ref on one side
    "forall x in xs: (@x >= 0 and @B.x < @x)",  # ref on one side
]


###############################################################################
# Test Code
###############################################################################


def test_refactor_but_no_references():
    parser = predicate_parser()
    for test_str in NO_REFS:
        expr = parser.parse(test_str)
        phi, psi = refactor_reference(expr, "B")
        assert phi.is_expression
        assert psi.is_expression
        assert phi is expr
        assert is_true(psi)


def test_refactor_references_but_no_splits():
    parser = predicate_parser()
    for test_str in REF_BUT_NO_SPLITS:
        expr = parser.parse(test_str)
        phi, psi = refactor_reference(expr, "B")
        assert phi.is_expression
        assert psi.is_expression
        #assert psi is expr
        assert is_true(phi)


def test_refactor_references_with_splits():
    parser = predicate_parser()
    for test_str in REF_WITH_SPLITS:
        expr = parser.parse(test_str)
        phi, psi = refactor_reference(expr, "B")
        assert phi.is_expression
        assert psi.is_expression
        assert phi != expr
        assert psi != expr
        assert not is_true(phi)
        assert not is_true(psi)


def test_replace_this_msg_but_no_splits():
    parser = predicate_parser()
    for test_str in REF_BUT_NO_SPLITS:
        expr = parser.parse(test_str)
        phi, psi = refactor_reference(expr, "B")
        assert is_true(phi)
        replace_this_with_var(psi, "A")
        replace_var_with_this(psi, "B")


def test_replace_this_msg_with_splits():
    parser = predicate_parser()
    for test_str in REF_WITH_SPLITS:
        expr = parser.parse(test_str)
        phi, psi = refactor_reference(expr, "B")
        assert not is_true(phi)
        assert not is_true(psi)
        replace_this_with_var(psi, "A")
        replace_var_with_this(psi, "B")
