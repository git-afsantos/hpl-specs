# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from importlib.metadata import PackageNotFoundError, version  # pragma: no cover

###############################################################################
# Constants
###############################################################################

try:
    __version__ = version('hpl')
except PackageNotFoundError:  # pragma: no cover
    # package is not installed
    __version__ = 'unknown'
