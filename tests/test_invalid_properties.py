# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos


###############################################################################
# Imports
###############################################################################

import logging
from sys import exit

from hpl.parser import property_parser
from hpl.exceptions import HplSanityError, HplSyntaxError, HplTypeError


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
    "globally: input as M causes output1 as M"
]


###############################################################################
# Test Code
###############################################################################

def test_invalid_properties():
    parser = property_parser()
    for test_str in BAD_PROPERTIES:
        print "\n  #", repr(test_str)
        try:
            ast = parser.parse(test_str)
            print "[Parsing] OK (unexpected)"
            print ""
            print repr(ast)
            return 1
        except (HplSanityError, HplSyntaxError, HplTypeError) as e:
            print "[Parsing] FAIL (expected)"
            print "  >>", str(e)
    print "\nAll", str(len(BAD_PROPERTIES)), "tests passed."
    return 0


def main():
    logging.basicConfig(level=logging.DEBUG)
    if test_invalid_properties():
        assert False
    return 0


if __name__ == "__main__":
    exit(main())
