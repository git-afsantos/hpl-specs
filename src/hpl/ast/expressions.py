# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Callable, Iterable, Optional, Set, Tuple, Union

from enum import auto, Flag

from attrs import evolve, field, frozen
from attrs.validators import deep_iterable, instance_of

from hpl.ast.base import HplAstObject
from hpl.errors import HplTypeError, invalid_type

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
    def default_data_type(self) -> DataType:
        return DataType.ANY

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


def _expr_type_converter(t: DataType) -> Callable[[HplExpression], HplExpression]:
    def converter(expr: HplExpression) -> HplExpression:
        return expr.cast(t)
    return converter


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
        t = DataType.NONE
        for value in self.values:
            t = t | value.data_type
        return t

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
    defined_at: Any = None
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

    @property
    def is_defined(self) -> bool:
        return self.defined_at is not None

    def __str__(self) -> str:
        return self.token


###############################################################################
# Quantifiers
###############################################################################


def _convert_quantifier_domain(expr: HplExpression) -> HplExpression:
    return expr.cast(DataType.COMPOUND)


def _convert_quantifier_condition(expr: HplExpression) -> HplExpression:
    return expr.cast(DataType.BOOL)


@frozen
class HplQuantifier(HplExpression):
    quantifier: str
    variable: str
    domain: HplExpression = field(converter=_convert_quantifier_domain)
    condition: HplExpression = field(converter=_convert_quantifier_condition)

    _SET_REF = "cannot reference quantified variable '{}' in the domain of:\n{}"
    _MULTI_DEF = "multiple definitions of variable '{}' in:\n{}"
    _UNUSED = "quantified variable '{}' is never used in:\n{}"

    def __init__(self, qt, var, dom, p, shadow=False):
        HplExpression.__init__(self, types=T_BOOL)
        self._type_check(dom, T_COMP)
        self._type_check(p, T_BOOL)
        self._check_variables(shadow)

    @property
    def is_quantifier(self):
        return True

    @property
    def is_universal(self):
        return self.quantifier == "forall"

    @property
    def is_existential(self):
        return self.quantifier == "exists"

    @property
    def op(self):
        return self.quantifier

    @property
    def x(self):
        return self.variable

    @property
    def d(self):
        return self.domain

    @property
    def p(self):
        return self.condition

    @property
    def phi(self):
        return self.condition

    def children(self):
        return (self.domain, self.condition)

    def clone(self):
        expr = HplQuantifier(self.quantifier, self.variable,
                             self.domain.clone(), self.condition.clone(),
                             shadow=True)
        expr.types = self.types
        return expr

    def _check_variables(self, shadow):
        types = self._check_domain_vars()
        self._check_expression_vars(types, shadow)

    def _check_domain_vars(self):
        dom = self.domain
        for obj in dom.iterate():
            assert obj.is_expression
            if obj.is_value and obj.is_variable:
                assert not obj.is_defined
                v = obj.name
                if self.variable == v:
                    raise HplSanityError(self._SET_REF.format(v, self))
        if dom.is_value:
            if dom.is_set or dom.is_range:
                return dom.subtypes
        return T_PRIM

    def _check_expression_vars(self, t, shadow):
        uid = id(self)
        used = 0
        for obj in self.condition.iterate():
            assert obj.is_expression
            if obj.is_value and obj.is_variable:
                v = obj.name
                if self.variable == v:
                    if obj.is_defined and not shadow:
                        assert obj.defined_at != uid
                        raise HplSanityError(self._MULTI_DEF.format(v, self))
                    obj.defined_at = uid
                    self._type_check(obj, t)
                    used += 1
        if not used:
            raise HplSanityError(self._UNUSED.format(self.variable, self))

    def __eq__(self, other):
        if not isinstance(other, HplQuantifier):
            return False
        return (self.quantifier == other.quantifier
                and self.variable == other.variable
                and self.domain == other.domain
                and self.condition == other.condition)

    def __hash__(self):
        h = 31 * hash(self.quantifier) + hash(self.variable)
        h = 31 * h + hash(self.domain)
        h = 31 * h + hash(self.condition)
        return h

    def __str__(self):
        return "({} {} in {}: {})".format(self.quantifier, self.variable,
            self.domain, self.condition)

    def __repr__(self):
        return "{}({}, {}, {}, {})".format(
            type(self).__name__, repr(self.quantifier), repr(self.variable),
            repr(self.domain), repr(self.condition))


