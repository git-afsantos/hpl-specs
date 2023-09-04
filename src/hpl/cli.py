# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

"""
Module that contains the command line program.

Why does this file exist, and why not put this in __main__?

  In some cases, it is possible to import `__main__.py` twice.
  This approach avoids that. Also see:
  https://click.palletsprojects.com/en/5.x/setuptools/#setuptools-integration

Some of the structure of this file came from this StackExchange question:
  https://softwareengineering.stackexchange.com/q/418600
"""

###############################################################################
# Imports
###############################################################################

from typing import Any, Dict, Final, List, Optional

import argparse
from enum import Enum
import json
from math import isinf, isnan
from pathlib import Path
import sys
from traceback import print_exc

from attrs import asdict

from hpl import __version__ as current_version
from hpl.ast.base import HplAstObject
from hpl.errors import HplSyntaxError
from hpl.parser import parse_property, parse_specification

###############################################################################
# Constants
###############################################################################

PROG: Final[str] = 'hpl'

FORMAT_JSON: Final[str] = 'json'

###############################################################################
# Argument Parsing
###############################################################################


def parse_arguments(argv: Optional[List[str]]) -> Dict[str, Any]:
    description = 'Command-line parser for HPL properties.'
    parser = argparse.ArgumentParser(prog=PROG, description=description)

    parser.add_argument(
        '--version',
        action='version',
        version=f'{PROG} {current_version}',
        help='prints the program version',
    )

    parser.add_argument(
        '-p',
        '--property',
        dest='as_property',
        action='store_true',
        help='process arg as HPL property (default: HPL file)',
    )

    parser.add_argument(
        '-o',
        '--output',
        choices=(FORMAT_JSON,),
        help='output format (default: none)',
    )

    parser.add_argument(
        'arg',
        help=f'argument for the {PROG} command',
    )

    args = parser.parse_args(args=argv)
    return vars(args)


###############################################################################
# Setup
###############################################################################


def load_configs(args: Dict[str, Any]) -> Dict[str, Any]:
    try:
        config: Dict[str, Any] = {}
        # with open(args['config_path'], 'r') as file_pointer:
        # yaml.safe_load(file_pointer)

        # arrange and check configs here

        return config
    except Exception as err:
        # log or raise errors
        print(err, file=sys.stderr)
        if str(err) == 'Really Bad':
            raise err

        # Optional: return some sane fallback defaults.
        sane_defaults: Dict[str, Any] = {}
        return sane_defaults


###############################################################################
# Helper Functions
###############################################################################


def _ast_object_serializer(_ast: HplAstObject, _field: Any, value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, float) and (isinf(value) or isnan(value)):
        return None
    return value


###############################################################################
# Entry Point
###############################################################################


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)

    try:
        # Load additional config files here, e.g., from a path given via args.
        # Alternatively, set sane defaults if configuration is missing.
        _config = load_configs(args)

        if args['as_property']:
            result: HplAstObject = parse_property(args['arg'])
        else:
            path: Path = Path(args['arg']).resolve(strict=True)
            text: str = path.read_text(encoding='utf-8')
            result = parse_specification(text)

        format: Optional[str] = args.get('output')
        if format == FORMAT_JSON:
            data: Dict[str, Any] = asdict(result, value_serializer=_ast_object_serializer)
            output: str = json.dumps(data, indent=2)
            print(output)

    except HplSyntaxError as hse:
        print('Syntax error:', file=sys.stderr)
        print(hse, file=sys.stderr)
        return 1

    except KeyboardInterrupt:
        print('Aborted manually.', file=sys.stderr)
        return 1

    except Exception as err:
        print('An unhandled exception crashed the application!')
        print(err)
        print_exc()
        return 1

    return 0  # success
