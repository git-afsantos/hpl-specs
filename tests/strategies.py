# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, Final, Iterable, Optional

from hypothesis import assume
from hypothesis.strategies import (
    SearchStrategy,
    booleans,
    builds,
    deferred,
    fixed_dictionaries,
    floats,
    integers,
    just,
    none,
    one_of,
    sampled_from,
    sets,
    text,
)

###############################################################################
# Constants
###############################################################################

SPEC_RULE: Final[str] = 'hpl_file'
PROP_RULE: Final[str] = 'hpl_property'
PRED_RULE: Final[str] = 'hpl_predicate'
EXPR_RULE: Final[str] = 'hpl_expression'

ALPHABET: Final[str] = 'abcdefghijklmnopqrstuvwxyz'

###############################################################################
# Helper Strategies
###############################################################################


def number_constants() -> SearchStrategy[str]:
    return sampled_from(['PI', 'E', 'INF', 'NAN'])


def number_literals() -> SearchStrategy[str]:
    ints = integers(min_value=-4, max_value=4)
    decs = floats(min_value=-4, max_value=4)
    return one_of(ints, decs).map(str)

def _apply_quotes(s: str) -> str:
    s = s.replace('"', '\\"')
    return f'"{s}"'


def string_literals() -> SearchStrategy[str]:
    return text(max_size=3).map(_apply_quotes)


def at_symbol(name: str) -> str:
    return '@' + name


def identifiers() -> SearchStrategy[str]:
    return text(ALPHABET, min_size=1, max_size=2)


def variable_references() -> SearchStrategy[str]:
    return identifiers().map(at_symbol)


def number_to_time(n: float) -> str:
    return f'{n}s' if n < 10.0 else f'{n}ms'


def time_units() -> SearchStrategy[str]:
    return floats(min_value=0.0, max_value=100.0, exclude_min=True).map(number_to_time)


def _array_access_builder(ref: str, idx: str) -> str:
    return f'{ref}[{idx}]'


def array_accesses() -> SearchStrategy[str]:
    array = deferred(references)
    expr = deferred(numeric_expressions)
    return builds(_array_access_builder, array, expr)


def _field_access_builder(ref: str, name: str) -> str:
    return f'{ref}.{name}'


def field_accesses() -> SearchStrategy[str]:
    obj = deferred(references)
    return builds(_field_access_builder, obj, identifiers())


def base_references() -> SearchStrategy[str]:
    return one_of(identifiers(), variable_references())


def references() -> SearchStrategy[str]:
    fields = deferred(field_accesses)
    arrays = deferred(array_accesses)
    return one_of(base_references(), fields, arrays)


def _function_call_builder(fun: str, expr: str) -> str:
    return f'{fun}({expr})'


def function_calls() -> SearchStrategy[str]:
    # FIXME do other types of functions
    expr = deferred(numeric_expressions)
    functions = sampled_from(['abs', 'sqrt'])
    return builds(_function_call_builder, functions, expr)


def _range_literal_builder(lb: str, ub: str, exc_min: bool, exc_max: bool) -> str:
    lr = '![' if exc_min else '['
    rr = ']!' if exc_max else ']'
    return f'{lr}{lb} to {ub}{rr}'


def range_literals() -> SearchStrategy[str]:
    lb = deferred(numeric_expressions)
    ub = deferred(numeric_expressions)
    exc_min = booleans()
    exc_max = booleans()
    return builds(_range_literal_builder, lb, ub, exc_min, exc_max)


def _set_to_str(elems: Iterable[str]) -> str:
    return f'{{{", ".join(elems)}}}'


def set_literals() -> SearchStrategy[str]:
    # FIXME any kind of expression?
    elems = deferred(numeric_expressions)
    return sets(elems, min_size=1, max_size=3).map(_set_to_str)


def atomic_values() -> SearchStrategy[str]:
    return one_of(
        booleans().map(str),
        number_literals(),
        number_constants(),
        string_literals(),
        references(),
        deferred(range_literals),
        deferred(set_literals),
        deferred(function_calls),
    )


def _prepend_minus(num: str) -> str:
    return f'(-{num})'


def negative_numbers() -> SearchStrategy[str]:
    return deferred(numeric_expressions).map(_prepend_minus)


def basic_numeric_expressions() -> SearchStrategy[str]:
    return one_of(
        number_literals(),
        number_constants(),
        references(),
        deferred(negative_numbers),
        parenthesized(deferred(numeric_expressions)),
    )


def _infix_operator_builder(op: str, arg1: str, arg2: str) -> str:
    return f'({arg1} {op} {arg2})'


def numeric_binary_operators() -> SearchStrategy[str]:
    op = sampled_from(['+', '-', '*', '/', '**'])
    arg1 = deferred(numeric_expressions)
    arg2 = deferred(numeric_expressions)
    return builds(_infix_operator_builder, op, arg1, arg2)


def numeric_expressions() -> SearchStrategy[str]:
    return one_of(
        number_literals(),
        number_constants(),
        references(),
        deferred(negative_numbers),
        deferred(numeric_binary_operators),
        parenthesized(deferred(numeric_expressions)),
    )


def set_expressions() -> SearchStrategy[str]:
    return one_of(references(), deferred(set_literals))


