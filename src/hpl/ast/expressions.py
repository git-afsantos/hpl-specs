# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Callable, Final, Iterable, Optional, Set, Tuple, Type, Union

from enum import Enum, auto, Flag, unique

from attrs import evolve, field, frozen
from attrs.validators import deep_iterable, instance_of

from hpl.ast.base import HplAstObject
from hpl.errors import HplSanityError, HplTypeError
from hpl.grammar import ALL_OPERATOR, AND_OPERATOR, IFF_OPERATOR, IMPLIES_OPERATOR, IN_OPERATOR, NOT_OPERATOR, OR_OPERATOR, SOME_OPERATOR

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

    @property
    def is_expression(self) -> bool:
        return True

    @property
    def is_value(self) -> bool:
        return False

    @property
    def is_operator(self) -> bool:
        return False

    @property
    def is_function_call(self) -> bool:
        return False

    @property
    def is_quantifier(self) -> bool:
        return False

    @property
    def is_accessor(self) -> bool:
        return False

    @property
    def can_be_bool(self) -> bool:
        return self.data_type.can_be_bool

    @property
    def can_be_number(self) -> bool:
        return self.data_type.can_be_number

    @property
    def can_be_string(self) -> bool:
        return self.data_type.can_be_string

    @property
    def can_be_array(self) -> bool:
        return self.data_type.can_be_array

    @property
    def can_be_set(self) -> bool:
        return self.data_type.can_be_set

    @property
    def can_be_range(self) -> bool:
        return self.data_type.can_be_range

    @property
    def can_be_message(self) -> bool:
        return self.data_type.can_be_message

    def can_be(self, t: DataType) -> bool:
        return self.data_type.can_be(t)

    def is_fully_typed(self) -> bool:
        for obj in self.iterate():
            t: DataType = obj.data_type
            if (not t) or (t == DataType.ANY):
                return False
        return True

    def cast(self, t: DataType) -> 'HplExpression':
        try:
            r: DataType = self.data_type.cast(t)
            return evolve(self, data_type=r)
        except TypeError as e:
            raise HplTypeError.in_expr(self, str(e))

    def _type_check(self, expr: 'HplExpression', t: DataType):
        try:
            expr.data_type.cast(t)
        except TypeError as e:
            raise HplTypeError.in_expr(self, str(e))

    def external_references(self) -> Set[str]:
        refs: Set[str] = set()
        for obj in self.iterate():
            assert obj.is_expression
            if obj.is_accessor:
                if obj.is_field and obj.message.is_value:
                    if obj.message.is_variable:
                        refs.add(obj.message.name)
        return refs

    def contains_reference(self, alias: str) -> bool:
        for obj in self.iterate():
            assert obj.is_expression
            if obj.is_value and obj.is_variable:
                if obj.name == alias:
                    return True
        return False

    def contains_self_reference(self) -> bool:
        for obj in self.iterate():
            assert obj.is_expression
            if obj.is_value and obj.is_this_msg:
                return True
        return False

    def contains_definition(self, alias: str) -> bool:
        for obj in self.iterate():
            assert obj.is_expression
            if obj.is_quantifier:
                if obj.variable == alias:
                    return True
        return False


def _type_checker(t: DataType) -> Callable[[HplExpression, Any, HplExpression], None]:
    def validator(self: HplExpression, _attribute: Any, expr: HplExpression):
        self._type_check(expr, t)
    return validator


###############################################################################
# Values
###############################################################################


@frozen
class HplValue(HplExpression):
    @property
    def is_value(self) -> bool:
        return True

    @property
    def is_literal(self) -> bool:
        return False

    @property
    def is_set(self) -> bool:
        return False

    @property
    def is_range(self) -> bool:
        return False

    @property
    def is_reference(self) -> bool:
        return False

    @property
    def is_variable(self) -> bool:
        return False

    @property
    def is_this_msg(self) -> bool:
        return False


###############################################################################
# Compound Values
###############################################################################


def _convert_set_values(values: Iterable[HplExpression]) -> Tuple[HplExpression]:
    return tuple(v.cast(DataType.PRIMITIVE) for v in values)


