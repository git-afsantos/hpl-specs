# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from enum import Enum
import math
from typing import Any, Dict, Iterable, Optional, Tuple, Union

from attrs import frozen
from hpl.ast.predicates import predicate_from_expression
from lark import Lark, Transformer
from lark.exceptions import UnexpectedCharacters, UnexpectedToken
from lark.visitors import v_args

from hpl.ast import (
    HplSpecification, HplProperty, HplScope, HplPattern, HplSimpleEvent,
    HplPredicate, HplVacuousTruth, HplQuantifier,
    HplUnaryOperator, HplBinaryOperator, HplSet, HplRange, HplLiteral,
    HplVarReference, HplFunctionCall, HplFieldAccess, HplArrayAccess,
    HplThisMessage, HplEventDisjunction
)
from hpl.ast.base import HplAstObject
from hpl.ast.events import HplEvent
from hpl.ast.expressions import HplExpression
from hpl.grammar import PREDICATE_GRAMMAR, HPL_GRAMMAR
from hpl.errors import HplSyntaxError

###############################################################################
# Constants
###############################################################################

INF = float('inf')
NAN = float('nan')


class NumberConstants(Enum):
    PI = math.pi
    INF = INF
    NAN = NAN
    E = math.e


###############################################################################
# Transformer
###############################################################################


