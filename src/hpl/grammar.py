# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

PREDICATE_GRAMMAR = r"""
hpl_predicate: "{" condition "}"

hpl_expression: condition

condition: (condition IF_OPERATOR)? disjunction

disjunction: (disjunction OR_OPERATOR)? conjunction

conjunction: (conjunction AND_OPERATOR)? _logic_expr

_logic_expr: negation
           | quantification
           | atomic_condition

negation.5: NOT_OPERATOR _logic_expr

quantification.3: QUANT_OPERATOR CNAME _KW_IN _atomic_value ":" _logic_expr

atomic_condition: expr (RELATIONAL_OPERATOR expr)?

expr: (expr ADD_OPERATOR)? term

term: (term MULT_OPERATOR)? factor

factor: (factor POWER_OPERATOR)? _exponent

_exponent: _atomic_value
         | negative_number
         | "(" condition ")"

negative_number: MINUS_OPERATOR _exponent

_atomic_value: boolean
             | string
             | number_constant
             | number
             | function_call
             | enum_literal
             | range_literal
             | _reference

number_constant: CONSTANT

enum_literal: "{" _enum_member "}"

_enum_member: (_enum_member ",")? expr

range_literal: _start_range expr _KW_TO expr _end_range

_start_range: L_RANGE_EXC | L_RANGE_INC

_end_range: R_RANGE_EXC | R_RANGE_INC

variable: VAR_REF

function_call: CNAME "(" expr ")"

_base_ref: variable
         | own_field

own_field: CNAME

_reference: _base_ref
          | field_access
          | array_access

field_access: _reference "." CNAME

array_access: _reference "[" _index "]"

_index: expr

channel_name: CHANNEL_NAME

int_literal: INT
string: ESCAPED_STRING
number: NUMBER
signed_number: SIGNED_NUMBER
boolean: TRUE | FALSE

TRUE: "True"
FALSE: "False"

RELATIONAL_OPERATOR: EQ_OPERATOR | NEQ_OPERATOR | COMP_OPERATOR | IN_OPERATOR
EQ_OPERATOR: "="
NEQ_OPERATOR: "!="
COMP_OPERATOR: /<=?/ | />=?/
IN_OPERATOR.2: "in"

NOT_OPERATOR.3: "not"
IF_OPERATOR.3: IMPLIES_OPERATOR | IFF_OPERATOR
IMPLIES_OPERATOR.3: "implies"
IFF_OPERATOR.3: "iff"
OR_OPERATOR.3: "or"
AND_OPERATOR.3: "and"

QUANT_OPERATOR.4: ALL_OPERATOR | SOME_OPERATOR
ALL_OPERATOR.4: "forall"
SOME_OPERATOR.4: "exists"

CONSTANT.5: "PI" | "INF" | "NAN" | "E"
ADD_OPERATOR: "+" | "-"
MULT_OPERATOR: "*" | "/"
POWER_OPERATOR: "**"
MINUS_OPERATOR: "-"

L_RANGE_EXC: "!["
L_RANGE_INC: "["
R_RANGE_EXC: "]!"
R_RANGE_INC: "]"

_KW_TO.4: "to"
_KW_IN.4: "in"
_KW_AS.4: "as"
_KW_OR.4: "or"
_KW_WITHIN.4: "within"
_KW_NO.4: "no"
_KW_SOME.4: "some"
_KW_REQUIRES.4: "requires"
_KW_CAUSES.4: "causes"
_KW_FORBIDS.4: "forbids"
_KW_AFTER.4: "after"
_KW_UNTIL.4: "until"
_KW_GLOBALLY.4: "globally"

CHANNEL_NAME: /[\/~]?[a-zA-Z][0-9a-zA-Z_]*(\/[a-zA-Z][0-9a-zA-Z_]*)*/

VAR_REF: "@" CNAME

TIME_UNIT: "s" | "ms"
FREQ_UNIT: "hz"

%import common.CNAME
%import common.INT
%import common.NUMBER
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS

"""

