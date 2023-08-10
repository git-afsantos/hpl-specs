# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, List, Set, Tuple

from attrs import evolve, field, frozen
from attrs.validators import instance_of

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import And, BuiltinUnaryOperator, DataType, HplExpression, HplVarReference, Not
from hpl.errors import HplSanityError

###############################################################################
# Top-level Predicate
###############################################################################


@frozen
class HplPredicate(HplAstObject):
    @property
    def is_predicate(self) -> bool:
        return True

    @property
    def is_vacuous(self) -> bool:
        return False

    @property
    def condition(self) -> HplExpression:
        raise NotImplementedError()
    
    @property
    def phi(self) -> HplExpression:
        return self.condition

    def is_fully_typed(self) -> bool:
        return self.condition.is_fully_typed()

    def negate(self) -> 'HplPredicate':
        raise NotImplementedError()

    def join(self, _other: 'HplPredicate') -> 'HplPredicate':
        raise NotImplementedError()

    def external_references(self) -> Set[str]:
        return self.condition.external_references()

    def contains_reference(self, alias: str) -> bool:
        return self.condition.contains_reference(alias)

    def contains_self_reference(self) -> bool:
        return self.condition.contains_self_reference()

    def replace_var_reference(self, _alias: str, _expr: HplExpression) -> 'HplPredicate':
        raise NotImplementedError()

    def replace_self_reference(self, _expr: HplExpression) -> 'HplPredicate':
        raise NotImplementedError()

    def refine_types(self, _type_token, _aliases=None) -> 'HplPredicate':
        raise NotImplementedError()


###############################################################################
# General Predicates
###############################################################################


@frozen
class HplPredicateExpression(HplPredicate):
    expression: HplExpression = field(validator=instance_of(HplExpression))

    @expression.validator
    def _check_expression(self, _attribute, expr: HplExpression):
        if not expr.can_be_bool:
            raise TypeError(f'not a boolean expression: {{{expr}}}')
        ref_table = {}
        for obj in expr.iterate():
            if obj.is_accessor or (obj.is_value and obj.is_variable):
                key = str(obj)
                refs = ref_table.get(key)
                if refs is None:
                    refs = []
                    ref_table[key] = refs
                refs.append(obj)
        self._all_refs_same_type(ref_table)
        self._some_field_refs(ref_table)

    def _all_refs_same_type(self, table: Dict[str, List[HplExpression]]):
        # All references to the same field/variable have the same type.
        for ref_group in table.values():
            # must traverse twice, in case we start with the most generic
            # and go down to the most specific
            final_type = DataType.ANY
            for ref in ref_group:
                final_type = ref.data_type.cast(final_type)
            for ref in reversed(ref_group):
                final_type = ref.data_type.cast(final_type)

    def _some_field_refs(self, table: Dict[str, List[HplExpression]]):
        # There is at least one reference to a field (own).
        #   [NYI] Stricter: one reference per atomic condition.
        for ref_group in table.values():
            for ref in ref_group:
                if not ref.is_accessor:
                    break
                if ref.is_indexed:
                    break
                if not ref.message.is_value:
                    break
                assert ref.message.is_reference
                if not ref.message.is_this_msg:
                    break
                return  # OK
        raise HplSanityError.predicate_without_self_refs(self)

    def children(self) -> Tuple[HplExpression]:
        return (self.expression,)

    def negate(self) -> HplPredicate:
        if self.expression.is_operator:
            if self.expression.operator == BuiltinUnaryOperator.NOT.value:
                return HplPredicateExpression(self.expression.operand)
        return HplPredicateExpression(Not(self.expression))

    def join(self, other: HplPredicate) -> HplPredicate:
        if other.is_vacuous:
            return self if other.is_true else other
        expr = And(self.expression, other.condition)
        return HplPredicateExpression(expr)

    def replace_var_reference(self, alias: str, expr: HplExpression) -> HplPredicate:
        phi: HplExpression = self.expression.replace_var_reference(alias, expr)
        return evolve(self, expression=phi)

    def replace_self_reference(self, expr: HplExpression) -> HplPredicate:
        phi: HplExpression = self.expression.replace_self_reference(expr)
        return evolve(self, expression=expr)

    def refine_types(self, rostype, aliases=None):
        # rostype: ROS Type Token
        # aliases: string (alias) -> ROS Type Token
        aliases = aliases if aliases is not None else {}
        stack = [self.condition]
        while stack:
            obj = stack.pop()
            if obj.is_accessor:
                self._refine_type(obj, rostype, aliases)
            else:
                stack.extend(reversed(obj.children()))

    def _refine_type(self, accessor, rostype, aliases):
        stack = [accessor]
        expr = accessor.message
        while expr.is_accessor:
            stack.append(expr)
            expr = expr.message
        assert expr.is_value and (expr.is_this_msg or expr.is_variable)
        if expr.is_this_msg:
            t = rostype
        else:
            if expr.name not in aliases:
                raise HplSanityError(
                    "undefined message alias: '{}'".format(expr.name))
            t = aliases[expr.name]
        assert t.is_message
        expr.ros_type = t
        while stack:
            expr = stack.pop()
            if expr.is_field:
                if not (t.is_message or expr.field in t.fields
                        or expr.field in t.constants):
                    raise HplTypeError.ros_field(t, expr.field, expr)
                if expr.field in t.fields:
                    t = t.fields[expr.field]
                else:
                    assert expr.field in t.constants, \
                        "'{}' not in {} or {}".format(
                            expr.field, t.fields, t.constants)
                    t = t.constants[expr.field].ros_type
            else:
                assert expr.is_indexed
                if not t.is_array:
                    raise HplTypeError.ros_array(t, expr)
                i = expr.index
                if (i.is_value and i.is_literal
                        and not t.contains_index(i.value)):
                    raise HplTypeError.ros_index(t, expr.index, expr)
                t = t.type_token
            if t.is_message:
                accessor._type_check(expr, T_MSG)
            elif t.is_array:
                accessor._type_check(expr, T_ARR)
            elif t.is_number:
                accessor._type_check(expr, T_NUM)
                # TODO check that values fit within types
            elif t.is_bool:
                accessor._type_check(expr, T_BOOL)
            elif t.is_string:
                accessor._type_check(expr, T_STR)
            expr.ros_type = t

    def __str__(self) -> str:
        return f'{{ {self.expression} }}'


