# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any

###############################################################################
# Functions
###############################################################################


def invalid_type(expected: str, found: str, obj: Any) -> None:
    raise TypeError(f'expected type {expected} but found {found} in {{{obj}}}')


###############################################################################
# Exceptions
###############################################################################


class HplSanityError(Exception):
    @classmethod
    def predicate_without_self_refs(cls, obj) -> 'HplSanityError':
        return cls(f'there are no references to message fields in «{obj}»')


class HplTypeError(Exception):
    @classmethod
    def ros_field(cls, rostype, field, expr):
        return cls(f"ROS '{rostype}' has no field '{field}': {expr}")

    @classmethod
    def ros_array(cls, rostype, expr):
        return cls(f"ROS '{rostype}' is not an array: {expr}")

    @classmethod
    def ros_index(cls, rostype, idx, expr):
        return cls(f"ROS '{rostype}' index {idx} out of range: {expr}")

    @classmethod
    def in_expr(cls, expr: Any, details: str):
        return cls(f'Type error in expression {{{expr}}}: {details}')

    @classmethod
    def unexpected(cls, expected: str, found: str, expr: Any):
        return cls(f'expected {expected} but found {found}: {expr}')

    @classmethod
    def cannot_cast(cls, initial: str, expected: str, expr: Any):
        return cls(f'cannot cast from {initial} to {expected}: {expr}')

    @classmethod
    def untyped(cls, expr: Any):
        return cls(f'no types left for {{{expr}}}')

    @classmethod
    def already_defined(cls, topic, ot, nt):
        return cls(f"Topic '{topic}' cannot be both of type {ot} and type {nt}")

    @classmethod
    def undefined(cls, topic):
        return cls(f"Unknown type for topic '{topic}'")


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
