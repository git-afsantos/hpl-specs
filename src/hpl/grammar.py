# -*- coding: utf-8 -*-

# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

PREDICATE_GRAMMAR = r"""
predicate: "{" condition "}"

top_level_condition: condition

condition: [condition IF_OPERATOR] disjunction

disjunction: [disjunction OR_OPERATOR] conjunction

conjunction: [conjunction AND_OPERATOR] _logic_expr

_logic_expr: negation
           | quantification
           | atomic_condition

negation: NOT_OPERATOR _logic_expr

quantification: QUANT_OPERATOR CNAME "in" _atomic_value ":" _logic_expr

atomic_condition: expr [RELATIONAL_OPERATOR expr]

expr: [expr ADD_OPERATOR] term

term: [term MULT_OPERATOR] factor

factor: [factor POWER_OPERATOR] _exponent

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

_enum_member: [_enum_member ","] expr

range_literal: _start_range expr "to" expr _end_range

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

ros_name: ROS_NAME

int_literal: INT
string: ESCAPED_STRING
number: NUMBER
signed_number: SIGNED_NUMBER
boolean: TRUE | FALSE

TRUE: "True"
FALSE: "False"

RELATIONAL_OPERATOR: EQ_OPERATOR | COMP_OPERATOR | IN_OPERATOR
EQ_OPERATOR: "=" | "!="
COMP_OPERATOR: "<" "="?
             | ">" "="?
IN_OPERATOR.2: "in"

NOT_OPERATOR.3: "not"
IF_OPERATOR.3: "implies" | "iff"
OR_OPERATOR.3: "or"
AND_OPERATOR.3: "and"

QUANT_OPERATOR.4: ALL_OPERATOR | SOME_OPERATOR
ALL_OPERATOR: "forall"
SOME_OPERATOR: "exists"

CONSTANT.5: "PI" | "INF" | "NAN"
ADD_OPERATOR: "+" | "-"
MULT_OPERATOR: "*" | "/"
POWER_OPERATOR: "**"
MINUS_OPERATOR: "-"

L_RANGE_EXC: "!["
L_RANGE_INC: "["
R_RANGE_EXC: "]!"
R_RANGE_INC: "]"

ROS_NAME: /[\/~]?[a-zA-Z][0-9a-zA-Z_]*(\/[a-zA-Z][0-9a-zA-Z_]*)*/

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

_list_of_properties: [_list_of_properties] hpl_property

hpl_property: metadata? _scope ":" _pattern

metadata: _metadata_items

_metadata_items: [_metadata_items] "#" _metadata_item

_metadata_item: metadata_id
              | metadata_title
              | metadata_desc

metadata_id: "id" ":" CNAME

metadata_title: "title" ":" ESCAPED_STRING

metadata_desc: "description" ":" ESCAPED_STRING

_scope: global_scope
      | after_until
      | until

global_scope: "globally"

after_until: "after" activator ["until" terminator]

until: "until" terminator

activator: event

terminator: event

_pattern: existence
        | absence
        | response
        | prevention
        | requirement

existence: "some" event _time_bound?

absence: "no" event _time_bound?

response: event "causes" event _time_bound?

prevention: event "forbids" event _time_bound?

requirement: event "requires" event _time_bound?

_time_bound: "within" time_amount

event: message predicate?

message: ros_name _alias?

time_amount: NUMBER TIME_UNIT

frequency: NUMBER FREQ_UNIT

_alias: "as" CNAME

predicate: "{" condition "}"

top_level_condition: condition

condition: [condition IF_OPERATOR] disjunction

disjunction: [disjunction OR_OPERATOR] conjunction

conjunction: [conjunction AND_OPERATOR] _logic_expr

_logic_expr: negation
           | quantification
           | atomic_condition

negation: NOT_OPERATOR _logic_expr

quantification: QUANT_OPERATOR CNAME "in" _atomic_value ":" _logic_expr

atomic_condition: expr [RELATIONAL_OPERATOR expr]

expr: [expr ADD_OPERATOR] term

term: [term MULT_OPERATOR] factor

factor: [factor POWER_OPERATOR] _exponent

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

_enum_member: [_enum_member ","] expr

range_literal: _start_range expr "to" expr _end_range

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

ros_name: ROS_NAME

int_literal: INT
string: ESCAPED_STRING
number: NUMBER
signed_number: SIGNED_NUMBER
boolean: TRUE | FALSE

TRUE: "True"
FALSE: "False"

RELATIONAL_OPERATOR: EQ_OPERATOR | COMP_OPERATOR | IN_OPERATOR
EQ_OPERATOR: "=" | "!="
COMP_OPERATOR: "<" "="?
             | ">" "="?
IN_OPERATOR.2: "in"

NOT_OPERATOR.3: "not"
IF_OPERATOR.3: "implies" | "iff"
OR_OPERATOR.3: "or"
AND_OPERATOR.3: "and"

QUANT_OPERATOR.4: ALL_OPERATOR | SOME_OPERATOR
ALL_OPERATOR: "forall"
SOME_OPERATOR: "exists"

CONSTANT.5: "PI" | "INF" | "NAN"
ADD_OPERATOR: "+" | "-"
MULT_OPERATOR: "*" | "/"
POWER_OPERATOR: "**"
MINUS_OPERATOR: "-"

L_RANGE_EXC: "!["
L_RANGE_INC: "["
R_RANGE_EXC: "]!"
R_RANGE_INC: "]"

ROS_NAME: /[\/~]?[a-zA-Z][0-9a-zA-Z_]*(\/[a-zA-Z][0-9a-zA-Z_]*)*/

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
