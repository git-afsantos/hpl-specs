// HPL 2.0 Complete Grammar
// Using Lark parser syntax

// ==============================================
// Start Rule
// ==============================================

start: statement*

statement: import_stmt
         | event_decl
         | computed_decl
         | condition_decl
         | group
         | statemachine
         | property

// ==============================================
// Imports
// ==============================================

import_stmt: IMPORT IDENTIFIER FROM STRING_LITERAL

// ==============================================
// Types
// ==============================================

type: scalar_type | array_type | qualified_type

scalar_type: INT | FLOAT | BOOL | STRING | TIME | DURATION

array_type: scalar_type LBRACKET RBRACKET

qualified_type: IDENTIFIER (DOT IDENTIFIER)+

// ==============================================
// Event Declarations
// ==============================================

event_decl: EVENT event_source [predicate] AS IDENTIFIER [type_annotation]

event_source: TOPIC | IDENTIFIER

type_annotation: COLON qualified_type

// ==============================================
// Computed Value Declarations
// ==============================================

computed_decl: type IDENTIFIER EQ computed_expr [reset_clause]

computed_expr: aggregation_call
             | expression

aggregation_call: COUNT LPAREN event_ref RPAREN
                | SUM LPAREN expression RPAREN
                | MAX LPAREN expression RPAREN
                | MIN LPAREN expression RPAREN
                | AVG LPAREN expression RPAREN
                | AGE LPAREN event_ref RPAREN
                | TIMESTAMP LPAREN event_ref RPAREN
                | BUFFER LPAREN expression COMMA SIZE COLON expression RPAREN
                | LAST LPAREN expression RPAREN

reset_clause: RESET ON event_ref

event_ref: AT IDENTIFIER | TOPIC

// ==============================================
// Condition Declarations
// ==============================================

condition_decl: CONDITION IDENTIFIER COLON pattern

// ==============================================
// Groups
// ==============================================

group: GROUP IDENTIFIER LBRACE
       group_body*
       RBRACE

group_body: event_decl
          | computed_decl
          | condition_decl
          | property

// ==============================================
// Properties
// ==============================================

property: PROPERTY IDENTIFIER [property_block] COLON scope COLON scope_body

property_block: LBRACE property_item* RBRACE

property_item: metadata
             | event_decl
             | computed_decl
             | condition_decl

metadata: IDENTIFIER COLON STRING_LITERAL

// ==============================================
// Scopes
// ==============================================

scope: always_scope
     | after_scope
     | until_scope
     | after_until_scope
     | when_scope
     | scope COLON scope  // Nested scopes

always_scope: ALWAYS

after_scope: AFTER event_spec

until_scope: UNTIL event_spec

after_until_scope: AFTER event_spec UNTIL event_spec

when_scope: WHEN state_condition

state_condition: IDENTIFIER DOT IN LPAREN state_list RPAREN

state_list: STRING_LITERAL (COMMA STRING_LITERAL)*

scope_body: pattern | expression

// ==============================================
// Patterns
// ==============================================

pattern: existence_pattern
       | absence_pattern
       | response_pattern
       | prevention_pattern
       | requirement_pattern

existence_pattern: SOME event_spec [within_clause]

absence_pattern: NO event_spec [within_clause]

response_pattern: [EACH] event_spec CAUSES event_spec [within_clause] [unless_clause]

prevention_pattern: event_spec FORBIDS event_spec [within_clause] [unless_clause]

requirement_pattern: event_spec REQUIRES event_spec [within_clause] [unless_clause]

// Event specification with optional alias and predicate
event_spec: event_ref [AS IDENTIFIER] [predicate]

within_clause: WITHIN time_expr

unless_clause: UNLESS event_spec [within_clause]

// ==============================================
// State Machines
// ==============================================

statemachine: STATEMACHINE IDENTIFIER LBRACE
              initial_state
              state_def*
              RBRACE

initial_state: INITIAL IDENTIFIER

state_def: STATE IDENTIFIER LBRACE
           transition*
           RBRACE

transition: event_transition
          | timeout_transition

event_transition: ON event_ref [predicate] [guard] ARROW IDENTIFIER

