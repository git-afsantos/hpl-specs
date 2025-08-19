# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from hpl.parser import property_parser
from hpl.rewrite import canonical_form

###############################################################################
# Predicate Examples
###############################################################################


###############################################################################
# Test Code
###############################################################################

parser = property_parser()


def test_canonical_global_absence_no_splits():
    property = parser.parse('globally: no a')
    outputs = canonical_form(property)

    assert len(outputs) == 1
    assert outputs[0] is property


def test_canonical_global_absence_splits():
    property = parser.parse('globally: no (a or b)')
    outputs = canonical_form(property)

    assert len(outputs) == 2

    assert outputs[0].pattern.behaviour.is_simple_event
    assert outputs[1].pattern.behaviour.is_simple_event

    assert outputs[0].pattern.behaviour is property.pattern.behaviour.event1
    assert outputs[1].pattern.behaviour is property.pattern.behaviour.event2


def test_canonical_global_existence_no_splits():
    property = parser.parse('globally: some (a or b)')
    outputs = canonical_form(property)

    assert len(outputs) == 1
    assert outputs[0] is property


def test_canonical_after_existence_splits():
    property = parser.parse('after (a or b): some (c or d)')
    outputs = canonical_form(property)

    assert len(outputs) == 2

    assert outputs[0].scope.activator.is_simple_event
    assert outputs[1].scope.activator.is_simple_event

    assert outputs[0].scope.activator is property.scope.activator.event1
    assert outputs[1].scope.activator is property.scope.activator.event2

    assert outputs[0].pattern is property.pattern
    assert outputs[1].pattern is property.pattern


def test_canonical_global_response_no_splits():
    property = parser.parse('globally: a causes (b or c)')
    outputs = canonical_form(property)

    assert len(outputs) == 1
    assert outputs[0] is property


def test_canonical_global_response_splits():
    property = parser.parse('globally: (a or b) causes (c or d)')
    outputs = canonical_form(property)

    assert len(outputs) == 2

    assert outputs[0].pattern.trigger.is_simple_event
    assert outputs[1].pattern.trigger.is_simple_event

    assert outputs[0].pattern.trigger is property.pattern.trigger.event1
    assert outputs[1].pattern.trigger is property.pattern.trigger.event2
