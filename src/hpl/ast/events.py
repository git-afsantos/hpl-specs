# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from enum import Enum, auto
from typing import Iterator, Optional, Set, Tuple

from attrs import field, frozen
from attrs.validators import instance_of, in_

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import HplExpression, HplThisMessage
from hpl.ast.predicates import HplPredicate, HplVacuousTruth
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
        cls,
        name: str,
        predicate: Optional[HplPredicate] = None,
        alias: Optional[str] = None
    ) -> 'HplSimpleEvent':
        if predicate is None:
            predicate = HplVacuousTruth()
        return cls(name, predicate, EventType.PUBLISH, alias=alias)

    @property
    def is_publish(self):
        return self.event_type == self.PUBLISH

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

    def __str__(self) -> str:
        alias = (' as ' + self.alias) if self.alias is not None else ''
        assert self.is_publish, f'event_type: {self.event_type}'
        return f'{self.name}{alias} {self.predicate}'


@frozen
class HplEventDisjunction(HplEvent):
    __slots__ = ("event1", "event2")

    _DUP = "topic '{}' appears multiple times in an event disjunction"

    def __init__(self, event1, event2):
        if not event1.is_event:
            raise TypeError("not an event: " + str(event1))
        if not event2.is_event:
            raise TypeError("not an event: " + str(event2))
        self.event1 = event1 # HplEvent
        self.event2 = event2 # HplEvent
        self._check_unique_topics()

    @property
    def is_event_disjunction(self):
        return True

    @property
    def events(self):
        return (self.event1, self.event2)

    def children(self):
        return (self.event1, self.event2)

    def aliases(self):
        return self.event1.aliases() + self.event2.aliases()

    def external_references(self):
        return (self.event1.external_references()
                | self.event2.external_references())

    def contains_reference(self, alias):
        return (self.event1.contains_reference(alias)
                or self.event2.contains_reference(alias))

    def simple_events(self):
        if self.event1.is_simple_event:
            yield self.event1
        else:
            for event in self.event1.simple_events():
                yield event
        if self.event2.is_simple_event:
            yield self.event2
        else:
            for event in self.event2.simple_events():
                yield event

    def clone(self):
        return HplEventDisjunction(self.event1.clone(), self.event2.clone())

    def _check_unique_topics(self):
        topics = set()
        pending = [self.event1, self.event2]
        while pending:
            event = pending.pop()
            if event.is_event_disjunction:
                pending.append(event.event1)
                pending.append(event.event2)
            elif event.is_simple_event:
                assert event.is_publish
                if event.topic in topics:
                    raise HplSanityError(self._DUP.format(event.topic))
                topics.add(event.topic)
            else:
                assert False, "unknown event type"

    def __eq__(self, other):
        if not isinstance(other, HplEventDisjunction):
            return False
        return ((self.event1 == other.event1
                    and self.event2 == other.event2)
                or (self.event1 == other.event2
                    and self.event2 == other.event1))

    def __hash__(self):
        return 31 * hash(self.event1) + 31 * hash(self.event2)

    def __str__(self):
        return "({} or {})".format(self.event1, self.event2)

    def __repr__(self):
        return "{}({}, {})".format(
            type(self).__name__, repr(self.event1), repr(self.event2))
