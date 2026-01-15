"""
HPL 2.0 AST Node Definitions (Improved)
Uses frozen attrs for immutability, enums for type safety
"""

from typing import Optional, List, Union
from enum import Enum, auto
from attrs import frozen, field
from typeguard import typechecked


# ==============================================
# Enumerations
# ==============================================

class TimeUnit(Enum):
    """Time units"""
    NANOSECONDS = "ns"
    MICROSECONDS = "us"
    MILLISECONDS = "ms"
    SECONDS = "s"
    MINUTES = "m"
    HOURS = "h"
    DAYS = "d"


class BinaryOperator(Enum):
    """Binary operators"""
    # Arithmetic
    ADD = "+"
    SUBTRACT = "-"
    MULTIPLY = "*"
    DIVIDE = "/"
    MODULO = "%"
    
    # Comparison
    EQUAL = "="
    NOT_EQUAL = "!="
    LESS_THAN = "<"
    LESS_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_EQUAL = ">="
    
    # Logical
    AND = "and"
    OR = "or"
    IMPLIES = "implies"


class UnaryOperator(Enum):
    """Unary operators"""
    NEGATE = "-"
    NOT = "not"


class Quantifier(Enum):
    """Quantifiers"""
    FORALL = "forall"
    EXISTS = "exists"


class ScalarTypeName(Enum):
    """Scalar type names"""
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    STRING = "string"
    TIME = "time"
    DURATION = "duration"


# ==============================================
# Base Node
# ==============================================

@frozen
class ASTNode:
    """Base class for all AST nodes"""
    line: Optional[int] = field(default=None, kw_only=True)
    column: Optional[int] = field(default=None, kw_only=True)


# ==============================================
# Top-Level Constructs
# ==============================================

@frozen
class Specification(ASTNode):
    """Root node of an HPL specification"""
    imports: tuple['Import', ...] = field(factory=tuple, converter=tuple)
    declarations: tuple[Union['EventDecl', 'ComputedDecl', 'ConditionDecl'], ...] = field(factory=tuple, converter=tuple)
    groups: tuple['Group', ...] = field(factory=tuple, converter=tuple)
    statemachines: tuple['StateMachine', ...] = field(factory=tuple, converter=tuple)
    properties: tuple['Property', ...] = field(factory=tuple, converter=tuple)


@frozen
class Import(ASTNode):
    """Import statement: import <module> from "<library>" """
    module: str
    library: str


# ==============================================
# Type System
# ==============================================

@frozen
class Type(ASTNode):
    """Base type class"""
    pass


@frozen
class ScalarType(Type):
    """Scalar types: int, float, bool, string, time, duration"""
    name: ScalarTypeName


@frozen
class ArrayType(Type):
    """Array types: int[], float[], etc."""
    element_type: ScalarType


@frozen
class QualifiedType(Type):
    """Qualified types: ros.Pose, geometry.Point, etc."""
    components: tuple[str, ...] = field(converter=tuple)


# ==============================================
# Declarations
# ==============================================

@frozen
class EventDecl(ASTNode):
    """Event declaration: event <source> [{ predicate }] as <alias> [: type]"""
    source: 'EventRef'
    alias: str
    predicate: Optional['Expression'] = None
    type_annotation: Optional[QualifiedType] = None


@frozen
class ComputedDecl(ASTNode):
    """Computed value: <type> <name> = <expr> [reset on <event>]"""
    type: Type
    name: str
    expression: 'Expression'
    reset_event: Optional['EventRef'] = None


@frozen
class ConditionDecl(ASTNode):
    """Condition: condition <name>: <pattern>"""
    name: str
    pattern: 'Pattern'


# ==============================================
# Groups
# ==============================================

@frozen
class Group(ASTNode):
    """Group of related properties with shared declarations"""
    name: str
    declarations: tuple[Union[EventDecl, ComputedDecl, ConditionDecl], ...] = field(factory=tuple, converter=tuple)
    properties: tuple['Property', ...] = field(factory=tuple, converter=tuple)


# ==============================================
# Properties
# ==============================================

@frozen
class Property(ASTNode):
    """Property: property <name> [{ declarations }]: <scope>: <pattern>"""
    name: str
    scope: 'Scope'
    body: Union['Pattern', 'Expression']
    declarations: tuple[Union[EventDecl, ComputedDecl, ConditionDecl], ...] = field(factory=tuple, converter=tuple)
    metadata: tuple[tuple[str, str], ...] = field(factory=tuple, converter=tuple)  # Immutable metadata


# ==============================================
# Scopes
# ==============================================

@frozen
class Scope(ASTNode):
    """Base scope class"""
    pass


@frozen
class AlwaysScope(Scope):
    """always: <body>"""
    pass


@frozen
class AfterScope(Scope):
    """after <event>: <body>"""
    event: 'EventSpec'


@frozen
class UntilScope(Scope):
    """until <event>: <body>"""
    event: 'EventSpec'


@frozen
class AfterUntilScope(Scope):
    """after <event1> until <event2>: <body>"""
    start_event: 'EventSpec'
    end_event: 'EventSpec'


@frozen
class WhenScope(Scope):
    """when <statemachine>.in(<states>): <body>"""
    statemachine: str
    states: tuple[str, ...] = field(converter=tuple)


@frozen
class NestedScope(Scope):
    """Nested scope: <outer>: <inner>: <body>"""
    outer: Scope
    inner: Scope


# ==============================================
# Patterns
# ==============================================

@frozen
class Pattern(ASTNode):
    """Base pattern class"""
    pass


