# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Any, Callable, Dict, Iterable, Optional, Tuple, Union

from enum import Enum
import math

from attrs import frozen
from lark import Lark, Transformer
from lark.exceptions import UnexpectedCharacters, UnexpectedToken
from lark.visitors import v_args

from hpl.ast import (
    HplArrayAccess,
    HplBinaryOperator,
    HplEventDisjunction,
    HplFieldAccess,
    HplFunctionCall,
    HplLiteral,
    HplPattern,
    HplPredicate,
    HplProperty,
    HplQuantifier,
    HplRange,
    HplScope,
    HplSet,
    HplSimpleEvent,
    HplSpecification,
    HplThisMessage,
    HplUnaryOperator,
    HplVacuousTruth,
    HplVarReference,
)
from hpl.ast.base import HplAstObject
from hpl.ast.events import HplEvent
from hpl.ast.expressions import HplExpression, _convert_binary_operator, _convert_unary_operator
from hpl.ast.predicates import predicate_from_expression
from hpl.errors import HplSyntaxError
from hpl.grammar import HPL_GRAMMAR, PREDICATE_GRAMMAR
from hpl.types import ARRAY_TYPE, MESSAGE_TYPE, NUMBER_TYPE

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
        return HplSpecification(tuple(children))

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

    def after_until(self, p: HplEvent, q: Optional[HplEvent] = None) -> HplScope:
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
            return HplEventDisjunction(children[0], self.event_disjunction(children[1:]))

    def event(self, name: str, alias: Optional[str], phi: Optional[HplPredicate]) -> HplSimpleEvent:
        phi = HplVacuousTruth() if phi is None else phi
        return HplSimpleEvent.publish(name, alias=alias, predicate=phi)

    def alias(self, name: str) -> str:
        return name

    def hpl_predicate(self, expr: HplExpression) -> HplPredicate:
        return predicate_from_expression(expr)

    def hpl_expression(self, expr: HplExpression) -> HplExpression:
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

    def negation(self, token: str, phi: HplExpression) -> HplUnaryOperator:
        op = _convert_unary_operator(token)
        return HplUnaryOperator(op, phi.cast(op.parameter))

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
            op = _convert_binary_operator(children[1])
            lhs = children[0].cast(op.parameter1)
            rhs = children[2].cast(op.parameter2)
            return HplBinaryOperator(op, lhs, rhs)
        return children[0]  # len(children) == 1

    def negative_number(self, token: str, n: HplExpression) -> HplUnaryOperator:
        op = _convert_unary_operator(token)
        return HplUnaryOperator(op, n.cast(op.parameter))

    def number_constant(self, token: str) -> HplLiteral:
        return HplLiteral(token, NumberConstants[token].value)

    @v_args(inline=False)
    def enum_literal(self, values: Iterable[HplExpression]) -> HplSet:
        return HplSet(values)

    def range_literal(self, lr: str, lb: HplExpression, ub: HplExpression, rr: str) -> HplRange:
        exc_min = lr.startswith('!')
        exc_max = rr.endswith('!')
        return HplRange(lb, ub, exclude_min=exc_min, exclude_max=exc_max)

    def variable(self, token: str) -> HplVarReference:
        return HplVarReference(token)

    def own_field(self, token: str) -> HplFieldAccess:
        return HplFieldAccess(HplThisMessage(), token)

    def field_access(self, ref: HplExpression, token: str) -> HplFieldAccess:
        return HplFieldAccess(ref.cast(MESSAGE_TYPE), token)

    def array_access(self, ref: HplExpression, index: HplExpression) -> HplArrayAccess:
        return HplArrayAccess(ref.cast(ARRAY_TYPE), index.cast(NUMBER_TYPE))

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
        except ValueError:
            return HplLiteral(token, float(token))

    def signed_number(self, token: str) -> HplLiteral:
        try:
            return HplLiteral(token, int(token))
        except ValueError:
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
    transform: Optional[Callable[[HplAstObject], HplAstObject]] = None

    @classmethod
    def from_grammar(
        cls,
        grammar: str,
        start: str = 'hpl_file',
        *,
        transform: Optional[Callable[[HplAstObject], HplAstObject]] = None,
        debug: bool = False,
    ) -> 'HplParser':
        return cls(
            Lark(
                grammar,
                parser='lalr',
                start=start,
                transformer=PropertyTransformer(),
                maybe_placeholders=True,
                debug=debug,
            ),
            transform=transform,
        )

    def parse(self, text: str) -> HplAstObject:
        try:
            result: HplAstObject = self._lark.parse(text)
        except (UnexpectedToken, UnexpectedCharacters, SyntaxError) as e:
            raise HplSyntaxError.from_lark(e)
        return result if self.transform is None else self.transform(result)

    @classmethod
    def specification_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(HPL_GRAMMAR, start='hpl_file', debug=debug)

    @classmethod
    def property_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(HPL_GRAMMAR, start='hpl_property', debug=debug)

    @classmethod
    def predicate_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(PREDICATE_GRAMMAR, start='hpl_predicate', debug=debug)

    @classmethod
    def condition_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(
            PREDICATE_GRAMMAR,
            start='hpl_expression',
            debug=debug,
            transform=predicate_from_expression,
        )

    @classmethod
    def expression_parser(cls, *, debug: bool = False) -> 'HplParser':
        return cls.from_grammar(PREDICATE_GRAMMAR, start='hpl_expression', debug=debug)


def specification_parser(debug: bool = False) -> HplParser:
    return HplParser.specification_parser(debug=debug)


def property_parser(debug: bool = False) -> HplParser:
    return HplParser.property_parser(debug=debug)


def predicate_parser(debug: bool = False) -> HplParser:
    return HplParser.predicate_parser(debug=debug)


def condition_parser(debug: bool = False) -> HplParser:
    return HplParser.condition_parser(debug=debug)


def expression_parser(debug: bool = False) -> HplParser:
    return HplParser.expression_parser(debug=debug)


def parse_specification(hpl_text: str) -> HplSpecification:
    return specification_parser().parse(hpl_text)


def parse_property(hpl_text: str) -> HplProperty:
    return property_parser().parse(hpl_text)


def parse_predicate(hpl_text: str) -> HplPredicate:
    return predicate_parser().parse(hpl_text)


def parse_condition(hpl_text: str) -> HplPredicate:
    return condition_parser().parse(hpl_text)


def parse_expresion(hpl_text: str) -> HplExpression:
    return expression_parser().parse(hpl_text)
