# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from enum import Enum, auto

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

    _DIFF_TYPES = "multiple occurrences of '{}' with incompatible types: " "found ({}) and ({})"
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
                raise HplSanityError("undefined message alias: '{}'".format(expr.name))
            t = aliases[expr.name]
        assert t.is_message
        expr.ros_type = t
        while stack:
            expr = stack.pop()
            if expr.is_field:
                if not (t.is_message or expr.field in t.fields or expr.field in t.constants):
                    raise HplTypeError.ros_field(t, expr.field, expr)
                if expr.field in t.fields:
                    t = t.fields[expr.field]
                else:
                    assert expr.field in t.constants, "'{}' not in {} or {}".format(
                        expr.field, t.fields, t.constants
                    )
                    t = t.constants[expr.field].ros_type
            else:
                assert expr.is_indexed
                if not t.is_array:
                    raise HplTypeError.ros_array(t, expr)
                i = expr.index
                if i.is_value and i.is_literal and not t.contains_index(i.value):
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


###############################################################################
# Type Tokens
###############################################################################


@frozen
class TypeToken:
    name: str

    def __attrs_pre_init__(self):
        raise TypeError('cannot instantiate an abstract class')

    @property
    def type(self) -> DataType:
        raise NotImplementedError()

    @property
    def is_bool(self) -> bool:
        return self.type.can_be_bool

    @property
    def is_number(self) -> bool:
        return self.type.can_be_number

    @property
    def is_string(self) -> bool:
        return self.type.can_be_string

    @property
    def is_message(self) -> bool:
        return self.type.can_be_message

    @property
    def is_array(self) -> bool:
        return self.type.can_be_array

    @property
    def is_range(self) -> bool:
        return self.type.can_be_range

    @property
    def is_set(self) -> bool:
        return self.type.can_be_set


@frozen
class StringType(TypeToken):
    @property
    def type(self) -> DataType:
        return DataType.STRING


@frozen
class EnumeratedType(TypeToken):
    _type: DataType = field(validator=in_(PRIMITIVE_TYPES))
    values: Tuple[Any] = field(factory=tuple, converter=tuple, validator=instance_of(tuple))

    @values.validator
    def _check_values(self, _attribute, values: Tuple[Any]):
        if self._type is DataType.BOOL:
            expected = bool
        elif self._type is DataType.NUMBER:
            expected = PY_NUMBER
        elif self._type is DataType.STRING:
            expected = str
        else:
            raise ValueError(f'unexpected type {self._type}')
        for value in values:
            if not isinstance(value, expected):
                raise TypeError(f'{value!r} is not of type {expected}')

    @property
    def type(self) -> DataType:
        return self._type

    @classmethod
    def booleans(cls, name: str = 'bool') -> 'EnumeratedType':
        return cls(name, type=DataType.BOOL, values=(False, True))


@frozen
class NumericType(TypeToken):
    min_value: Union[int, float, complex] = field(default=-INF, validator=instance_of(PY_NUMBER))
    max_value: Union[int, float, complex] = field(default=INF, validator=instance_of(PY_NUMBER))

    @max_value.validator
    def _check_max_value(self, _attribute, value: Union[int, float]):
        if value < self.min_value:
            raise ValueError(f'max_value={value} < min_value={self.min_value}')

    @property
    def type(self) -> DataType:
        return DataType.NUMBER

    @classmethod
    def uint8(cls, name: str = 'uint8') -> 'NumericType':
        min_value = 0
        max_value = 255
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def uint16(cls, name: str = 'uint16') -> 'NumericType':
        min_value = 0
        max_value = 65535
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def uint32(cls, name: str = 'uint32') -> 'NumericType':
        min_value = 0
        max_value = 4294967295
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def uint64(cls, name: str = 'uint64') -> 'NumericType':
        min_value = 0
        max_value = 18446744073709551615
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def int8(cls, name: str = 'int8') -> 'NumericType':
        min_value = -128
        max_value = 127
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def int16(cls, name: str = 'int16') -> 'NumericType':
        min_value = -32768
        max_value = 32767
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def int32(cls, name: str = 'int32') -> 'NumericType':
        min_value = -2147483648
        max_value = 2147483647
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def int64(cls, name: str = 'int64') -> 'NumericType':
        min_value = -9223372036854775808
        max_value = 9223372036854775807
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def float32(cls, name: str = 'float32') -> 'NumericType':
        min_value = -3.3999999521443642e38
        max_value = 3.3999999521443642e38
        return cls(name, min_value=min_value, max_value=max_value)

    @classmethod
    def float64(cls, name: str = 'float64') -> 'NumericType':
        min_value = -1.7e308
        max_value = 1.7e308
        return cls(name, min_value=min_value, max_value=max_value)


@frozen
class MessageType(TypeToken):
    fields: Mapping[str, TypeToken] = field(factory=dict)
    constants: Mapping[str, Any] = field(factory=dict)

    @property
    def type(self) -> DataType:
        return DataType.MESSAGE

    def leaf_fields(self) -> Mapping[str, TypeToken]:
        fields = {}
        for name, token in self.fields.items():
            if token.is_message:
                for subname, subtoken in token.leaf_fields():
                    fields[f'{name}.{subname}'] = subtoken
            else:
                fields[name] = token
        return fields


@frozen
class ArrayType(TypeToken):
    subtype: TypeToken
    length: int = field(default=-1, validator=ge(-1))

    @property
    def type(self) -> DataType:
        return DataType.ARRAY

    @property
    def is_fixed_length(self) -> bool:
        return self.length >= 0


###############################################################################
# Exported Constants
###############################################################################

BOOLEANS: Final[EnumeratedType] = EnumeratedType.booleans()
UINT8: Final[NumericType] = NumericType.uint8()
UINT16: Final[NumericType] = NumericType.uint16()
UINT32: Final[NumericType] = NumericType.uint32()
UINT64: Final[NumericType] = NumericType.uint64()
INT8: Final[NumericType] = NumericType.int8()
INT16: Final[NumericType] = NumericType.int16()
INT32: Final[NumericType] = NumericType.int32()
INT64: Final[NumericType] = NumericType.int64()
FLOAT32: Final[NumericType] = NumericType.float32()
FLOAT64: Final[NumericType] = NumericType.float64()
STRINGS: Final[StringType] = StringType('string')