HPL_GRAMMAR = r"""
hpl_file: _list_of_properties

_list_of_properties: (_list_of_properties)? hpl_property

hpl_property: [metadata] _scope ":" _pattern

metadata: _metadata_items

_metadata_items: (_metadata_items)? "#" _metadata_item

_metadata_item: metadata_id
              | metadata_title
              | metadata_desc

metadata_id: "id" ":" CNAME

metadata_title: "title" ":" ESCAPED_STRING

metadata_desc: "description" ":" ESCAPED_STRING

_scope: global_scope
      | after_until
      | until

global_scope: _KW_GLOBALLY

after_until: _KW_AFTER _activator [_KW_UNTIL _terminator]

until: _KW_UNTIL _terminator

_activator: _any_event

_terminator: _any_event

_pattern: existence
        | absence
        | response
        | prevention
        | requirement

existence: _KW_SOME _any_event _time_bound

absence: _KW_NO _any_event _time_bound

response: _any_event _KW_CAUSES _any_event _time_bound

prevention: _any_event _KW_FORBIDS _any_event _time_bound

requirement: _any_event _KW_REQUIRES _any_event _time_bound

_time_bound: [_KW_WITHIN time_amount]

_any_event: event
          | event_disjunction

event: channel_name [alias] [hpl_predicate]

event_disjunction: "(" (event _KW_OR)+ event ")"

time_amount: NUMBER TIME_UNIT

frequency: NUMBER FREQ_UNIT

alias: _KW_AS CNAME

hpl_predicate: "{" condition "}"

hpl_expression: condition

condition: (condition IF_OPERATOR)? disjunction

disjunction: (disjunction OR_OPERATOR)? conjunction

conjunction: (conjunction AND_OPERATOR)? _logic_expr

_logic_expr: negation
           | quantification
           | atomic_condition

negation.5: NOT_OPERATOR _logic_expr

quantification.3: QUANT_OPERATOR CNAME _KW_IN _atomic_value ":" _logic_expr

atomic_condition: expr (RELATIONAL_OPERATOR expr)?

expr: (expr ADD_OPERATOR)? term

term: (term MULT_OPERATOR)? factor

factor: (factor POWER_OPERATOR)? _exponent

_exponent: _atomic_value
         | negative_number
         | "(" condition ")"

negative_number: MINUS_OPERATOR _exponent

_atomic_value: boolean
             | string
             | number_constant
             | number
             | function_call
             | enum_literal
             | range_literal
             | _reference

number_constant: CONSTANT

enum_literal: "{" _enum_member "}"

_enum_member: (_enum_member ",")? expr

range_literal: _start_range expr _KW_TO expr _end_range

_start_range: L_RANGE_EXC | L_RANGE_INC

_end_range: R_RANGE_EXC | R_RANGE_INC

variable: VAR_REF

function_call: CNAME "(" expr ")"

_base_ref: variable
         | own_field

own_field: CNAME

_reference: _base_ref
          | field_access
          | array_access

field_access: _reference "." CNAME

array_access: _reference "[" _index "]"

_index: expr

channel_name: CHANNEL_NAME

int_literal: INT
string: ESCAPED_STRING
number: NUMBER
signed_number: SIGNED_NUMBER
boolean: TRUE | FALSE

TRUE: "True"
FALSE: "False"

RELATIONAL_OPERATOR: EQ_OPERATOR | NEQ_OPERATOR | COMP_OPERATOR | IN_OPERATOR
EQ_OPERATOR: "="
NEQ_OPERATOR: "!="
COMP_OPERATOR: /<=?/ | />=?/
IN_OPERATOR.2: "in"

NOT_OPERATOR.3: "not"
IF_OPERATOR.3: IMPLIES_OPERATOR | IFF_OPERATOR
IMPLIES_OPERATOR.3: "implies"
IFF_OPERATOR.3: "iff"
OR_OPERATOR.3: "or"
AND_OPERATOR.3: "and"

QUANT_OPERATOR.4: ALL_OPERATOR | SOME_OPERATOR
ALL_OPERATOR.4: "forall"
SOME_OPERATOR.4: "exists"

CONSTANT.5: "PI" | "INF" | "NAN" | "E"
ADD_OPERATOR: "+" | "-"
MULT_OPERATOR: "*" | "/"
POWER_OPERATOR: "**"
MINUS_OPERATOR: "-"

L_RANGE_EXC: "!["
L_RANGE_INC: "["
R_RANGE_EXC: "]!"
R_RANGE_INC: "]"

_KW_TO.4: "to"
_KW_IN.4: "in"
_KW_AS.4: "as"
_KW_OR.4: "or"
_KW_WITHIN.4: "within"
_KW_NO.4: "no"
_KW_SOME.4: "some"
_KW_REQUIRES.4: "requires"
_KW_CAUSES.4: "causes"
_KW_FORBIDS.4: "forbids"
_KW_AFTER.4: "after"
_KW_UNTIL.4: "until"
_KW_GLOBALLY.4: "globally"

CHANNEL_NAME: /[\/~]?[a-zA-Z][0-9a-zA-Z_]*(\/[a-zA-Z][0-9a-zA-Z_]*)*/

VAR_REF: "@" CNAME

TIME_UNIT: "s" | "ms"
FREQ_UNIT: "hz"

%import common.CNAME
%import common.INT
%import common.NUMBER
%import common.SIGNED_NUMBER
%import common.ESCAPED_STRING
%import common.WS
%ignore WS

"""

IN_OPERATOR = 'in'
NOT_OPERATOR = 'not'
IMPLIES_OPERATOR = 'implies'
IFF_OPERATOR = 'iff'
OR_OPERATOR = 'or'
AND_OPERATOR = 'and'
ALL_OPERATOR = 'forall'
SOME_OPERATOR = 'exists'