def Forall(x, dom, phi, shadow=False):
    return HplQuantifier("forall", x, dom, phi, shadow=shadow)

def Exists(x, dom, phi, shadow=False):
    return HplQuantifier("exists", x, dom, phi, shadow=shadow)


###############################################################################
# Operators and Functions
###############################################################################

class HplUnaryOperator(HplExpression):
    __slots__ = HplExpression.__slots__ + ("operator", "operand")

    _OPS = {
        "-": (T_NUM, T_NUM),
        "not": (T_BOOL, T_BOOL)
    }

    def __init__(self, op, arg):
        tin, tout = self._OPS[op]
        HplExpression.__init__(self, types=tout)
        self.operator = op # string
        self.operand = arg # HplExpression
        self._type_check(arg, tin)

    @property
    def is_operator(self):
        return True

    @property
    def arity(self):
        return 1

    @property
    def op(self):
        return self.operator

    @property
    def a(self):
        return self.operand

    def children(self):
        return (self.operand,)

    def clone(self):
        expr = HplUnaryOperator(self.operator, self.operand.clone())
        expr.types = self.types
        return expr

    def __eq__(self, other):
        if not isinstance(other, HplUnaryOperator):
            return False
        return (self.operator == other.operator
                and self.operand == other.operand)

    def __hash__(self):
        return 31 * hash(self.operator) + hash(self.operand)

    def __str__(self):
        op = self.operator
        if op and op[-1].isalpha():
            op = op + " "
        return "({}{})".format(op, self.operand)

    def __repr__(self):
        return "{}({}, {})".format(
            type(self).__name__, repr(self.operator), repr(self.operand))


def Not(a):
    return HplUnaryOperator("not", a)


class HplBinaryOperator(HplExpression):
    __slots__ = HplExpression.__slots__ + (
        "operator", "operand1", "operand2", "infix", "commutative")

    # operator: (Input -> Input -> Output), infix, commutative
    _OPS = {
        "+": (T_NUM, T_NUM, T_NUM, True, True),
        "-": (T_NUM, T_NUM, T_NUM, True, False),
        "*": (T_NUM, T_NUM, T_NUM, True, True),
        "/": (T_NUM, T_NUM, T_NUM, True, False),
        "**": (T_NUM, T_NUM, T_NUM, True, False),
        "implies": (T_BOOL, T_BOOL, T_BOOL, True, False),
        "iff": (T_BOOL, T_BOOL, T_BOOL, True, True),
        "or": (T_BOOL, T_BOOL, T_BOOL, True, True),
        "and": (T_BOOL, T_BOOL, T_BOOL, True, True),
        "=": (T_PRIM, T_PRIM, T_BOOL, True, True),
        "!=": (T_PRIM, T_PRIM, T_BOOL, True, True),
        "<": (T_NUM, T_NUM, T_BOOL, True, False),
        "<=": (T_NUM, T_NUM, T_BOOL, True, False),
        ">": (T_NUM, T_NUM, T_BOOL, True, False),
        ">=": (T_NUM, T_NUM, T_BOOL, True, False),
        "in": (T_PRIM, T_SET | T_RAN, T_BOOL, True, False),
    }

    def __init__(self, op, arg1, arg2):
        tin1, tin2, tout, infix, comm = self._OPS[op]
        HplExpression.__init__(self, types=tout)
        self.operator = op # string
        self.operand1 = arg1 # HplExpression
        self.operand2 = arg2 # HplExpression
        self.infix = infix # bool
        self.commutative = comm # bool
        self._type_check(arg1, tin1)
        self._type_check(arg2, tin2)

    @property
    def is_operator(self):
        return True

    @property
    def arity(self):
        return 2

    @property
    def op(self):
        return self.operator

    @property
    def a(self):
        return self.operand1

    @property
    def b(self):
        return self.operand2

    def children(self):
        return (self.operand1, self.operand2)

    def clone(self):
        expr = HplBinaryOperator(self.operator, self.operand1.clone(),
                                 self.operand2.clone())
        expr.types = self.types
        return expr

    def __eq__(self, other):
        if not isinstance(other, HplBinaryOperator):
            return False
        if self.operator != other.operator:
            return False
        a = self.operand1
        b = self.operand2
        x = other.operand1
        y = other.operand2
        if self.commutative:
            return (a == x and b == y) or (a == y and b == x)
        return a == x and b == y

    def __hash__(self):
        h = 31 * hash(self.operator) + hash(self.operand1)
        h = 31 * h + hash(self.operand2)
        return h

    def __str__(self):
        a = str(self.operand1)
        b = str(self.operand2)
        if self.infix:
            return "({} {} {})".format(a, self.operator, b)
        else:
            return "{}({}, {})".format(self.operator, a, b)

    def __repr__(self):
        return "{}({}, {}, {})".format(
            type(self).__name__, repr(self.operator),
            repr(self.operand1), repr(self.operand2))


