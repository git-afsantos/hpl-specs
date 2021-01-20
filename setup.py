# -*- coding: utf-8 -*-

try:
    import regex as re
except ImportError:
    import re
import os
from setuptools import setup, find_packages

# Utility function to read the README file.
# Used for the long_description.  It"s nice, because now 1) we have a top level
# README file and 2) it"s easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

__version__ ,= re.findall('__version__ = "(.*)"', read("hpl/__init__.py"))


# Courtesy of https://stackoverflow.com/a/36693250
#def package_files(directory):
#    paths = []
#    for (path, directories, filenames) in os.walk(directory):
#        for filename in filenames:
#            paths.append(os.path.join("..", path, filename))
#    return paths


#extra_files = package_files("examples")
#extra_files.append("*.yaml")


setup(
    name             = "hpl-specs",
    version          = __version__,
    author           = u"André Santos",
    author_email     = "andre.f.santos@inesctec.pt",
    description      = "HAROS Property Specification Language",
    long_description = read("README.md"),
    license          = "MIT",
    keywords         = "haros ros property-specification parser parsing ast",
    url              = "https://github.com/git-afsantos/hpl-specs",
    packages         = find_packages(),
    #entry_points     = {"console_scripts": ["hplc = hpl.hplc:main"]},
    #package_data     = {"hpl": extra_files},
    install_requires = [
        "future",
        "lark-parser<1.0.0"
    ],
    extras_require   = {},
    zip_safe         = True
)
