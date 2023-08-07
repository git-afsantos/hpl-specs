# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

import hpl

###############################################################################
# Tests
###############################################################################


def test_import_was_ok():
    assert True


def test_pkg_has_version():
    assert hasattr(hpl, '__version__')
    assert isinstance(hpl.__version__, str)
    assert hpl.__version__ != ''
