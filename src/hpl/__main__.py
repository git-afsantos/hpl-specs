# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

"""
Entrypoint module, in case you use `python -m <package>`.

Why does this file exist, and why __main__? For more info, read:

  - https://www.python.org/dev/peps/pep-0338/
  - https://docs.python.org/2/using/cmdline.html#cmdoption-m
  - https://docs.python.org/3/using/cmdline.html#cmdoption-m
"""

###############################################################################
# Imports
###############################################################################

import sys

from hpl.cli import main

###############################################################################
# Entry Point
###############################################################################

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))  # pragma: no cover
