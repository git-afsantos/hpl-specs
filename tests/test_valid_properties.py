# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from hypothesis import assume, given, settings

from hpl.ast import HplAstObject, HplProperty
from hpl.errors import HplSanityError
from hpl.parser import property_parser

from .strategies import properties

###############################################################################
# Property Examples
###############################################################################

GOOD_PROPERTIES = [
    'globally: some topic {int < 1 and float < 2 and string = "hello"}',
    'globally: no topic within 1s',
    'globally: input causes output',
    'globally: input causes output within 1s',
    'globally: output requires input',
    'globally: output requires input within 100 ms',
    (
        'after ~events/bumper {state = PRESSED}:'
        'some ~cmd_vel {linear.x < 0.0 and angular.z = 0.0}'
    ),
    'after input: no output',
    'globally: some topic {m.int in [0 to 10]!}',
    'globally: some topic {not int in [0 to 10]}',
    'globally: some topic {float_array[0] < float_array[1]}',
    'globally: some topic {forall i in [0 to len(int_array)]!: int_array[@i] > 0}',
    'globally: some topic {exists x in int_array: @x > 0}',
    'globally: some topic {len(twist_array) > 0}',
    'until input: some output',
    'after input as M: some output {x = @M.x}',
    'globally: no /joy_teleop/joy {not buttons[0] in {0, 1}}',
    'globally: no /agrob/agrob_mode {not mode in {0,1,2,3}}',
    (
        'after (p1 or p2 as P2 or p3 {phi} or p4 as P4 {phi})'
        'until (q1 or q2 as Q2 or q3 {phi} or q4 as Q4 {phi}):'
        '(a1 or a2 as A2 or a3 {phi} or a4 as A4 {phi})'
        'causes (b1 or b2 as B2 or b3 {phi} or b4 as B4 {phi})'
        'within 100 ms'
    ),
]

###############################################################################
# Test Code
###############################################################################

parser = property_parser()


def test_valid_handwritten_properties():
    for test_str in GOOD_PROPERTIES:
        ast = parser.parse(test_str)
        assert isinstance(ast, HplAstObject)
        assert ast.is_property
        assert isinstance(ast, HplProperty)


@given(properties())
@settings(max_examples=500)
def test_valid_generated_properties(text: str):
    try:
        ast = parser.parse(text)
    except (HplSanityError, TypeError):
        assume(False)  # discard insane properties

    assert isinstance(ast, HplAstObject)
    assert ast.is_property
    assert isinstance(ast, HplProperty)
