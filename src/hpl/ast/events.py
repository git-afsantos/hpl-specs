# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from enum import Enum, auto
from typing import Iterator, Optional, Set, Tuple

from attrs import field, frozen
from attrs.validators import instance_of

from hpl.ast.base import HplAstObject
from hpl.ast.expressions import HplExpression
from hpl.ast.predicates import HplPredicate
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
    event_type: EventType
    predicate: HplPredicate = field(validator=instance_of(HplPredicate))
    name: str
    alias: Optional[str] = None
    msg_type: Optional[TypeToken] = None

    def __init__(self, event_type, predicate, topic, alias=None):
        if event_type != self.PUBLISH:
            raise ValueError(event_type)
        if not predicate.is_predicate:
            raise TypeError("not a predicate: " + str(predicate))
        if alias:
            predicate.replace_self_reference(alias)

    @property
    def is_simple_event(self):
        return True

    @classmethod
    def publish(cls, topic, predicate=None, alias=None):
        if predicate is None:
            predicate = HplVacuousTruth()
        return cls(cls.PUBLISH, predicate, topic, alias=alias)

    @property
    def is_publish(self):
        return self.event_type == self.PUBLISH

    @property
    def phi(self):
        return self.predicate

    @property
    def ros_type(self):
        return self.msg_type

    def children(self):
        return (self.predicate,)

    def aliases(self):
        if self.alias is None:
            return ()
        return (self.alias,)

    def external_references(self):
        refs = set()
        for obj in self.predicate.iterate():
            if obj.is_expression and obj.is_accessor:
                if obj.is_field and obj.message.is_value:
                    if obj.message.is_variable:
                        refs.add(obj.message.name)
        if self.alias is not None:
            refs.discard(self.alias)
        return refs

    def contains_reference(self, alias):
        return self.predicate.contains_reference(alias)

    def refine_types(self, rostype, aliases=None):
        if self.msg_type is not None:
            if rostype == self.msg_type:
                return
            raise HplTypeError.already_defined(
                self.topic, self.msg_type, rostype)
        self.predicate.refine_types(rostype, aliases=aliases)

    def simple_events(self):
        yield self

    def clone(self):
        p = self.predicate.clone()
        event = HplSimpleEvent(self.event_type, p, self.topic, alias=self.alias)
        event.msg_type = self.msg_type
        return event

    def __eq__(self, other):
        if not isinstance(other, HplSimpleEvent):
            return False
        return (self.event_type == other.event_type
                and self.predicate == other.predicate
                and self.topic == other.topic)

    def __hash__(self):
        h = 31 * hash(self.event_type) + hash(self.predicate)
        return 31 * h + hash(self.topic)

    def __str__(self):
        alias = (" as " + self.alias) if self.alias is not None else ""
        if self.event_type == self.PUBLISH:
            return "{}{} {}".format(self.topic, alias, self.predicate)
        else:
            assert False, "unexpected event type"

    def __repr__(self):
        return "{}({}, {}, {}, alias={})".format(
            type(self).__name__, repr(self.event_type), repr(self.predicate),
            repr(self.topic), repr(self.alias))


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
