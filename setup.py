# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

try:
    import regex as re
except ImportError:
    import re
import os
from setuptools import setup, find_packages

SOURCE = os.path.relpath(os.path.join(os.path.dirname(__file__), "src"))

# Utility function to read the README, etc..
# Used for the long_description and other fields.
def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as f:
        contents = f.read()
    return contents

__version__ ,= re.findall('__version__ = "(.*)"', read("src/hpl/__init__.py"))

requirements = [r for r in read("requirements.txt").splitlines() if r]


setup(
    name             = "hpl-specs",
    version          = __version__,
    author           = u"André Santos",
    author_email     = "andre.f.santos@inesctec.pt",
    description      = "HAROS Property Specification Language",
    long_description = read("README.rst"),
    license          = "MIT",
    keywords         = "haros ros property-specification parser parsing ast",
    url              = "https://github.com/git-afsantos/hpl-specs",
    packages         = find_packages(SOURCE),
    package_dir      = {"": SOURCE},
    package_data     = {"hpl": ["grammars/*.lark"]},
    #classifiers      = []
    scripts          = ["scripts/build_grammars"],
    #entry_points     = {"console_scripts": ["hplc = hpl.hplc:main"]},
    python_requires  = ">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*",
    install_requires = requirements,
    extras_require   = {},
    zip_safe         = False
)
