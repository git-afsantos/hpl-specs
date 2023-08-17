# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Final, Iterable, Mapping, Tuple

from enum import Flag, auto

from attrs import field, frozen
from attrs.validators import ge, in_, instance_of

###############################################################################
# Constants
###############################################################################

INF: Final[float] = float('inf')

###############################################################################
# Type System
###############################################################################

# These work as possible types for an expression.
# An expression of unknown type would have "any" type (i.e., all flags on).
# E.g., (NUMBER | BOOL) means the expression can be either a number or a bool.
# Things like variables start with many possible types, and are refined as the
# tree is built.


class DataType(Flag):
    BOOL = auto()
    NUMBER = auto()
    STRING = auto()
    ARRAY = auto()
    RANGE = auto()
    SET = auto()
    MESSAGE = auto()

    NONE = BOOL & NUMBER
    PRIMITIVE = BOOL | NUMBER | STRING
    ITEM = BOOL | NUMBER | STRING | MESSAGE
    COMPOUND = ARRAY | RANGE | SET
    ANY = BOOL | NUMBER | STRING | ARRAY | RANGE | SET | MESSAGE

    @staticmethod
    def union(types: Iterable['DataType']) -> 'DataType':
        result = DataType.NONE
        for t in types:
            result = result | t
        return result

    @property
    def pretty_name(self) -> str:
        ns = []
        for name, member in type(self).__members__.items():
            if self is member:
                return self.name.capitalize()
            if (self & member) != 0:
                ns.append(name)
        return ' or '.join(ns)

    @property
    def can_be_bool(self) -> bool:
        return bool(self & DataType.BOOL)

    @property
    def can_be_number(self) -> bool:
        return bool(self & DataType.NUMBER)

    @property
    def can_be_string(self) -> bool:
        return bool(self & DataType.STRING)

    @property
    def can_be_array(self) -> bool:
        return bool(self & DataType.ARRAY)

    @property
    def can_be_set(self) -> bool:
        return bool(self & DataType.SET)

    @property
    def can_be_range(self) -> bool:
        return bool(self & DataType.RANGE)

    @property
    def can_be_message(self) -> bool:
        return bool(self & DataType.MESSAGE)

    def can_be(self, t: 'DataType') -> bool:
        return bool(self & t)

    def cast(self, t: 'DataType') -> 'DataType':
        r = self & t
        if not r:
            raise TypeError(f"cannot cast '{self}' to '{t}'")
        return r

    def __str__(self) -> str:
        return self.pretty_name


###############################################################################
# Exported Constants
###############################################################################

BOOL_TYPE: Final[DataType] = DataType.BOOL
NUMBER_TYPE: Final[DataType] = DataType.NUMBER
STRING_TYPE: Final[DataType] = DataType.STRING
ARRAY_TYPE: Final[DataType] = DataType.ARRAY
SET_TYPE: Final[DataType] = DataType.SET
MESSAGE_TYPE: Final[DataType] = DataType.MESSAGE

PRIMITIVE_TYPES: Final[Tuple[DataType]] = (BOOL_TYPE, NUMBER_TYPE, STRING_TYPE)

BASE_TYPES: Final[Tuple[DataType]] = (
    BOOL_TYPE,
    NUMBER_TYPE,
    STRING_TYPE,
    ARRAY_TYPE,
    SET_TYPE,
    MESSAGE_TYPE,
)

###############################################################################
# Type Tokens
###############################################################################


@frozen
class TypeToken:
    name: str
    type: DataType = field(validator=in_(BASE_TYPES))

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

    def __str__(self) -> str:
        return self.name


@frozen
class EnumeratedType(TypeToken):
    values: Tuple[Any] = field(factory=tuple, converter=tuple, validator=instance_of(tuple))

    @values.validator
    def _check_values(self, _attribute, values: Tuple[Any]):
        if self.type is DataType.BOOL:
            expected = bool
        elif self.type is DataType.NUMBER:
            expected = (int, float, complex)
        elif self.type is DataType.STRING:
            expected = str
        else:
            expected = object
        for value in values:
            if not isinstance(value, expected):
                raise TypeError(f'{value!r} is not of type {expected}')

    @classmethod
    def booleans(cls, name: str = 'bool') -> 'EnumeratedType':
        return cls(name, type=DataType.BOOL, values=(False, True))