@frozen
class HplSet(HplValue):
    values: Tuple[HplValue] = field(
        converter=_convert_set_values,
        validator=deep_iterable(instance_of(HplValue)),
    )

    @property
    def default_data_type(self) -> DataType:
        return DataType.SET

    @property
    def is_set(self) -> bool:
        return True

    @property
    def subtypes(self) -> DataType:
        return DataType.union(value.data_type for value in self.values)

    def to_set(self) -> Set[HplValue]:
        return set(self.values)

    def children(self) -> Tuple[HplValue]:
        return self.values

    def __str__(self) -> str:
        return f'{{{", ".join(str(v) for v in self.values)}}}'


def _convert_range_bounds(value: HplExpression) -> HplExpression:
    return value.cast(DataType.NUMBER)


@frozen
class HplRange(HplValue):
    min_value: HplValue = field(converter=_convert_range_bounds, validator=instance_of(HplValue))
    max_value: HplValue = field(converter=_convert_range_bounds, validator=instance_of(HplValue))
    exclude_min: bool = False
    exclude_max: bool = False

    @property
    def default_data_type(self) -> DataType:
        return DataType.RANGE

    @property
    def is_range(self) -> bool:
        return True

    @property
    def subtypes(self) -> DataType:
        return DataType.NUMBER

    def children(self) -> Tuple[HplValue]:
        return (self.min_value, self.max_value)

    def __str__(self) -> str:
        lp = '![' if self.exclude_min else '['
        rp = ']!' if self.exclude_max else ']'
        lb = str(self.min_value)
        ub = str(self.max_value)
        return f'{lp}{lb} to {ub}{rp}'


###############################################################################
# Atomic Values
###############################################################################


@frozen
class HplLiteral(HplValue):
    token: str
    value: Union[bool, int, float, str] = field(validator=instance_of((bool, int, float, str)))

    @property
    def default_data_type(self) -> DataType:
        if self.value is True or self.value is False:
            return DataType.BOOL
        if isinstance(self.value, str):
            return DataType.STRING
        return DataType.NUMBER

    @property
    def is_literal(self) -> bool:
        return True

    def __str__(self) -> str:
        return self.token


@frozen
class HplThisMessage(HplValue):
    message_type: Any = None

    @property
    def default_data_type(self) -> DataType:
        return DataType.MESSAGE

    @property
    def is_reference(self) -> bool:
        return True

    @property
    def is_this_msg(self) -> bool:
        return True

    def __str__(self) -> str:
        return ''


@frozen
class HplVarReference(HplValue):
    token: str
    message_type: Any = None

    @property
    def default_data_type(self) -> DataType:
        return DataType.ITEM

    @property
    def is_reference(self) -> bool:
        return True

    @property
    def is_variable(self) -> bool:
        return True

    @property
    def name(self) -> str:
        return self.token[1:]  # remove lead "@"

    def __str__(self) -> str:
        return self.token


###############################################################################
# Quantifiers
###############################################################################


