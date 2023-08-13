# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pytest import raises

from hpl.parser import property_parser
from hpl.errors import HplSanityError, HplSyntaxError


###############################################################################
# Property Examples
###############################################################################

BAD_PROPERTIES = [
    # missing scope
    "some topic",

    # using comma instead of 'and' to separate filters
    'globally: some topic {int < 1, float < 2, string = "hello"}',

    # filters must be non-empty
    "globally: some topic {}",

    # cannot compare numbers to strings
    'globally: some topic {int > "42"}',

    # cannot duplicate aliases
    "globally: input as M causes output1 as M",

    # missing parenthesis
    "globally: input1 as M or input2 causes output1 as M"
]


###############################################################################
# Test Code
###############################################################################

def test_invalid_properties():
    parser = property_parser()
    for test_str in BAD_PROPERTIES:
        with raises((HplSanityError, HplSyntaxError, TypeError)):
            parser.parse(test_str)
