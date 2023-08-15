# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from enum import Enum
import math
from typing import Tuple

from attrs import frozen
from hpl.ast.base import HplAstObject
from hpl.ast.expressions import HplExpression
from lark import Lark, Transformer
from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from hpl.ast import (
    HplSpecification, HplProperty, HplScope, HplPattern, HplSimpleEvent,
    HplPredicate, HplVacuousTruth, HplQuantifier,
    HplUnaryOperator, HplBinaryOperator, HplSet, HplRange, HplLiteral,
    HplVarReference, HplFunctionCall, HplFieldAccess, HplArrayAccess,
    HplThisMessage, HplEventDisjunction
)
from hpl.grammar import PREDICATE_GRAMMAR, HPL_GRAMMAR
from hpl.errors import HplSyntaxError

###############################################################################
# Constants
###############################################################################

INF = float("inf")
NAN = float("nan")


class NumberConstants(Enum):
    PI = math.pi
    INF = INF
    NAN = NAN
    E = math.e


###############################################################################
# Transformer
###############################################################################


class PropertyTransformer(Transformer):
    def hpl_file(self, children):
        return HplSpecification(children)

    def hpl_property(self, children):
        assert len(children) == 2 or len(children) == 3
        if len(children) == 3:
            meta, scope, pattern = children
        else:
            meta = {}
            scope, pattern = children
        hpl_property = HplProperty(scope, pattern, meta=meta)
        hpl_property.sanity_check()
        return hpl_property

    def metadata(self, children):
        metadata = {}
        pid = None
        dup = None
        for key, value in children:
            if key == "id":
                pid = value
            if key in metadata:
                dup = key
            metadata[key] = value
        if dup is not None:
            raise HplSyntaxError.duplicate_metadata(dup, pid=pid)
        return metadata

    def metadata_id(self, children):
        assert len(children) == 1
        data = children[0]
        return ("id", data)

    def metadata_title(self, children):
        assert len(children) == 1
        data = children[0]
        return ("title", data)

    def metadata_desc(self, children):
        assert len(children) == 1
        data = children[0]
        return ("description", data)

    def global_scope(self, children):
        assert not children
        return HplScope.globally()

    def after_until(self, children):
        assert len(children) == 1 or len(children) == 2
        p = children[0]
        if len(children) == 2:
            return HplScope.after_until(p, children[1])
        return HplScope.after(p)

    def until(self, children):
        event = children[0]
        return HplScope.until(event)

    def activator(self, children):
        event = children[0]
        return event

    def terminator(self, children):
        event = children[0]
        return event

    def existence(self, children):
        assert len(children) == 1 or len(children) == 2
        b = children[0]
        max_time = INF if len(children) == 1 else children[1]
        return HplPattern.existence(b, max_time=max_time)

    def absence(self, children):
        assert len(children) == 1 or len(children) == 2
        b = children[0]
        max_time = INF if len(children) == 1 else children[1]
        return HplPattern.absence(b, max_time=max_time)

    def response(self, children):
        assert len(children) == 2 or len(children) == 3
        a = children[0]
        b = children[1]
        max_time = INF if len(children) == 2 else children[2]
        return HplPattern.response(a, b, max_time=max_time)

    def prevention(self, children):
        assert len(children) == 2 or len(children) == 3
        a = children[0]
        b = children[1]
        max_time = INF if len(children) == 2 else children[2]
        return HplPattern.prevention(a, b, max_time=max_time)

    def requirement(self, children):
        assert len(children) == 2 or len(children) == 3
        b = children[0]
        a = children[1]
        max_time = INF if len(children) == 2 else children[2]
        return HplPattern.requirement(b, a, max_time=max_time)

    def event_disjunction(self, children):
        assert len(children) >= 2
        if len(children) == 2:
            return HplEventDisjunction(children[0], children[1])
        else:
            return HplEventDisjunction(
                children[0], self.event_disjunction(children[1:]))

    def event(self, children):
        assert len(children) == 1 or len(children) == 2
        ros_name, alias = children[0]
        phi = HplVacuousTruth() if len(children) == 1 else children[1]
        return HplSimpleEvent.publish(ros_name, alias=alias, predicate=phi)

    def message(self, children):
        alias = None if len(children) == 1 else children[1]
        return (children[0], alias)

    def predicate(self, children):
        expr = children[0]
        return HplPredicate(expr)

    def top_level_condition(self, children):
        expr = children[0]
        # TODO remove, just for debugging
        phi = HplPredicate(expr)
        return expr

    def condition(self, children):
        return self._lr_binop(children)

    def disjunction(self, children):
        return self._lr_binop(children)

    def conjunction(self, children):
        return self._lr_binop(children)

    def negation(self, children):
        op, phi = children
        return HplUnaryOperator(op, phi)

    def quantification(self, children):
        qt, var, dom, phi = children
        return HplQuantifier(qt, var, dom, phi)

    def atomic_condition(self, children):
        return self._lr_binop(children)

    def function_call(self, children):
        fun, arg = children
        return HplFunctionCall(fun, (arg,))

    def expr(self, children):
        return self._lr_binop(children)

    def term(self, children):
        return self._lr_binop(children)

    def factor(self, children):
        return self._lr_binop(children)

    def _lr_binop(self, children):
        assert len(children) == 1 or len(children) == 3
        if len(children) == 3:
            op = children[1]
            lhs = children[0]
            rhs = children[2]
            return HplBinaryOperator(op, lhs, rhs)
        return children[0] # len(children) == 1

    def negative_number(self, children: Tuple[str, HplExpression]) -> HplUnaryOperator:
        op, n = children
        return HplUnaryOperator(op, n)

    def number_constant(self, children: Tuple[str]) -> HplLiteral:
        c = children[0]
        return HplLiteral(c, NumberConstants[c])

    def enum_literal(self, values: Tuple[HplExpression]) -> HplSet:
        return HplSet(values)

    def range_literal(self, children: Tuple[str, HplExpression, HplExpression, str]) -> HplRange:
        lr, lb, ub, rr = children
        exc_min = lr.startswith("!")
        exc_max = rr.endswith("!")
        return HplRange(lb, ub, exc_min=exc_min, exc_max=exc_max)

    def variable(self, children: Tuple[str]) -> HplVarReference:
        token = children[0]
        return HplVarReference(token)

    def own_field(self, children: Tuple[str]) -> HplFieldAccess:
        token = children[0]
        return HplFieldAccess(HplThisMessage(), token)

    def field_access(self, children: Tuple[HplExpression, str]) -> HplFieldAccess:
        ref, token = children
        return HplFieldAccess(ref, token)

    def array_access(self, children: Tuple[HplExpression, HplExpression]) -> HplArrayAccess:
        ref, index = children
        return HplArrayAccess(ref, index)

    def frequency(self, children: Tuple[str, str]) -> float:
        n, unit = children
        n = float(n)
        assert unit == 'hz'
        n = 1.0 / n  # seconds
        return n

    def time_amount(self, children: Tuple[str, str]) -> float:
        n, unit = children
        n = float(n)
        if unit == 'ms':
            n = n / 1000.0
        else:
            assert unit == 's'
        return n

    def boolean(self, children: Tuple[str]) -> HplLiteral:
        b = children[0]
        if b == 'True':
            return HplLiteral(b, True)
        assert b == 'False'
        return HplLiteral(b, False)

    def string(self, children: Tuple[str]) -> HplLiteral:
        s = children[0]
        return HplLiteral(s, s)

    def number(self, children: Tuple[str]) -> HplLiteral:
        n = children[0]
        try:
            return HplLiteral(n, int(n))
        except ValueError as e:
            return HplLiteral(n, float(n))

    def signed_number(self, children: Tuple[str]) -> HplLiteral:
        n = children[0]
        try:
            return HplLiteral(n, int(n))
        except ValueError as e:
            return HplLiteral(n, float(n))

    def int_literal(self, children: Tuple[str]) -> HplLiteral:
        n = children[0]
        return HplLiteral(n, int(n))

    def channel_name(self, children: Tuple[str]) -> str:
        n = children[0]
        return n