class QuantifierType(Enum):
    ALL = ALL_OPERATOR
    SOME = SOME_OPERATOR

    @property
    def name(self) -> str:
        return self.value

    @property
    def token(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


def _convert_quantifier_type(t: Union[str, QuantifierType]) -> QuantifierType:
    return t if isinstance(t, QuantifierType) else QuantifierType(t)


def _convert_quantifier_domain(expr: HplExpression) -> HplExpression:
    return expr.cast(DataType.COMPOUND)


def _convert_quantifier_condition(expr: HplExpression) -> HplExpression:
    return expr.cast(DataType.BOOL)


@frozen
class HplQuantifier(HplExpression):
    quantifier: QuantifierType = field(converter=_convert_quantifier_type)
    variable: str
    domain: HplExpression = field(converter=_convert_quantifier_domain)
    condition: HplExpression = field(converter=_convert_quantifier_condition)

    @classmethod
    def forall(cls, var: str, dom: HplExpression, phi: HplExpression ) -> 'HplQuantifier':
        return cls(quantifier=QuantifierType.ALL, variable=var, domain=dom, condition=phi)

    @classmethod
    def exists(cls, var: str, dom: HplExpression, phi: HplExpression) -> 'HplQuantifier':
        return cls(quantifier=QuantifierType.SOME, variable=var, domain=dom, condition=phi)

    @domain.validator
    def _check_domain(self, _attribute, domain: HplExpression):
        # 1. must be a compound type
        self._type_check(domain, DataType.COMPOUND)

        # 2. must not reference the quantified variable
        for obj in domain.iterate():
            assert obj.is_expression
            if obj.is_value and obj.is_variable:
                # assert not obj.is_defined
                if self.variable == obj.name:
                    raise HplSanityError((
                        f"cannot reference quantified variable '{obj.name}'"
                        f" in the domain of «{self}»"
                    ))

    @condition.validator
    def _check_condition_is_bool(self, _attribute, condition: HplExpression):
        # 1. must be a boolean expression
        self._type_check(condition, DataType.BOOL)

        # 2. must not redefine the quantified variable
        # 3. must assume the variable is of the type of domain elements
        v: str = self.variable
        t: DataType = DataType.PRIMITIVE
        if self.domain.is_value and (self.domain.is_set or self.domain.is_range):
            t = self.domain.subtypes
        used: int = 0

        for obj in condition.iterate():
            assert obj.is_expression
            if obj.is_quantifier:
                if obj.variable == v:
                    raise HplSanityError(f"multiple definitions of variable '{v}' in «{self}»")
            elif obj.is_value and obj.is_variable:
                if obj.name == v:
                    self._type_check(obj, t)
                    used += 1

        # 4. must reference the quantified variable at least once
        if not used:
            raise HplSanityError(f"quantified variable '{v}' is never used in «{self}»")

    @property
    def default_data_type(self) -> DataType:
        return DataType.BOOL

    @property
    def is_quantifier(self) -> bool:
        return True

    @property
    def is_universal(self) -> bool:
        return self.quantifier is QuantifierType.ALL

    @property
    def is_existential(self):
        return self.quantifier is QuantifierType.SOME

    @property
    def op(self) -> QuantifierType:
        return self.quantifier

    @property
    def x(self) -> str:
        return self.variable

    @property
    def d(self) -> HplExpression:
        return self.domain

    @property
    def p(self) -> HplExpression:
        return self.condition

    @property
    def phi(self) -> HplExpression:
        return self.condition

    def children(self) -> Tuple[HplExpression, HplExpression]:
        return (self.domain, self.condition)

    def __str__(self) -> str:
        return f'({self.op} {self.x} in {self.d}: {self.p})'


Forall: Final[Callable[[str, HplExpression, HplExpression], HplQuantifier]] = HplQuantifier.forall
Exists: Final[Callable[[str, HplExpression, HplExpression], HplQuantifier]] = HplQuantifier.exists


###############################################################################
# Operators and Functions
###############################################################################


@frozen
class UnaryOperatorDefinition:
    token: str
    parameter: DataType
    result: DataType

    @classmethod
    def minus(cls) -> 'UnaryOperatorDefinition':
        return cls('-', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def negation(cls) -> 'UnaryOperatorDefinition':
        return cls(NOT_OPERATOR, DataType.BOOL, DataType.BOOL)

    @property
    def name(self) -> str:
        return self.token

    def __str__(self) -> str:
        return self.token


@unique
class BuiltinUnaryOperator(Enum):
    '''Set of built-in operators.'''

    MINUS = UnaryOperatorDefinition.minus()
    NOT = UnaryOperatorDefinition.negation()

    @property
    def name(self) -> str:
        return self.value.token

    @property
    def token(self) -> str:
        return self.value.token

    def __str__(self) -> str:
        return self.value.token


def _convert_unary_operator(
    op: Union[str, BuiltinUnaryOperator, UnaryOperatorDefinition]
) -> UnaryOperatorDefinition:
    if isinstance(op, UnaryOperatorDefinition):
        return op
    if isinstance(op, BuiltinUnaryOperator):
        return op.value
    for member in BuiltinUnaryOperator.__members__.values():
        if member.token == op:
            return member
    raise ValueError(f'{op!r} is not a valid unary operator')


@frozen
class HplUnaryOperator(HplExpression):
    operator: UnaryOperatorDefinition = field(converter=_convert_unary_operator)
    operand: HplExpression = field(validator=instance_of(HplExpression))

    @classmethod
    def minus(cls, operand: HplExpression) -> 'HplUnaryOperator':
        return cls(operator=BuiltinUnaryOperator.MINUS, operand=operand)

    @classmethod
    def negation(cls, operand: HplExpression) -> 'HplUnaryOperator':
        return cls(operator=BuiltinUnaryOperator.NOT, operand=operand)

    @operand.validator
    def _check_operand(self, _attribute, arg: HplExpression):
        self._type_check(arg, self.operator.parameter)

    def __attrs_post_init__(self):
        object.__setattr__(self, 'data_type', self.operator.result)

    @property
    def is_operator(self) -> bool:
        return True

    @property
    def arity(self) -> int:
        return 1

    @property
    def op(self) -> UnaryOperatorDefinition:
        return self.operator

    @property
    def a(self) -> HplExpression:
        return self.operand

    @property
    def parameter_type(self) -> DataType:
        return self.operator.parameter

    def children(self) -> Tuple[HplExpression]:
        return (self.operand,)

    def __str__(self) -> str:
        op: str = self.operator.token
        if op and op[-1].isalpha():
            op = op + ' '
        return f'({op}{self.operand})'


Not: Final[Callable[[HplExpression], HplUnaryOperator]] = HplUnaryOperator.negation


@frozen
class BinaryOperatorDefinition:
    token: str
    parameter1: DataType
    parameter2: DataType
    result: DataType
    infix: bool = True
    commutative: bool = False

    @classmethod
    def addition(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('+', t, t, t, infix=True, commutative=True)

    @classmethod
    def subtraction(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('-', t, t, t, infix=True, commutative=False)

    @classmethod
    def multiplication(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('*', t, t, t, infix=True, commutative=True)

    @classmethod
    def division(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('/', t, t, t, infix=True, commutative=False)

    @classmethod
    def power(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('**', t, t, t, infix=True, commutative=False)

    @classmethod
    def implication(cls) -> 'BinaryOperatorDefinition':
        t = DataType.BOOL
        return cls(IMPLIES_OPERATOR, t, t, t, infix=True, commutative=False)

    @classmethod
    def equivalence(cls) -> 'BinaryOperatorDefinition':
        t = DataType.BOOL
        return cls(IFF_OPERATOR, t, t, t, infix=True, commutative=True)

    @classmethod
    def disjunction(cls) -> 'BinaryOperatorDefinition':
        t = DataType.BOOL
        return cls(OR_OPERATOR, t, t, t, infix=True, commutative=True)

    @classmethod
    def conjunction(cls) -> 'BinaryOperatorDefinition':
        t = DataType.BOOL
        return cls(AND_OPERATOR, t, t, t, infix=True, commutative=True)

    @classmethod
    def equality(cls) -> 'BinaryOperatorDefinition':
        t = DataType.PRIMITIVE
        return cls('=', t, t, DataType.BOOL, infix=True, commutative=True)

    @classmethod
    def inequality(cls) -> 'BinaryOperatorDefinition':
        t = DataType.PRIMITIVE
        return cls('!=', t, t, DataType.BOOL, infix=True, commutative=True)

    @classmethod
    def less_than(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('<', t, t, DataType.BOOL, infix=True, commutative=False)

    @classmethod
    def less_than_eq(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('<=', t, t, DataType.BOOL, infix=True, commutative=False)

    @classmethod
    def greater_than(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('>', t, t, DataType.BOOL, infix=True, commutative=False)

    @classmethod
    def greater_than_eq(cls) -> 'BinaryOperatorDefinition':
        t = DataType.NUMBER
        return cls('>=', t, t, DataType.BOOL, infix=True, commutative=False)

    @classmethod
    def inclusion(cls) -> 'BinaryOperatorDefinition':
        t1 = DataType.PRIMITIVE
        t2 = DataType.COMPOUND
        t3 = DataType.BOOL
        return cls(IN_OPERATOR, t1, t2, t3, infix=True, commutative=False)

    @property
    def name(self) -> str:
        return self.token

    @property
    def parameters(self) -> Tuple[DataType, DataType]:
        return (self.parameter1, self.parameter2)

    def __str__(self) -> str:
        return self.token


@unique
class BuiltinBinaryOperator(Enum):
    '''Set of supported operators.'''

    ADD = BinaryOperatorDefinition.addition()
    SUB = BinaryOperatorDefinition.subtraction()
    MULT = BinaryOperatorDefinition.multiplication()
    DIV = BinaryOperatorDefinition.division()
    POW = BinaryOperatorDefinition.power()
    IMP = BinaryOperatorDefinition.implication()
    IFF = BinaryOperatorDefinition.equivalence()
    OR = BinaryOperatorDefinition.disjunction()
    AND = BinaryOperatorDefinition.conjunction()
    EQ = BinaryOperatorDefinition.equality()
    NEQ = BinaryOperatorDefinition.inequality()
    LT = BinaryOperatorDefinition.less_than()
    LTE = BinaryOperatorDefinition.less_than_eq()
    GT = BinaryOperatorDefinition.greater_than()
    GTE = BinaryOperatorDefinition.greater_than_eq()
    IN = BinaryOperatorDefinition.inclusion()

    @property
    def name(self) -> str:
        return self.value.token

    @property
    def token(self) -> str:
        return self.value.token

    def __str__(self) -> str:
        return self.value.token


def _convert_binary_operator(
    op: Union[str, BuiltinBinaryOperator, BinaryOperatorDefinition]
) -> BinaryOperatorDefinition:
    if isinstance(op, BinaryOperatorDefinition):
        return op
    if isinstance(op, BuiltinBinaryOperator):
        return op.value
    for member in BuiltinBinaryOperator.__members__.values():
        if member.token == op:
            return member
    raise ValueError(f'{op!r} is not a valid binary operator')


@frozen
class HplBinaryOperator(HplExpression):
    operator: BinaryOperatorDefinition = field(converter=_convert_binary_operator)
    operand1: HplExpression = field(validator=instance_of(HplExpression))
    operand2: HplExpression = field(validator=instance_of(HplExpression))

    @classmethod
    def conjunction(cls, a: HplExpression, b: HplExpression) -> 'HplBinaryOperator':
        return cls(operator=BuiltinBinaryOperator.AND, operand1=a, operand2=b)

    @classmethod
    def disjunction(cls, a: HplExpression, b: HplExpression) -> 'HplBinaryOperator':
        return cls(operator=BuiltinBinaryOperator.OR, operand1=a, operand2=b)

    @classmethod
    def implication(cls, a: HplExpression, b: HplExpression) -> 'HplBinaryOperator':
        return cls(operator=BuiltinBinaryOperator.IMP, operand1=a, operand2=b)

    @classmethod
    def equivalence(cls, a: HplExpression, b: HplExpression) -> 'HplBinaryOperator':
        return cls(operator=BuiltinBinaryOperator.IFF, operand1=a, operand2=b)

    @operand1.validator
    def _check_operand1(self, _attribute, arg: HplExpression):
        self._type_check(arg, self.operator.parameter1)

    @operand2.validator
    def _check_operand2(self, _attribute, arg: HplExpression):
        self._type_check(arg, self.operator.parameter2)

    def __attrs_post_init__(self):
        object.__setattr__(self, 'data_type', self.operator.result)

    @property
    def is_operator(self) -> bool:
        return True

    @property
    def arity(self) -> int:
        return 2

    @property
    def op(self) -> BinaryOperatorDefinition:
        return self.operator

    @property
    def a(self) -> HplExpression:
        return self.operand1

    @property
    def b(self) -> HplExpression:
        return self.operand2

    @property
    def is_infix(self) -> bool:
        return self.operator.infix

    @property
    def is_commutative(self) -> bool:
        return self.operator.commutative

    @property
    def parameter1_type(self) -> DataType:
        return self.operator.parameter1

    @property
    def parameter2_type(self) -> DataType:
        return self.operator.parameter2

    def children(self) -> Tuple[HplExpression, HplExpression]:
        return (self.operand1, self.operand2)

    def __str__(self) -> str:
        if self.is_infix:
            return f'({self.operand1} {self.operator} {self.operand2})'
        else:
            return f'{self.operator}({self.operand1}, {self.operand2})'


# necessary alias to shorten the following lines
BinOp: Final[Type[HplBinaryOperator]] = HplBinaryOperator

And: Final[Callable[[HplExpression, HplExpression], HplBinaryOperator]] = BinOp.conjunction
Or: Final[Callable[[HplExpression, HplExpression], HplBinaryOperator]] = BinOp.disjunction
Implies: Final[Callable[[HplExpression, HplExpression], HplBinaryOperator]] = BinOp.implication
Iff: Final[Callable[[HplExpression, HplExpression], HplBinaryOperator]] = BinOp.equivalence


@frozen
class FunctionSignature:
    '''Each of these objects represents a function overload.'''

    parameters: Tuple[DataType]
    result: DataType
    variadic: Optional[DataType] = None  # type of variadic parameters

    @property
    def is_variadic(self) -> bool:
        return self.variadic is not None

    @property
    def arity(self) -> int:
        return len(self.parameters)

    def accepts(self, args: Iterable[DataType]) -> bool:
        if not isinstance(args, (tuple, list)):
            args = tuple(args)
        n = len(args)
        arity = self.arity
        if arity > n:
            return False
        if arity < n and not self.is_variadic:
            return False
        for arg, param in zip(args, self.parameters):
            if not arg.can_be(param):
                return False
        if self.is_variadic:
            i = min(n, arity)
            for arg in args[i:]:
                if not arg.can_be(self.variadic):
                    return False
        return True


@frozen
class FunctionDefinition:
    name: str
    overloads: Tuple[FunctionSignature]

    @property
    def result(self) -> DataType:
        return DataType.union(sig.result for sig in self.overloads)
    
    def get_parameter_type_string(self) -> str:
        result = []
        for sig in self.overloads:
            types = sig.parameters
            if sig.is_variadic:
                types = types + (f'*{sig.variadic}')
            result.append(f'({", ".join(types)})')
        return ' or '.join(result)

    @classmethod
    def f(cls, name: str, *args: Iterable[DataType]) -> 'FunctionDefinition':
        if not args:
            raise ValueError('must provide at least a return type')
        params = tuple(args[:-1])
        result = args[-1]
        sig = FunctionSignature(params, result)
        return cls(name, (sig,))

    @classmethod
    def abs(cls) -> 'FunctionDefinition':
        return cls.f('abs', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def to_bool(cls) -> 'FunctionDefinition':
        return cls.f('bool', DataType.PRIMITIVE, DataType.BOOL)

    @classmethod
    def to_int(cls) -> 'FunctionDefinition':
        return cls.f('int', DataType.PRIMITIVE, DataType.NUMBER)

    @classmethod
    def to_float(cls) -> 'FunctionDefinition':
        return cls.f('float', DataType.PRIMITIVE, DataType.NUMBER)

    @classmethod
    def to_string(cls) -> 'FunctionDefinition':
        return cls.f('str', DataType.PRIMITIVE, DataType.STRING)

    @classmethod
    def length(cls) -> 'FunctionDefinition':
        return cls.f('len', DataType.COMPOUND, DataType.NUMBER)

    @classmethod
    def sum(cls) -> 'FunctionDefinition':
        return cls.f('sum', DataType.COMPOUND, DataType.NUMBER)

    @classmethod
    def product(cls) -> 'FunctionDefinition':
        return cls.f('prod', DataType.COMPOUND, DataType.NUMBER)

    @classmethod
    def sqrt(cls) -> 'FunctionDefinition':
        return cls.f('sqrt', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def ceil(cls) -> 'FunctionDefinition':
        return cls.f('ceil', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def floor(cls) -> 'FunctionDefinition':
        return cls.f('floor', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def log(cls) -> 'FunctionDefinition':
        return cls.f('log', DataType.NUMBER, DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def sin(cls) -> 'FunctionDefinition':
        return cls.f('sin', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def cos(cls) -> 'FunctionDefinition':
        return cls.f('cos', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def tan(cls) -> 'FunctionDefinition':
        return cls.f('tan', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def asin(cls) -> 'FunctionDefinition':
        return cls.f('asin', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def acos(cls) -> 'FunctionDefinition':
        return cls.f('acos', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def atan(cls) -> 'FunctionDefinition':
        return cls.f('atan', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def atan2(cls) -> 'FunctionDefinition':
        return cls.f('atan2', DataType.NUMBER, DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def degrees(cls) -> 'FunctionDefinition':
        return cls.f('deg', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def radians(cls) -> 'FunctionDefinition':
        return cls.f('rad', DataType.NUMBER, DataType.NUMBER)

    @classmethod
    def max(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.COMPOUND,), num)
        sig2 = FunctionSignature((num, num,), num, variadic=DataType.NUMBER)
        return cls('max', (sig1, sig2))

    @classmethod
    def min(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.COMPOUND,), num)
        sig2 = FunctionSignature((num, num,), num, variadic=DataType.NUMBER)
        return cls('min', (sig1, sig2))

    @classmethod
    def gcd(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.COMPOUND,), num)
        sig2 = FunctionSignature((num, num,), num, variadic=DataType.NUMBER)
        return cls('gcd', (sig1, sig2))

    @classmethod
    def roll(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.MESSAGE,), num)
        sig2 = FunctionSignature((num, num, num, num), num)
        return cls('roll', (sig1, sig2))

    @classmethod
    def pitch(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.MESSAGE,), num)
        sig2 = FunctionSignature((num, num, num, num), num)
        return cls('pitch', (sig1, sig2))

    @classmethod
    def yaw(cls) -> 'FunctionDefinition':
        num = DataType.NUMBER
        sig1 = FunctionSignature((DataType.MESSAGE,), num)
        sig2 = FunctionSignature((num, num, num, num), num)
        return cls('yaw', (sig1, sig2))


@unique
class BuiltinFunction(Enum):
    '''Set of built-in functions.'''

    ABS = FunctionDefinition.abs()
    BOOL = FunctionDefinition.to_bool()
    INT = FunctionDefinition.to_int()
    FLOAT = FunctionDefinition.to_float()
    STRING = FunctionDefinition.to_string()
    LENGTH = FunctionDefinition.length()
    SUM = FunctionDefinition.sum()
    PRODUCT = FunctionDefinition.product()
    SQRT = FunctionDefinition.sqrt()
    CEIL = FunctionDefinition.ceil()
    FLOOR = FunctionDefinition.floor()
    LOG = FunctionDefinition.log()
    SIN = FunctionDefinition.sin()
    COS = FunctionDefinition.cos()
    TAN = FunctionDefinition.tan()
    ASIN = FunctionDefinition.asin()
    ACOS = FunctionDefinition.acos()
    ATAN = FunctionDefinition.atan()
    ATAN2 = FunctionDefinition.atan2()
    DEG = FunctionDefinition.degrees()
    RAD = FunctionDefinition.radians()
    MAX = FunctionDefinition.max()
    MIN = FunctionDefinition.min()
    GCD = FunctionDefinition.gcd()
    ROLL = FunctionDefinition.roll()
    PITCH = FunctionDefinition.pitch()
    YAW = FunctionDefinition.yaw()


def _convert_function_def(
    fun: Union[str, BuiltinFunction, FunctionDefinition]
) -> FunctionDefinition:
    if isinstance(fun, FunctionDefinition):
        return fun
    if isinstance(fun, BuiltinFunction):
        return fun.value
    for member in BuiltinFunction.__members__.values():
        if member.name == fun:
            return member
    raise ValueError(f'{fun!r} is not a valid function')


@frozen
class HplFunctionCall(HplExpression):
    function: FunctionDefinition = field(converter=_convert_function_def)
    arguments: Tuple[HplExpression] = field(converter=tuple)

    @arguments.validator
    def _check_arguments(self, _attribute, args: Tuple[HplExpression]):
        types = tuple(arg.data_type for arg in args)
        for sig in self.function.overloads:
            if not sig.accepts(types):
                continue
            return
        expected = self.function.get_parameter_type_string()
        raise HplTypeError.in_expr(self, f'arguments do not match {expected}')

    def __attrs_post_init__(self):
        object.__setattr__(self, 'data_type', self.function.result)

    _SIG = "function '{}' expects {}, but got {}."

    def __init__(self, fun, args):
        HplExpression.__init__(self, types=function_type.output)
        self._type_check_args(function_type)

    @property
    def is_function_call(self):
        return True

    @property
    def arity(self):
        return len(self.arguments)

    def children(self):
        return self.arguments

    def clone(self):
        expr = HplFunctionCall(self.function,
                               tuple(a.clone() for a in self.arguments))
        expr.types = self.types
        return expr

    def _type_check_args(self, function_type):
        args = self.arguments
        nargs = len(args)
        for params in function_type.params:
            if params.var_args:
                if self._match_with_var_args(params):
                    return True
            else:
                if self._match_normal(params):
                    return True
        raise HplTypeError(self._error_msg(function_type.params))

    def _match_with_var_args(self, params):
        args = self.arguments
        nargs = len(args)
        nparams = len(params.types)
        if nargs < nparams:
            return False
        for i in range(nparams):
            t = params.types[i]
            if not args[i].can_be(t):
                return False
        # repeat the last type indefinitely
        for i in range(nparams, nargs):
            t = params.types[-1]
            if not args[i].can_be(t):
                return False
        # by this point, everything matches; commit the changes
        for i in range(nparams):
            t = params.types[i]
            self._type_check(args[i], t)
        for i in range(nparams, nargs):
            t = params.types[-1]
            self._type_check(args[i], t)
        return True

    def _match_normal(self, params):
        args = self.arguments
        nargs = len(args)
        nparams = len(params.types)
        if nargs != nparams:
            return False
        for i in range(nparams):
            t = params.types[i]
            if not args[i].can_be(t):
                return False
        # by this point, everything matches; commit the changes
        for i in range(nparams):
            t = params.types[i]
            self._type_check(args[i], t)
        return True

    def _error_msg(self, overloads):
        # function '{}' expects {}, but got {}.
        sigs = []
        for params in overloads:
            sigs.append("({}{})".format(
                ", ".join(type_name(t) for t in params.types),
                "*" if params.var_args else ""
            ))
        sigs = " or ".join(sigs)
        args = "({})".format(", ".join(type_name(arg.types)
                             for arg in self.arguments))
        return self._SIG.format(self.function, sigs, args)

    def __eq__(self, other):
        if not isinstance(other, HplFunctionCall):
            return False
        return (self.function == other.function
                and self.arguments == other.arguments)

    def __hash__(self):
        return 31 * hash(self.function) + hash(self.arguments)

    def __str__(self):
        return "{}({})".format(self.function,
            ", ".join(str(arg) for arg in self.arguments))

    def __repr__(self):
        return "{}({}, {})".format(
            type(self).__name__, repr(self.function), repr(self.arguments))


###############################################################################
# Message Field Access
###############################################################################

class HplFieldAccess(HplExpression):
    __slots__ = HplExpression.__slots__ + ("message", "field", "ros_type")

    def __init__(self, msg, field):
        HplExpression.__init__(self, types=T_ROS)
        self.message = msg # HplExpression
        self.field = field # string
        self.ros_type = None
        self._type_check(msg, T_MSG)

    @property
    def is_accessor(self):
        return True

    @property
    def is_field(self):
        return True

    @property
    def is_indexed(self):
        return False

    def base_message(self):
        obj = self
        while obj.is_accessor:
            obj = obj.message
        assert obj.is_value
        return obj

    def children(self):
        return (self.message,)

    def __str__(self):
        return str(self.field) if not self.message else f'{self.message}.{self.field}'


class HplArrayAccess(HplExpression):
    __slots__ = HplExpression.__slots__ + ("array", "item", "ros_type")

    _MULTI_ARRAY = "multi-dimensional array access: '{}[{}]'"

    def __init__(self, array, index):
        if array.is_accessor and array.is_indexed:
            raise HplTypeError(self._MULTI_ARRAY.format(array, index))
        HplExpression.__init__(self, types=T_ITEM)
        self.array = array # HplExpression
        self.index = index # HplExpression
        self.ros_type = None
        self._type_check(array, T_ARR)
        self._type_check(index, T_NUM)

    @property
    def is_accessor(self):
        return True

    @property
    def is_field(self):
        return False

    @property
    def is_indexed(self):
        return True

    @property
    def message(self):
        return self.array

    def base_message(self):
        obj = self
        while obj.is_accessor:
            obj = obj.message
        assert obj.is_value
        return obj

    def children(self):
        return (self.array, self.index)

    def clone(self):
        expr = HplArrayAccess(self.array.clone(), self.index.clone())
        expr.ros_type = self.ros_type
        expr.types = self.types
        return expr

    def __eq__(self, other):
        if not isinstance(other, HplArrayAccess):
            return False
        return (self.array == other.array
                and self.index == other.index)

    def __hash__(self):
        return 31 * hash(self.array) + hash(self.index)

    def __str__(self):
        return "{}[{}]".format(self.array, self.index)

    def __repr__(self):
        return "{}({}, {})".format(
            type(self).__name__, repr(self.array), repr(self.index))
