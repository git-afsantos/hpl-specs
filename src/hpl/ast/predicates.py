# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Dict, List, Mapping, Optional, Set, Tuple

from attrs import field, frozen
from attrs.validators import instance_of

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import (
    And,
    BuiltinUnaryOperator,
    DataType,
    HplDataAccess,
    HplExpression,
    HplFieldAccess,
    HplLiteral,
    HplValue,
    Not,
)
from hpl.errors import HplSanityError, invalid_type
from hpl.types import TypeToken

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

    def join(self, other: 'HplPredicate') -> 'HplPredicate':
        raise NotImplementedError()

    def external_references(self) -> Set[str]:
        return self.condition.external_references()

    def contains_reference(self, alias: str) -> bool:
        return self.condition.contains_reference(alias)

    def contains_self_reference(self) -> bool:
        return self.condition.contains_self_reference()

    def replace_var_reference(self, alias: str, expr: HplExpression) -> 'HplPredicate':
        raise NotImplementedError()

    def replace_self_reference(self, expr: HplExpression) -> 'HplPredicate':
        raise NotImplementedError()

    def type_check_references(
        self,
        this_msg: TypeToken,
        variables: Optional[Mapping[str, TypeToken]] = None,
    ):
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
        ref_table = _get_reference_table(expr)
        self._all_refs_same_type(ref_table)
        # self._some_field_refs(ref_table)

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

    def check_some_self_references(self):
        ref_table = _get_reference_table(self.expression)
        self._some_field_refs(ref_table)

    def _some_field_refs(self, table: Dict[str, List[HplExpression]]):
        # There is at least one reference to a field (own).
        #   [NYI] Stricter: one reference per atomic condition.
        for ref_group in table.values():
            for ref in ref_group:
                if not ref.is_accessor:
                    break
                assert isinstance(ref, HplDataAccess)
                if ref.is_indexed:
                    break
                assert isinstance(ref, HplFieldAccess)
                if not ref.message.is_value:
                    break
                assert isinstance(ref.message, HplValue)
                assert ref.message.is_reference
                if not ref.message.is_this_msg:
                    break
                return  # OK
        raise HplSanityError.predicate_without_self_refs(self)

    @property
    def condition(self) -> HplExpression:
        return self.expression

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
        return self.but(expression=phi)

    def replace_self_reference(self, expr: HplExpression) -> HplPredicate:
        phi: HplExpression = self.expression.replace_self_reference(expr)
        return self.but(expression=phi)

    def type_check_references(
        self,
        this_msg: TypeToken,
        variables: Optional[Mapping[str, TypeToken]] = None,
    ):
        return self.expression.type_check_references(this_msg, variables=variables)

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

    @property
    def condition(self) -> HplExpression:
        return HplLiteral('True', True)

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

    def type_check_references(
        self,
        this_msg: TypeToken,
        variables: Optional[Mapping[str, TypeToken]] = None,
    ):
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

    @property
    def condition(self) -> HplExpression:
        return HplLiteral('False', False)

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

    def type_check_references(
        self,
        this_msg: TypeToken,
        variables: Optional[Mapping[str, TypeToken]] = None,
    ):
        pass

    def __str__(self) -> str:
        return '{ False }'


###############################################################################
# Helper Functions
###############################################################################


def _get_reference_table(expr: HplExpression) -> Dict[str, List[HplExpression]]:
    ref_table = {}
    for obj in expr.iterate():
        assert isinstance(obj, HplExpression)
        if obj.is_accessor or (obj.is_value and obj.is_variable):
            key = str(obj)
            refs = ref_table.get(key)
            if refs is None:
                refs = []
                ref_table[key] = refs
            refs.append(obj)
    return ref_table


def predicate_from_expression(expr: HplExpression) -> HplPredicate:
    if not expr.can_be_bool:
        raise invalid_type('boolean', expr)
    if expr.is_value and expr.is_literal:
        assert isinstance(expr, HplLiteral)
        assert isinstance(expr.value, bool)
        return HplVacuousTruth() if expr.value else HplContradiction()
    return HplPredicateExpression(expr)