@v_args(inline=True)
class PropertyTransformer(Transformer):
    @v_args(inline=False)
    def hpl_file(self, children: Iterable[HplProperty]) -> HplSpecification:
        return HplSpecification(children)

    def hpl_property(
        self,
        metadata: Optional[Dict[str, Any]],
        scope: HplScope,
        pattern: HplPattern,
    ) -> HplProperty:
        if metadata is None:
            metadata = {}
        # hpl_property.sanity_check()
        hpl_property = HplProperty(scope, pattern)
        hpl_property.metadata.update(metadata)
        return hpl_property

    @v_args(inline=False)
    def metadata(self, children: Iterable[Tuple[str, Any]]) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {}
        pid = None
        dup = None
        for key, value in children:
            if key == 'id':
                pid = value
            if key in metadata:
                dup = key
            metadata[key] = value
        if dup is not None:
            raise HplSyntaxError.duplicate_metadata(dup, pid=pid)
        return metadata

    def metadata_id(self, data: str) -> Tuple[str, str]:
        return ('id', data)

    def metadata_title(self, data: str) -> Tuple[str, str]:
        return ('title', data)

    def metadata_desc(self, data: str) -> Tuple[str, str]:
        return ('description', data)

    @v_args(inline=False)
    def global_scope(self, children: Iterable[Any]) -> HplScope:
        assert not children
        return HplScope.globally()

    def after_until(self, p: HplEvent, q: Optional[HplEvent]) -> HplScope:
        return HplScope.after(p) if q is None else HplScope.after_until(p, q)

    def until(self, event: HplEvent) -> HplScope:
        return HplScope.until(event)

    def existence(self, b: HplEvent, t: Optional[float]) -> HplPattern:
        max_time = INF if t is None else t
        return HplPattern.existence(b, max_time=max_time)

    def absence(self, b: HplEvent, t: Optional[float]) -> HplPattern:
        max_time = INF if t is None else t
        return HplPattern.absence(b, max_time=max_time)

    def response(self, a: HplEvent, b: HplEvent, t: Optional[float]) -> HplPattern:
        max_time = INF if t is None else t
        return HplPattern.response(a, b, max_time=max_time)

    def prevention(self, a: HplEvent, b: HplEvent, t: Optional[float]) -> HplPattern:
        max_time = INF if t is None else t
        return HplPattern.prevention(a, b, max_time=max_time)

    def requirement(self, b: HplEvent, a: HplEvent, t: Optional[float]) -> HplPattern:
        max_time = INF if t is None else t
        return HplPattern.requirement(b, a, max_time=max_time)

    @v_args(inline=False)
    def event_disjunction(self, children: Iterable[HplEvent]) -> HplEventDisjunction:
        assert len(children) >= 2
        if len(children) == 2:
            return HplEventDisjunction(children[0], children[1])
        else:
            return HplEventDisjunction(
                children[0], self.event_disjunction(children[1:]))

    def event(self, msg: Tuple[str, Optional[str]], phi: Optional[HplPredicate]) -> HplSimpleEvent:
        name, alias = msg
        phi = HplVacuousTruth() if phi is None else phi
        return HplSimpleEvent.publish(name, alias=alias, predicate=phi)

    def message(self, name: str, alias: Optional[str]) -> Tuple[str, Optional[str]]:
        return (name, alias)

    def predicate(self, expr: HplExpression) -> HplPredicate:
        return predicate_from_expression(expr)

    def top_level_condition(self, expr: HplExpression) -> HplExpression:
        return expr

    @v_args(inline=False)
    def condition(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    @v_args(inline=False)
    def disjunction(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    @v_args(inline=False)
    def conjunction(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    def negation(self, op: str, phi: HplExpression) -> HplUnaryOperator:
        return HplUnaryOperator(op, phi)

    def quantification(
        self,
        quantifier: str,
        variable: str,
        domain: HplExpression,
        condition: HplExpression,
    ) -> HplQuantifier:
        return HplQuantifier(quantifier, variable, domain, condition)

    @v_args(inline=False)
    def atomic_condition(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    def function_call(self, fun: str, arg: HplExpression) -> HplExpression:
        return HplFunctionCall(fun, (arg,))

    @v_args(inline=False)
    def expr(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    @v_args(inline=False)
    def term(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    @v_args(inline=False)
    def factor(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        return self._lr_binop(children)

    def _lr_binop(self, children: Iterable[Union[str, HplExpression]]) -> HplExpression:
        assert len(children) == 1 or len(children) == 3
        if len(children) == 3:
            op = children[1]
            lhs = children[0]
            rhs = children[2]
            return HplBinaryOperator(op, lhs, rhs)
        return children[0]  # len(children) == 1

    def negative_number(self, op: str, n: HplExpression) -> HplUnaryOperator:
        return HplUnaryOperator(op, n)

    def number_constant(self, token: str) -> HplLiteral:
        return HplLiteral(token, NumberConstants[token])

    @v_args(inline=False)
    def enum_literal(self, values: Iterable[HplExpression]) -> HplSet:
        return HplSet(values)

    def range_literal(self, lr: str, lb: HplExpression, ub: HplExpression, rr: str) -> HplRange:
        exc_min = lr.startswith('!')
        exc_max = rr.endswith('!')
        return HplRange(lb, ub, exc_min=exc_min, exc_max=exc_max)

    def variable(self, token: str) -> HplVarReference:
        return HplVarReference(token)

    def own_field(self, token: str) -> HplFieldAccess:
        return HplFieldAccess(HplThisMessage(), token)

    def field_access(self, ref: HplExpression, token: str) -> HplFieldAccess:
        return HplFieldAccess(ref, token)

    def array_access(self, ref: HplExpression, index: HplExpression) -> HplArrayAccess:
        return HplArrayAccess(ref, index)

    def frequency(self, num: str, unit: str) -> float:
        n = float(num)
        assert unit == 'hz'
        n = 1.0 / n  # seconds
        return n

    def time_amount(self, num: str, unit: str) -> float:
        n = float(num)
        if unit == 'ms':
            n = n / 1000.0
        else:
            assert unit == 's'
        return n

    def boolean(self, token: str) -> HplLiteral:
        if token == 'True':
            return HplLiteral(token, True)
        assert token == 'False'
        return HplLiteral(token, False)

    def string(self, token: str) -> HplLiteral:
        return HplLiteral(token, token)

    def number(self, token: str) -> HplLiteral:
        try:
            return HplLiteral(token, int(token))
        except ValueError as e:
            return HplLiteral(token, float(token))

    def signed_number(self, token: str) -> HplLiteral:
        try:
            return HplLiteral(token, int(token))
        except ValueError as e:
            return HplLiteral(token, float(token))

    def int_literal(self, token: str) -> HplLiteral:
        return HplLiteral(token, int(token))

    def channel_name(self, name: str) -> str:
        return name


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
            maybe_placeholders=True,
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