###############################################################################
# Vacuous Predicates
###############################################################################


@frozen
class HplVacuousTruth(HplPredicate):
    @property
    def is_vacuous(self) -> bool:
        return True

    @property
    def is_true(self) -> bool:
        return True

    def is_fully_typed(self) -> bool:
        return True

    def negate(self) -> HplPredicate:
        return HplContradiction()

    def join(self, other: HplPredicate):
        return other

    def external_references(self) -> Set[str]:
        return set()

    def contains_reference(self, _alias: str) -> bool:
        return False

    def contains_self_reference(self) -> bool:
        return False

    def replace_var_reference(self, _alias: str, _expr: HplExpression) -> HplPredicate:
        return self

    def replace_self_reference(self, _expr: HplExpression) -> HplPredicate:
        return self

    def refine_types(self, rostype, aliases=None):
        pass

    def __str__(self) -> str:
        return '{ True }'


@frozen
class HplContradiction(HplPredicate):
    @property
    def is_vacuous(self) -> bool:
        return True

    @property
    def is_true(self) -> bool:
        return False

    def is_fully_typed(self) -> bool:
        return True

    def negate(self) -> HplPredicate:
        return HplVacuousTruth()

    def join(self, other: HplPredicate) -> HplPredicate:
        return self

    def external_references(self) -> Set[str]:
        return set()

    def contains_reference(self, _alias: str) -> bool:
        return False

    def contains_self_reference(self) -> bool:
        return False

    def replace_var_reference(self, _alias: str, _expr: HplExpression) -> HplPredicate:
        return self

    def replace_self_reference(self, _expr: HplExpression) -> HplPredicate:
        return self

    def refine_types(self, rostype, aliases=None):
        pass

    def __str__(self) -> str:
        return '{ False }'