@frozen
class ExistencePattern(Pattern):
    """some <event> [within <time>]"""
    event: 'EventSpec'
    within: Optional['TimeExpression'] = None


@frozen
class AbsencePattern(Pattern):
    """no <event> [within <time>]"""
    event: 'EventSpec'
    within: Optional['TimeExpression'] = None


@frozen
class ResponsePattern(Pattern):
    """[each] <trigger> causes <response> [within <time>] [unless <exception>]"""
    trigger: 'EventSpec'
    response: 'EventSpec'
    each: bool = False
    within: Optional['TimeExpression'] = None
    unless_clause: Optional['UnlessClause'] = None


@frozen
class PreventionPattern(Pattern):
    """<trigger> forbids <forbidden> [within <time>] [unless <exception>]"""
    trigger: 'EventSpec'
    forbidden: 'EventSpec'
    within: Optional['TimeExpression'] = None
    unless_clause: Optional['UnlessClause'] = None


@frozen
class RequirementPattern(Pattern):
    """<consequent> requires <antecedent> [within <time>] [unless <exception>]"""
    consequent: 'EventSpec'
    antecedent: 'EventSpec'
    within: Optional['TimeExpression'] = None
    unless_clause: Optional['UnlessClause'] = None


@frozen
class UnlessClause(ASTNode):
    """unless <event> [within <time>]"""
    event: 'EventSpec'
    within: Optional['TimeExpression'] = None


# ==============================================
# Event Specifications
# ==============================================

@frozen
class EventSpec(ASTNode):
    """Event specification: <event_ref> [as <alias>] [{ predicate }]"""
    event: 'EventRef'
    alias: Optional[str] = None
    predicate: Optional['Expression'] = None


@frozen
class EventRef(ASTNode):
    """
    Event reference - unified representation.
    
    - Declared event: name="error", is_topic=False (refers to @error)
    - Topic reference: name="/error", is_topic=True (inline /error)
    """
    name: str
    is_topic: bool


# ==============================================
# State Machines
# ==============================================

@frozen
class StateMachine(ASTNode):
    """State machine definition"""
    name: str
    initial_state: str
    states: tuple['State', ...] = field(factory=tuple, converter=tuple)


@frozen
class State(ASTNode):
    """State definition with transitions"""
    name: str
    transitions: tuple['Transition', ...] = field(factory=tuple, converter=tuple)


@frozen
class Transition(ASTNode):
    """Base transition class"""
    target: str


@frozen
class EventTransition(Transition):
    """on <event> [{ predicate }] [[ guard ]] -> <target>"""
    event: EventRef
    predicate: Optional['Expression'] = None
    guard: Optional['Expression'] = None


@frozen
class TimeoutTransition(Transition):
    """timeout <time> -> <target>"""
    timeout: 'TimeExpression'


# ==============================================
# Expressions
# ==============================================

@frozen
class Expression(ASTNode):
    """Base expression class"""
    pass


@frozen
class Literal(Expression):
    """Literal value: number, string, boolean"""
    value: Union[int, float, str, bool]


@frozen
class Identifier(Expression):
    """Simple identifier reference"""
    name: str


@frozen
class AtIdentifier(Expression):
    """@ prefixed identifier: @event_name"""
    name: str


@frozen
class FieldAccess(Expression):
    """Field access: expr.field or @event.field"""
    object: Expression
    field: str


@frozen
class ArrayAccess(Expression):
    """Array indexing: expr[index]"""
    array: Expression
    index: Expression


@frozen
class Call(Expression):
    """Function call: func(args)"""
    function: Expression
    arguments: tuple[Expression, ...] = field(factory=tuple, converter=tuple)


@frozen
class UnaryOp(Expression):
    """Unary operation: -expr, not expr"""
    operator: UnaryOperator
    operand: Expression


@frozen
class BinaryOp(Expression):
    """Binary operation: left op right"""
    operator: BinaryOperator
    left: Expression
    right: Expression


@frozen
class QuantifierExpr(Expression):
    """Quantified expression: forall/exists x in collection: predicate"""
    quantifier: Quantifier
    variable: str
    collection: Expression
    predicate: Expression


@frozen
class LambdaExpr(Expression):
    """Lambda expression: x => expression"""
    parameter: str
    body: Expression


# ==============================================
# Aggregation Expressions
# ==============================================

@frozen
class AggregationCall(Expression):
    """Base aggregation function call"""
    pass


@frozen
class CountCall(AggregationCall):
    """count(event)"""
    event: EventRef


@frozen
class SumCall(AggregationCall):
    """sum(expression)"""
    expression: Expression


@frozen
class MaxCall(AggregationCall):
    """max(expression)"""
    expression: Expression


@frozen
class MinCall(AggregationCall):
    """min(expression)"""
    expression: Expression


@frozen
class AvgCall(AggregationCall):
    """avg(expression)"""
    expression: Expression


@frozen
class AgeCall(AggregationCall):
    """age(event)"""
    event: EventRef


@frozen
class TimestampCall(AggregationCall):
    """timestamp(event)"""
    event: EventRef


@frozen
class BufferCall(AggregationCall):
    """buffer(expression, size: n)"""
    expression: Expression
    size: Expression


@frozen
class LastCall(AggregationCall):
    """last(expression)"""
    expression: Expression


# ==============================================
# Time Expressions
# ==============================================

@frozen
class TimeExpression(ASTNode):
    """Time expression: <number> <unit>"""
    value: Union[int, float]
    unit: TimeUnit
