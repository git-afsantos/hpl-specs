# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from enum import auto, Enum

from attrs import evolve, field, frozen

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import DataType
from hpl.errors import HplTypeError

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


###############################################################################
# Expressions
###############################################################################


@frozen
class HplExpression(HplAstObject):
    data_type: DataType = field()

    @data_type.default
    def _get_default_data_type(self):
        return self.default_data_type

    @data_type.validator
    def _check_own_data_type(self, _attribute, value: DataType):
        self.default_data_type.cast(value)

    @property
    def default_data_type(self) -> DataType:
        return DataType.ANY

    def cast(self, t: DataType) -> 'HplExpression':
        try:
            r: DataType = self.data_type.cast(t)
            return evolve(self, data_type=r)
        except TypeError as e:
            raise HplTypeError.in_expr(self, str(e))
