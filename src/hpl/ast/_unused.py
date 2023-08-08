# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from enum import auto, Enum

from attrs import frozen

###############################################################################
# Top-level Classes
###############################################################################


class HplAstObjectType(Enum):
    SPECIFICATION = auto()
    PROPERTY = auto()
    SCOPE = auto()
    PATTERN = auto()
    EVENT = auto()
    PREDICATE = auto()
    EXPRESSION = auto()


@frozen
class HplAstMetadata:
    object_type: HplAstObjectType

    @property
    def is_specification(self) -> bool:
        return self.object_type == HplAstObjectType.SPECIFICATION

    @property
    def is_property(self) -> bool:
        return self.object_type == HplAstObjectType.PROPERTY

    @property
    def is_scope(self) -> bool:
        return self.object_type == HplAstObjectType.SCOPE

    @property
    def is_pattern(self) -> bool:
        return self.object_type == HplAstObjectType.PATTERN

    @property
    def is_event(self) -> bool:
        return self.object_type == HplAstObjectType.EVENT

    @property
    def is_predicate(self) -> bool:
        return self.object_type == HplAstObjectType.PREDICATE

    @property
    def is_expression(self) -> bool:
        return self.object_type == HplAstObjectType.EXPRESSION
