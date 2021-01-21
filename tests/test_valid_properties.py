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

GOOD_PROPERTIES = [
    'globally: some topic {int < 1 and float < 2 and string = "hello"}',

    "globally: no topic within 1s",

    "globally: input causes output",

    "globally: input causes output within 1s",

    "globally: output requires input",

    "globally: output requires input within 100 ms",

    """after ~events/bumper {state = PRESSED}:
        some ~cmd_vel {linear.x < 0.0 and angular.z = 0.0}""",

    "after input: no output",

    "globally: some topic {m.int in [0 to 10]!}",

    "globally: some topic {not int in [0 to 10]}",

    "globally: some topic {float_array[0] < float_array[1]}",

    "globally: some topic {forall i in [0 to len(int_array)]!: int_array[@i] > 0}",

    r"globally: some topic {exists x in int_array: @x > 0}",

    "globally: some topic {len(twist_array) > 0}",

    "until input: some output",

    "after input as M: some output {x = @M.x}",

    "globally: no /joy_teleop/joy {not buttons[0] in {0, 1}}",

    "globally: no /agrob/agrob_mode {not mode in {0,1,2,3}}",
]


###############################################################################
# Test Code
###############################################################################

def test_valid_properties():
    parser = property_parser()
    for test_str in GOOD_PROPERTIES:
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
    print "\nAll", str(len(GOOD_PROPERTIES)), "tests passed."
    return 0


def main():
    logging.basicConfig(level=logging.DEBUG)
    if test_valid_properties():
        assert False
    return 0


if __name__ == "__main__":
    exit(main())