def And(a, b):
    return HplBinaryOperator("and", a, b)

def Or(a, b):
    return HplBinaryOperator("or", a, b)

def Implies(a, b):
    return HplBinaryOperator("implies", a, b)

def Iff(a, b):
    return HplBinaryOperator("iff", a, b)


FunctionType = namedtuple("FunctionType", ("params", "output"))

Parameters = namedtuple("Parameters", ("types", "var_args"))

def F(*args):
    assert len(args) > 1
    params = Parameters(tuple(args[:-1]), False)
    return FunctionType((params,), args[-1])


class HplFunctionCall(HplExpression):
    __slots__ = HplExpression.__slots__ + ("function", "arguments",)

    _SIG = "function '{}' expects {}, but got {}."

    # name: Input -> Output
    _BUILTINS = {
        "abs":   F(T_NUM, T_NUM),
        "bool":  F(T_PRIM, T_BOOL),
        "int":   F(T_PRIM, T_NUM),
        "float": F(T_PRIM, T_NUM),
        "str":   F(T_PRIM, T_STR),
        "len":   F(T_COMP, T_NUM),
        "sum":   F(T_COMP, T_NUM),
        "prod":  F(T_COMP, T_NUM),
        "sqrt":  F(T_NUM, T_NUM),
        "ceil":  F(T_NUM, T_NUM),
        "floor": F(T_NUM, T_NUM),
        "log":   F(T_NUM, T_NUM, T_NUM),
        "sin":   F(T_NUM, T_NUM),
        "cos":   F(T_NUM, T_NUM),
        "tan":   F(T_NUM, T_NUM),
        "asin":  F(T_NUM, T_NUM),
        "acos":  F(T_NUM, T_NUM),
        "atan":  F(T_NUM, T_NUM),
        "atan2": F(T_NUM, T_NUM, T_NUM),
        "deg":   F(T_NUM, T_NUM),
        "rad":   F(T_NUM, T_NUM),
        "x":     F(T_MSG, T_NUM),
        "y":     F(T_MSG, T_NUM),
        "z":     F(T_MSG, T_NUM),
        "max": FunctionType(
            (Parameters((T_COMP,), False),
             Parameters((T_NUM, T_NUM), True)),
            T_NUM
        ),
        "min": FunctionType(
            (Parameters((T_COMP,), False),
             Parameters((T_NUM, T_NUM), True)),
            T_NUM
        ),
        "gcd": FunctionType(
            (Parameters((T_COMP,), False),
             Parameters((T_NUM, T_NUM), True)),
            T_NUM
        ),
        "roll": FunctionType(
            (Parameters((T_MSG,), False),
             Parameters((T_NUM, T_NUM, T_NUM, T_NUM), False)),
            T_NUM
        ),
        "pitch": FunctionType(
            (Parameters((T_MSG,), False),
             Parameters((T_NUM, T_NUM, T_NUM, T_NUM), False)),
            T_NUM
        ),
        "yaw": FunctionType(
            (Parameters((T_MSG,), False),
             Parameters((T_NUM, T_NUM, T_NUM, T_NUM), False)),
            T_NUM
        ),
    }

    def __init__(self, fun, args):
        try:
            function_type = self._BUILTINS[fun]
        except KeyError:
            raise HplTypeError("undefined function '{}'".format(fun))
        HplExpression.__init__(self, types=function_type.output)
        self.function = fun # string
        self.arguments = args # [HplValue]
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
