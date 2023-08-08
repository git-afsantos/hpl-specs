# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Iterator, Tuple

from attrs import frozen

###############################################################################
# Top-level Classes
###############################################################################


@frozen
class HplAstObject:
    @property
    def is_specification(self) -> bool:
        return False

    @property
    def is_property(self) -> bool:
        return False

    @property
    def is_scope(self) -> bool:
        return False

    @property
    def is_pattern(self) -> bool:
        return False

    @property
    def is_event(self) -> bool:
        return False

    @property
    def is_predicate(self) -> bool:
        return False

    @property
    def is_expression(self) -> bool:
        return False

    def children(self) -> Tuple['HplAstObject']:
        return ()

    def iterate(self) -> Iterator['HplAstObject']:
        stack = [self]
        while stack:
            obj = stack.pop()
            stack.extend(reversed(obj.children()))
            yield obj
