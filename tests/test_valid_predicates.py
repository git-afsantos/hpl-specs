# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos


###############################################################################
# Imports
###############################################################################

import logging
from sys import exit

from hpl.parser import predicate_parser
from hpl.exceptions import HplSanityError, HplSyntaxError, HplTypeError


###############################################################################
# Predicate Examples
###############################################################################

GOOD_PREDICATES = [
    "a + b < c",
    "forall x in xs: @x",
    "a implies iff iff iff",
    "not a + b < c",
    "a + b * c ** d = e ** -(f - g) / h",
    "(not ((a or b) implies c) and d)",
    "a[1] = a[@i + 1]",
    "f.int in [0 to 10]",
    "f.int in ![0 to 10]",
    "f.int in [0 to 10]!",
    "f.int in ![0 to len(array)]!",
    "not array[0] in {0, 1, 2}",
]


###############################################################################
# Test Code
###############################################################################

def test_valid_predicates():
    parser = predicate_parser()
    for test_str in GOOD_PREDICATES:
        print "\n  #", repr(test_str)
        try:
            ast = parser.parse(test_str)
            print "[Parsing] OK (expected)"
            print ""
            print repr(ast)
        except (HplSanityError, HplSyntaxError, HplTypeError) as e:
            print "[Parsing] FAIL (unexpected)"
            print "  >>", str(e)
            return 1
    print "\nAll", str(len(GOOD_PREDICATES)), "tests passed."
    return 0


def main():
    logging.basicConfig(level=logging.DEBUG)
    if test_valid_predicates():
        assert False
    return 0


if __name__ == "__main__":
    exit(main())