guard: LBRACKET expression RBRACKET

timeout_transition: TIMEOUT time_expr ARROW IDENTIFIER

// ==============================================
// Expressions
// ==============================================

expression: or_expr

or_expr: and_expr (OR and_expr)*

and_expr: not_expr (AND not_expr)*

not_expr: NOT not_expr
        | implies_expr

implies_expr: comparison_expr [IMPLIES comparison_expr]

comparison_expr: additive_expr ((EQ | NE | LT | LE | GT | GE) additive_expr)*

additive_expr: multiplicative_expr ((PLUS | MINUS) multiplicative_expr)*

multiplicative_expr: unary_expr ((STAR | SLASH | PERCENT) unary_expr)*

unary_expr: MINUS unary_expr
          | postfix_expr

postfix_expr: primary_expr (field_access | array_access | call)*

field_access: DOT IDENTIFIER

array_access: LBRACKET expression RBRACKET

call: LPAREN [arguments] RPAREN

arguments: expression (COMMA expression)*

primary_expr: literal
            | reference
            | LPAREN expression RPAREN
            | quantifier
            | lambda_expr

literal: NUMBER
       | STRING_LITERAL
       | TRUE
       | FALSE

reference: AT IDENTIFIER (DOT IDENTIFIER)*   // @event or @event.field
         | TOPIC                             // /topic
         | IDENTIFIER                        // field, variable, function

quantifier: (FORALL | EXISTS) IDENTIFIER IN expression COLON expression

lambda_expr: IDENTIFIER ARROW_FUNC expression

// ==============================================
// Time Expressions
// ==============================================

time_expr: NUMBER TIME_UNIT

// ==============================================
// Predicates
// ==============================================

predicate: LBRACE expression RBRACE

// ==============================================
// Keywords
// ==============================================

ALWAYS: "always"
AFTER: "after"
UNTIL: "until"
WHEN: "when"
SOME: "some"
NO: "no"
EACH: "each"
CAUSES: "causes"
FORBIDS: "forbids"
REQUIRES: "requires"
UNLESS: "unless"
WITHIN: "within"
IMPORT: "import"
FROM: "from"
AS: "as"
EVENT: "event"
CONDITION: "condition"
PROPERTY: "property"
GROUP: "group"
STATEMACHINE: "statemachine"
INITIAL: "initial"
STATE: "state"
ON: "on"
TIMEOUT: "timeout"
RESET: "reset"
FORALL: "forall"
EXISTS: "exists"
IN: "in"
AND: "and"
OR: "or"
NOT: "not"
IMPLIES: "implies"
TRUE: "true"
FALSE: "false"

// Type keywords
INT: "int"
FLOAT: "float"
BOOL: "bool"
STRING: "string"
TIME: "time"
DURATION: "duration"

// Aggregation functions
COUNT: "count"
SUM: "sum"
MAX: "max"
MIN: "min"
AVG: "avg"
AGE: "age"
TIMESTAMP: "timestamp"
BUFFER: "buffer"
LAST: "last"
SIZE: "size"

// Operators
ARROW: "->"
ARROW_FUNC: "=>"
DOUBLE_COLON: "::"
COLON: ":"
COMMA: ","
DOT: "."
AT: "@"
LBRACE: "{"
RBRACE: "}"
LPAREN: "("
RPAREN: ")"
LBRACKET: "["
RBRACKET: "]"
EQ: "="
NE: "!="
LT: "<"
LE: "<="
GT: ">"
GE: ">="
PLUS: "+"
MINUS: "-"
STAR: "*"
SLASH: "/"
PERCENT: "%"

// Literals
NUMBER: /\d+(\.\d+)?([eE][+-]?\d+)?/
STRING_LITERAL: /"([^"\\]|\\.)*"/ | /'([^'\\]|\\.)*'/
TOPIC: /\/[\w\/]*/

// Identifiers
IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/

// Time units
TIME_UNIT: "s" | "ms" | "us" | "ns" | "m" | "h" | "d"

// Whitespace and comments
COMMENT: /#[^\n]*/
%import common.WS
%ignore WS
%ignore COMMENT
