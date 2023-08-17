# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Iterator, Mapping, Optional, Set, Tuple

from enum import Enum, auto

from attrs import field, frozen
from attrs.validators import in_, instance_of

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import HplExpression, HplThisMessage
from hpl.ast.predicates import HplPredicate, HplVacuousTruth
from hpl.errors import HplSanityError
from hpl.types import TypeToken

###############################################################################
# Events and Event Operators
###############################################################################


@frozen
class HplEvent(HplAstObject):
    @property
    def is_event(self) -> bool:
        return True

    @property
    def is_simple_event(self) -> bool:
        return False

    @property
    def is_event_disjunction(self) -> bool:
        return False

    def aliases(self) -> Tuple[str]:
        return ()

    def external_references(self) -> Set[str]:
        return set()

    def contains_reference(self, alias: str) -> bool:
        raise NotImplementedError()

    def contains_self_reference(self) -> bool:
        raise NotImplementedError()

    def replace_var_reference(self, alias: str, expr: HplExpression) -> 'HplEvent':
        raise NotImplementedError()

    def simple_events(self) -> Iterator['HplEvent']:
        raise NotImplementedError()

    def type_check_references(self, msg_types: Mapping[str, TypeToken]) -> None:
        raise NotImplementedError()


class EventType(Enum):
    PUBLISH = auto()


@frozen
class HplSimpleEvent(HplEvent):
    name: str
    predicate: HplPredicate = field(validator=instance_of(HplPredicate))
    event_type: EventType = field(validator=in_(EventType))
    alias: Optional[str] = None
    message_type: Optional[TypeToken] = None

    def __attrs_post_init__(self):
        if self.alias:
            phi = self.predicate.replace_var_reference(self.alias, HplThisMessage())
            object.__setattr__(self, 'predicate', phi)

    @property
    def is_simple_event(self) -> bool:
        return True

    @classmethod
    def publish(
        cls, name: str, predicate: Optional[HplPredicate] = None, alias: Optional[str] = None
    ) -> 'HplSimpleEvent':
        if predicate is None:
            predicate = HplVacuousTruth()
        return cls(name, predicate, EventType.PUBLISH, alias=alias)

    @property
    def is_publish(self):
        return self.event_type is EventType.PUBLISH

    @property
    def phi(self) -> HplPredicate:
        return self.predicate

    def children(self) -> Tuple[HplPredicate]:
        return (self.predicate,)

    def aliases(self) -> Tuple[str]:
        if self.alias is None:
            return ()
        return (self.alias,)

    def external_references(self) -> Set[str]:
        refs = self.predicate.external_references()
        if self.alias:
            refs.discard(self.alias)
        return refs

    def contains_reference(self, alias: str) -> bool:
        return self.predicate.contains_reference(alias)

    def contains_self_reference(self) -> bool:
        it_does: bool = self.predicate.contains_self_reference()
        if it_does:
            return True
        return self.alias and self.predicate.contains_reference(self.alias)

    def replace_var_reference(self, alias: str, expr: HplExpression) -> HplEvent:
        phi = self.predicate.replace_var_reference(alias, expr)
        return self.but(predicate=phi)

    def simple_events(self) -> Iterator[HplEvent]:
        yield self

    def type_check_references(self, msg_types: Mapping[str, TypeToken]) -> None:
        this_msg = msg_types[self.name]
        self.predicate.type_check_references(this_msg, variables=msg_types)

    def __str__(self) -> str:
        alias = (' as ' + self.alias) if self.alias is not None else ''
        assert self.is_publish, f'event_type: {self.event_type}'
        return f'{self.name}{alias} {self.predicate}'


@frozen
class HplEventDisjunction(HplEvent):
    event1: HplEvent = field(validator=instance_of(HplEvent))
    event2: HplEvent = field(validator=instance_of(HplEvent))

    def __attrs_post_init__(self):
        names = set()
        pending = list(self.simple_events())
        while pending:
            event = pending.pop()
            assert event.is_simple_event
            if event.name in names:
                raise HplSanityError.duplicate_event(event.name, self)
            names.add(event.name)

    @property
    def is_event_disjunction(self) -> bool:
        return True

    @property
    def events(self) -> Tuple[HplEvent, HplEvent]:
        return (self.event1, self.event2)

    def children(self) -> Tuple[HplEvent, HplEvent]:
        return (self.event1, self.event2)

    def aliases(self) -> Tuple[str]:
        return self.event1.aliases() + self.event2.aliases()

    def external_references(self) -> Set[str]:
        return self.event1.external_references() | self.event2.external_references()

    def contains_reference(self, alias: str) -> bool:
        return self.event1.contains_reference(alias) or self.event2.contains_reference(alias)

    def contains_self_reference(self) -> bool:
        return self.event1.contains_self_reference() or self.event2.contains_self_reference()

    def replace_var_reference(self, alias: str, expr: HplExpression) -> 'HplEventDisjunction':
        e1 = self.event1.replace_var_reference(alias, expr)
        e2 = self.event2.replace_var_reference(alias, expr)
        if e1 is self.event1 and e2 is self.event2:
            return self
        return self.but(event1=e1, event2=e2)

    def simple_events(self) -> Iterator[HplEvent]:
        for event in self.event1.simple_events():
            yield event
        for event in self.event2.simple_events():
            yield event

    def type_check_references(self, msg_types: Mapping[str, TypeToken]) -> None:
        self.event1.type_check_references(msg_types)
        self.event2.type_check_references(msg_types)

    def __str__(self) -> str:
        return f'({self.event1} or {self.event2})'