@frozen
class RangedType(TypeToken):
    min_value: Any = field(default=-INF)
    max_value: Any = field(default=INF)

    @max_value.validator
    def _check_max_value(self, _attribute, value: Any):
        if value < self.min_value:
            raise ValueError(f'max_value={value} < min_value={self.min_value}')

    @classmethod
    def uint8(cls, name: str = 'uint8') -> 'RangedType':
        min_value = 0
        max_value = 255
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def uint16(cls, name: str = 'uint16') -> 'RangedType':
        min_value = 0
        max_value = 65535
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def uint32(cls, name: str = 'uint32') -> 'RangedType':
        min_value = 0
        max_value = 4294967295
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def uint64(cls, name: str = 'uint64') -> 'RangedType':
        min_value = 0
        max_value = 18446744073709551615
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def int8(cls, name: str = 'int8') -> 'RangedType':
        min_value = -128
        max_value = 127
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def int16(cls, name: str = 'int16') -> 'RangedType':
        min_value = -32768
        max_value = 32767
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def int32(cls, name: str = 'int32') -> 'RangedType':
        min_value = -2147483648
        max_value = 2147483647
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def int64(cls, name: str = 'int64') -> 'RangedType':
        min_value = -9223372036854775808
        max_value = 9223372036854775807
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def float32(cls, name: str = 'float32') -> 'RangedType':
        min_value = -3.3999999521443642e38
        max_value = 3.3999999521443642e38
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)

    @classmethod
    def float64(cls, name: str = 'float64') -> 'RangedType':
        min_value = -1.7e308
        max_value = 1.7e308
        return cls(name, type=DataType.NUMBER, min_value=min_value, max_value=max_value)


@frozen
class MessageType(TypeToken):
    type: DataType = field(init=False, default=DataType.MESSAGE)
    fields: Mapping[str, TypeToken] = field(factory=dict)
    constants: Mapping[str, Tuple[TypeToken, Any]] = field(factory=dict)

    def leaf_fields(self) -> Mapping[str, TypeToken]:
        fields = {}
        for name, token in self.fields.items():
            if token.is_message:
                for subname, subtoken in token.leaf_fields():
                    fields[f'{name}.{subname}'] = subtoken
            else:
                fields[name] = token
        return fields

    def contains_name(self, name: str) -> bool:
        return name in self.fields or name in self.constants

    def get_type_of(self, name: str) -> TypeToken:
        t: TypeToken = self.fields.get(name)
        return t if t is not None else self.constants[name][0]


@frozen
class ArrayType(TypeToken):
    type: DataType = field(init=False, default=DataType.ARRAY)
    subtype: TypeToken
    length: int = field(default=-1, validator=ge(-1))

    @property
    def is_fixed_length(self) -> bool:
        return self.length >= 0

    def contains_index(self, index: int) -> bool:
        return self.length < 0 or self.length > index


###############################################################################
# Exported Constants
###############################################################################

BOOLEANS: Final[EnumeratedType] = EnumeratedType.booleans()
UINT8: Final[RangedType] = RangedType.uint8()
UINT16: Final[RangedType] = RangedType.uint16()
UINT32: Final[RangedType] = RangedType.uint32()
UINT64: Final[RangedType] = RangedType.uint64()
INT8: Final[RangedType] = RangedType.int8()
INT16: Final[RangedType] = RangedType.int16()
INT32: Final[RangedType] = RangedType.int32()
INT64: Final[RangedType] = RangedType.int64()
FLOAT32: Final[RangedType] = RangedType.float32()
FLOAT64: Final[RangedType] = RangedType.float64()
STRINGS: Final[TypeToken] = TypeToken('string', type=DataType.STRING)
