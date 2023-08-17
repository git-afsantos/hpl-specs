# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pytest import raises

from hpl.errors import HplSanityError, HplSyntaxError
from hpl.parser import property_parser

###############################################################################
# Test Code
###############################################################################

parser = property_parser()


def test_missing_scope():
    with raises(HplSyntaxError):
        parser.parse('some topic')


def test_using_comma_instead_of_and():
    with raises(HplSyntaxError):
        parser.parse('globally: some topic {int < 1, float < 2, string = "hello"}')


def test_filters_must_be_non_empty():
    with raises(HplSyntaxError):
        parser.parse('globally: some topic {}')


def test_cannot_compare_numbers_to_strings():
    with raises(TypeError):
        parser.parse('globally: some topic {int > "42"}')


def test_cannot_duplicate_aliases():
    with raises(HplSanityError):
        parser.parse('globally: input as M causes output1 as M')


def test_missing_parenthesis():
    with raises(HplSyntaxError):
        parser.parse('globally: input1 as M or input2 causes output1 as M')