def inclusion_conditions() -> SearchStrategy[str]:
    # FIXME do any kind of expression minus sets and ranges
    arg1 = one_of(
        booleans(),
        number_literals(),
        number_constants(),
        string_literals(),
        references(),
        deferred(function_calls),
    )
    arg2 = deferred(set_expressions)
    return builds(_infix_operator_builder, just('in'), arg1, arg2)


def numeric_relational_conditions() -> SearchStrategy[str]:
    op = sampled_from(['=', '!=', '<', '>', '<=', '>='])
    arg1 = numeric_expressions()
    arg2 = numeric_expressions()
    return builds(_infix_operator_builder, op, arg1, arg2)


def atomic_conditions() -> SearchStrategy[str]:
    return one_of(numeric_relational_conditions(), inclusion_conditions())


def _quantifier_builder(q: str, v: str, d: str, p: str) -> str:
    return f'{q} {v} in {d}: {p}'


def quantifiers() -> SearchStrategy[str]:
    q = sampled_from(['forall', 'exists'])
    v = identifiers()
    d = deferred(set_expressions)
    p = deferred(logic_expressions)
    return builds(_quantifier_builder, q, v, d, p)


def _prepend_not(expr: str) -> str:
    return f'(not {expr})'


def negations() -> SearchStrategy[str]:
    return deferred(logic_expressions).map(_prepend_not)


def logic_binary_operators() -> SearchStrategy[str]:
    op = sampled_from(['and', 'or', 'implies', 'iff'])
    arg1 = deferred(logic_expressions)
    arg2 = deferred(logic_expressions)
    return builds(_infix_operator_builder, op, arg1, arg2)


def logic_expressions() -> SearchStrategy[str]:
    return one_of(
        booleans().map(str),
        references(),
        atomic_conditions(),
        deferred(negations),
        deferred(logic_binary_operators),
        parenthesized(deferred(logic_expressions)),
    )


def apply_parentheses(expr: str, parentheses: str = '()') -> str:
    return f'{parentheses[0]}{expr}{parentheses[1]}'


def parenthesized(strategy: SearchStrategy[str]) -> SearchStrategy[str]:
    return strategy.map(apply_parentheses)


def _simple_event_builder(name: str, alias: Optional[str], pred: Optional[str]) -> str:
    alias = f' as {alias}' if alias else ''
    pred = f' {pred}' if pred else ''
    return f'{name}{alias}{pred}'


def simple_events() -> SearchStrategy[str]:
    name = identifiers()
    alias = none() | identifiers().map(str.upper)
    pred = none() | predicates()
    return builds(_simple_event_builder, name, alias, pred)


def _disjoiner(elems: Iterable[str]) -> str:
    return ' or '.join(elems)


def event_disjunctions() -> SearchStrategy[str]:
    elems = sets(simple_events(), min_size=2, max_size=3)
    return parenthesized(builds(_disjoiner, elems))


def events() -> SearchStrategy[str]:
    return one_of(simple_events(), event_disjunctions())


def _unary_pattern_builder(kw: str, event: str, bound: Optional[str]) -> str:
    bound = f' within {bound}' if bound else ''
    return f'{kw} {event}{bound}'


def unary_patterns() -> SearchStrategy[str]:
    pattern = sampled_from(['no', 'some'])
    bound = none() | time_units()
    return builds(_unary_pattern_builder, pattern, events(), bound)


def _binary_pattern_builder(kw: str, ev1: str, ev2: str, bound: Optional[str]) -> str:
    bound = f' within {bound}' if bound else ''
    return f'{ev1} {kw} {ev2}{bound}'


def binary_patterns() -> SearchStrategy[str]:
    pattern = sampled_from(['causes', 'requires', 'forbids'])
    bound = none() | time_units()
    return builds(_binary_pattern_builder, pattern, events(), events(), bound)


def patterns() -> SearchStrategy[str]:
    return one_of(unary_patterns(), binary_patterns())


def _prepend_after(event: str) -> str:
    return f'after {event}'


def _prepend_until(event: str) -> str:
    return f'until {event}'


def _space_joiner(*args: Iterable[str]) -> str:
    return ' '.join(args)


def scopes() -> SearchStrategy[str]:
    after = events().map(_prepend_after)
    until = events().map(_prepend_until)
    after_until = builds(_space_joiner, after, until)
    return one_of(just('globally'), after, until, after_until)


def metadata() -> SearchStrategy[Dict[str, str]]:
    mandatory = {}
    optional = {
        'id': identifiers(),
        'title': string_literals(),
        'description': string_literals(),
    }
    return fixed_dictionaries(mandatory, optional=optional)


def _property_builder(meta: Optional[Dict[str, str]], scope: str, pattern: str) -> str:
    meta = meta or {}
    annotations = ''.join(f'# {k}: {v}\n' for k, v in meta.items())
    return f'{annotations}{scope}: {pattern}'


###############################################################################
# Grammar Strategies
###############################################################################


def expressions() -> SearchStrategy[str]:
    return one_of(numeric_expressions(), logic_expressions())


def predicates() -> SearchStrategy[str]:
    return builds(apply_parentheses, logic_expressions(), parentheses=just('{}'))


def properties() -> SearchStrategy[str]:
    meta = none() | metadata()
    return builds(_property_builder, meta, scopes(), patterns())


def specifications() -> SearchStrategy[str]:
    return sets(properties(), min_size=1).map('\n\n'.join)
