# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any

###############################################################################
# Functions
###############################################################################


def type_error_in_expr(error: TypeError, expr: Any) -> TypeError:
    return TypeError(f'type error in expression «{expr}»: {error}')


def invalid_type(expected: str, found: str, obj: Any) -> TypeError:
    return TypeError(f'expected type {expected} but found {found} in «{obj}»')


def missing_field(type_token: Any, field: str, obj: Any) -> TypeError:
    return TypeError(f"type '{type_token}' has no field '{field}' in «{obj}»")


def index_out_of_range(t_array: Any, idx: int, obj: Any) -> IndexError:
    return IndexError(f"index {idx} out of range in type '{t_array}' in «{obj}»")


###############################################################################
# Exceptions
###############################################################################


class HplSanityError(Exception):
    @classmethod
    def predicate_without_self_refs(cls, obj) -> 'HplSanityError':
        return cls(f'there are no references to message fields in «{obj}»')

    @classmethod
    def duplicate_event(cls, name: str, obj) -> 'HplSanityError':
        return cls(f"channel '{name}' appears multiple times in «{obj}»")


class HplSyntaxError(Exception):
    @classmethod
    def duplicate_metadata(cls, key, pid=None):
        which = ''
        if pid is not None:
            which = f" for property '{pid}'"
        return cls(f"duplicate metadata key '{key}'{which}")

    @classmethod
    def from_lark(cls, lark_exception):
        return cls(str(lark_exception))
