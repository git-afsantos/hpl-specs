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




###############################################################################
# Predicates
###############################################################################

@frozen
class HplPredicate(HplAstObject):
    condition: HplExpression

    _DIFF_TYPES = ("multiple occurrences of '{}' with incompatible types: "
                   "found ({}) and ({})")
    _NO_REFS = "there are no references to any fields of this message"

    def __init__(self, expr):
        if not expr.is_expression:
            raise TypeError("not an expression: " + str(expr))
        if not expr.can_be_bool:
            raise HplTypeError("not a boolean expression: " + str(expr))
        self.condition = expr
        self._static_checks()

    @property
    def phi(self):
        return self.condition

    def is_fully_typed(self):
        return self.condition.is_fully_typed()

    def children(self):
        return (self.condition,)

    def negate(self):
        if self.condition.is_operator and self.condition.operator == "not":
            return HplPredicate(self.condition.operand)
        return HplPredicate(HplUnaryOperator("not", self.condition))

    def join(self, other):
        if other.is_vacuous:
            return self if other.is_true else other
        expr = HplBinaryOperator("and", self.condition, other.condition)
        return HplPredicate(expr)

    def external_references(self):
        return self.condition.external_references()

    def contains_reference(self, alias):
        return self.condition.contains_reference(alias)

    def refine_types(self, rostype, aliases=None):
        # rostype: ROS Type Token
        # aliases: string (alias) -> ROS Type Token
        aliases = aliases if aliases is not None else {}
        stack = [self.condition]
        while stack:
            obj = stack.pop()
            if obj.is_accessor:
                self._refine_type(obj, rostype, aliases)
            else:
                stack.extend(reversed(obj.children()))

    def replace_self_reference(self, alias):
        for obj in self.iterate():
            if obj.is_expression and obj.is_accessor:
                if obj.is_field and obj.message.is_value:
                    if obj.message.is_variable:
                        if obj.message.name == alias:
                            msg = HplThisMessage()
                            obj.message = msg
                            obj._type_check(msg, T_MSG)

    def _refine_type(self, accessor, rostype, aliases):
        stack = [accessor]
        expr = accessor.message
        while expr.is_accessor:
            stack.append(expr)
            expr = expr.message
        assert expr.is_value and (expr.is_this_msg or expr.is_variable)
        if expr.is_this_msg:
            t = rostype
        else:
            if expr.name not in aliases:
                raise HplSanityError(
                    "undefined message alias: '{}'".format(expr.name))
            t = aliases[expr.name]
        assert t.is_message
        expr.ros_type = t
        while stack:
            expr = stack.pop()
            if expr.is_field:
                if not (t.is_message or expr.field in t.fields
                        or expr.field in t.constants):
                    raise HplTypeError.ros_field(t, expr.field, expr)
                if expr.field in t.fields:
                    t = t.fields[expr.field]
                else:
                    assert expr.field in t.constants, \
                        "'{}' not in {} or {}".format(
                            expr.field, t.fields, t.constants)
                    t = t.constants[expr.field].ros_type
            else:
                assert expr.is_indexed
                if not t.is_array:
                    raise HplTypeError.ros_array(t, expr)
                i = expr.index
                if (i.is_value and i.is_literal
                        and not t.contains_index(i.value)):
                    raise HplTypeError.ros_index(t, expr.index, expr)
                t = t.type_token
            if t.is_message:
                accessor._type_check(expr, T_MSG)
            elif t.is_array:
                accessor._type_check(expr, T_ARR)
            elif t.is_number:
                accessor._type_check(expr, T_NUM)
                # TODO check that values fit within types
            elif t.is_bool:
                accessor._type_check(expr, T_BOOL)
            elif t.is_string:
                accessor._type_check(expr, T_STR)
            expr.ros_type = t