###############################################################################
# HPL Parser
###############################################################################


@frozen
class HplParser:
    _lark: Lark

    @classmethod
    def from_grammar(
        cls,
        grammar: str,
        start: str = 'hpl_file',
        *,
        debug: bool = False,
    ) -> 'HplParser':
        return cls(Lark(
            grammar,
            parser='lalr',
            start=start,
            transformer=PropertyTransformer(),
            debug=debug,
        ))

    def parse(self, text: str) -> HplAstObject:
        try:
            return self._lark.parse(text)
        except (UnexpectedToken, UnexpectedCharacters, SyntaxError) as e:
            raise HplSyntaxError.from_lark(e)

    @classmethod
    def specification_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(HPL_GRAMMAR, start='hpl_file', debug=debug)

    @classmethod
    def property_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(HPL_GRAMMAR, start='hpl_property', debug=debug)

    @classmethod
    def predicate_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(PREDICATE_GRAMMAR, start='top_level_condition', debug=debug)


def specification_parser(debug: bool = False) -> HplParser:
    return HplParser.specification_parser(debug=debug)


def property_parser(debug: bool = False) -> HplParser:
    return HplParser.property_parser(debug=debug)


def predicate_parser(debug: bool = False) -> HplParser:
    return HplParser.predicate_parser(debug=debug)


def parse_specification(hpl_text: str) -> HplSpecification:
    return specification_parser().parse(hpl_text)


def parse_property(hpl_text: str) -> HplProperty:
    return property_parser().parse(hpl_text)


def parse_predicate(hpl_text: str) -> HplPredicate:
    return predicate_parser().parse(hpl_text)
