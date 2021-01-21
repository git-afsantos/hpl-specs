# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from __future__ import unicode_literals
from builtins import object
import math

from lark import Lark, Transformer
from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from .ast import (
    HplSpecification, HplProperty, HplScope, HplPattern, HplEvent,
    HplExpression, HplPredicate, HplVacuousTruth, HplQuantifier,
    HplUnaryOperator, HplBinaryOperator, HplSet, HplRange, HplLiteral,
    HplVarReference, HplFunctionCall, HplFieldAccess, HplArrayAccess,
    HplThisMessage
)
from .grammar import PREDICATE_GRAMMAR, HPL_GRAMMAR
from .exceptions import HplSyntaxError


###############################################################################
# Constants
###############################################################################

INF = float("inf")
NAN = float("nan")


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

    def event(self, children):
        assert len(children) == 1 or len(children) == 2
        ros_name, alias = children[0]
        phi = HplVacuousTruth() if len(children) == 1 else children[1]
        return HplEvent.publish(ros_name, alias=alias, predicate=phi)

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

    def negative_number(self, children):
        op, n = children
        return HplUnaryOperator(op, n)

    _CONSTANTS = {
        "PI": math.pi,
        "INF": INF,
        "NAN": NAN
    }

    def number_constant(self, children):
        c = children[0]
        return HplLiteral(c, self._CONSTANTS[c])

    def enum_literal(self, values):
        return HplSet(values)

    def range_literal(self, children):
        lr, lb, ub, rr = children
        exc_min = lr.startswith("!")
        exc_max = rr.endswith("!")
        return HplRange(lb, ub, exc_min=exc_min, exc_max=exc_max)

    def variable(self, children):
        token = children[0]
        return HplVarReference(token)

    def own_field(self, children):
        token = children[0]
        return HplFieldAccess(HplThisMessage(), token)

    def field_access(self, children):
        ref, token = children
        return HplFieldAccess(ref, token)

    def array_access(self, children):
        ref, index = children
        return HplArrayAccess(ref, index)

    def frequency(self, children):
        n, unit = children
        n = float(n)
        assert unit == "hz"
        n = 1.0 / n # seconds
        return n

    def time_amount(self, children):
        n, unit = children
        n = float(n)
        if unit == "ms":
            n = n / 1000.0
        else:
            assert unit == "s"
        return n

    def boolean(self, children):
        b = children[0]
        if b == "True":
            return HplLiteral(b, True)
        assert b == "False"
        return HplLiteral(b, False)

    def string(self, children):
        s = children[0]
        return HplLiteral(s, s)

    def number(self, children):
        n = children[0]
        try:
            return HplLiteral(n, int(n))
        except ValueError as e:
            return HplLiteral(n, float(n))

    def signed_number(self, children):
        n = children[0]
        try:
            return HplLiteral(n, int(n))
        except ValueError as e:
            return HplLiteral(n, float(n))

    def int_literal(self, children):
        n = children[0]
        return HplLiteral(n, int(n))

    def ros_name(self, children):
        n = children[0]
        return n


###############################################################################
# HPL Parser
###############################################################################

class HplParser(object):
    __slots__ = ("_lark",)

    def __init__(self, grammar, start="hpl_file", debug=False):
        self._lark = Lark(grammar, parser="lalr", start=start,
                          transformer=PropertyTransformer(), debug=debug)

    def parse(self, text):
        try:
            return self._lark.parse(text)
        except (UnexpectedToken, UnexpectedCharacters, SyntaxError) as e:
            raise HplSyntaxError.from_lark(e)

    @classmethod
    def specification_parser(cls, debug=False):
        return cls(HPL_GRAMMAR, start="hpl_file", debug=debug)

    @classmethod
    def property_parser(cls, debug=False):
        return cls(HPL_GRAMMAR, start="hpl_property", debug=debug)

    @classmethod
    def predicate_parser(cls, debug=False):
        return cls(PREDICATE_GRAMMAR, start="top_level_condition", debug=debug)


def specification_parser(debug=False):
    return HplParser.specification_parser(debug=debug)

def property_parser(debug=False):
    return HplParser.property_parser(debug=debug)

def predicate_parser(debug=False):
    return HplParser.predicate_parser(debug=debug)


def parse_specification(hpl_text):
    return specification_parser().parse(hpl_text)

def parse_property(hpl_text):
    return property_parser().parse(hpl_text)

def parse_predicate(hpl_text):
    return predicate_parser().parse(hpl_text)
