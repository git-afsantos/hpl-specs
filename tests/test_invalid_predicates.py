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

BAD_PREDICATES = [
    "a + b + c",
    "{1} and [2 to f.g.h]",
    "(1 and 2) + (not x)",
    "forall 42 in D: phi",
    "forall x in 42: phi",
    "forall x in D: 42",
    "a implies iff b",
    "a implies 42",
    "a and 42",
    "a or 42",
    "not 42",
    "not a + b",
    "-(a and b)",
    "a < b < c",
    "(a < b) < c",
    "x = -{1,2,3}",
    "a implies forall x in xs: b",
    "a[1][2]",
    "(a + 1) > 0 and a",
    "exists x in xs: (a[@x] implies @x)",
    "@a < 3",
    "---42 = -42",
    "f(x) > 0",
]


###############################################################################
# Test Code
###############################################################################

def test_invalid_predicates():
    parser = predicate_parser()
    for test_str in BAD_PREDICATES:
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
    print "\nAll", str(len(BAD_PREDICATES)), "tests passed."
    return 0


def main():
    logging.basicConfig(level=logging.DEBUG)
    if test_invalid_predicates():
        assert False
    return 0


if __name__ == "__main__":
    exit(main())
