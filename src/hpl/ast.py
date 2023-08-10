# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Final, Iterable, Tuple

import enum
from math import isclose

from attrs import field, frozen

from hpl.errors import HplSanityError, HplTypeError

###############################################################################
# Constants
###############################################################################

INF: Final[float] = float('inf')





@frozen
class HplSpecification(HplAstObject):
    properties: Tuple['HplProperty']

    @property
    def is_specification(self):
        return True

    def children(self):
        return self.properties

    def sanity_check(self):
        for prop in self.properties:
            prop.sanity_check()

    def clone(self):
        return HplSpecification([p.clone() for p in self.properties])

    def __eq__(self, other):
        if not isinstance(other, HplSpecification):
            return False
        return set(self.properties) == set(other.properties)

    def __hash__(self):
        return hash(set(self.properties))

    def __str__(self):
        return "\n".join(str(prop) for prop in self.properties)

    def __repr__(self):
        return "{}({})".format(type(self).__name__, repr(self.properties))


class HplProperty(HplAstObject):
    __slots__ = ("scope", "pattern", "metadata")

    def __init__(self, scope, pattern, meta=None):
        self.scope = scope # HplScope
        self.pattern = pattern # HplPattern
        self.metadata = meta if meta is not None else {}

    @property
    def is_property(self):
        return True

    @property
    def is_safety(self):
        return self.pattern.is_safety

    @property
    def is_liveness(self):
        return self.pattern.is_liveness

    @property
    def uid(self):
        return self.metadata.get("id", None)

    def children(self):
        return (self.scope, self.pattern)

    def is_fully_typed(self):
        for event in self.events():
            for e in event.simple_events():
                if not e.predicate.is_fully_typed():
                    return False
        return True

    def refine_types(self, rostypes, aliases=None):
        # rostypes: string (topic) -> ROS Type Token
        # aliases:  string (alias) -> ROS Type Token
        for event in self.events():
            for e in event.simple_events():
                rostype = rostypes.get(e.topic)
                if rostype is None:
                    raise HplTypeError.undefined(e.topic)
                e.refine_types(rostype, aliases=aliases)

    def events(self):
        if self.scope.activator is not None:
            yield self.scope.activator
        yield self.pattern.behaviour
        if self.pattern.trigger is not None:
            yield self.pattern.trigger
        if self.scope.terminator is not None:
            yield self.scope.terminator

    def sanity_check(self):
        initial = self._check_activator()
        if self.pattern.is_absence or self.pattern.is_existence:
            self._check_behaviour(initial)
        elif self.pattern.is_requirement:
            aliases = self._check_behaviour(initial)
            self._check_trigger(aliases)
        elif self.pattern.is_response or self.pattern.is_prevention:
            aliases = self._check_trigger(initial)
            self._check_behaviour(aliases)
        else:
            assert False, 'unexpected pattern type: ' + repr(self.pattern.pattern_type)
        self._check_terminator(initial)

    def clone(self):
        return HplProperty(self.scope.clone(), self.pattern.clone(),
                           meta=dict(self.metadata))

    def _check_activator(self):
        p = self.scope.activator
        if p is not None:
            refs = p.external_references()
            if refs:
                raise HplSanityError(
                    "references to undefined events: " + repr(refs))
            return p.aliases()
        return ()

    def _check_trigger(self, available):
        a = self.pattern.trigger
        assert a is not None
        self._check_refs_defined(a.external_references(), available)
        aliases = a.aliases()
        self._check_duplicates(aliases, available)
        return aliases + available

    def _check_behaviour(self, available):
        b = self.pattern.behaviour
        self._check_refs_defined(b.external_references(), available)
        aliases = b.aliases()
        self._check_duplicates(aliases, available)
        return aliases + available

    def _check_terminator(self, available):
        q = self.scope.terminator
        if q is not None:
            self._check_refs_defined(q.external_references(), available)
            self._check_duplicates(q.aliases(), available)

    def _check_refs_defined(self, refs, available):
        for ref in refs:
            if not ref in available:
                raise HplSanityError(
                    "reference to undefined event: " + repr(ref))

    def _check_duplicates(self, aliases, available):
        for alias in aliases:
            if alias in available:
                raise HplSanityError("duplicate alias: " + repr(alias))

    def __eq__(self, other):
        if not isinstance(other, HplProperty):
            return False
        return self.pattern == other.pattern and self.scope == other.scope

    def __hash__(self):
        return 31 * hash(self.scope) + hash(self.pattern)

    def __str__(self):
        return "{}: {}".format(self.scope, self.pattern)

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__,
            repr(self.scope), repr(self.pattern))


class HplScope(HplAstObject):
    __slots__ = ("scope_type", "activator", "terminator")

    GLOBAL = 1
    AFTER_UNTIL = 2
    AFTER = 3
    UNTIL = 4

    def __init__(self, scope, activator=None, terminator=None):
        if scope == self.GLOBAL:
            if activator is not None:
                raise ValueError(activator)
            if terminator is not None:
                raise ValueError(terminator)
        elif scope == self.AFTER:
            if terminator is not None:
                raise ValueError(terminator)
        elif scope == self.UNTIL:
            if activator is not None:
                raise ValueError(activator)
        elif scope != self.AFTER_UNTIL:
            raise ValueError(scope)
        self.scope_type = scope
        self.activator = activator # HplEvent | None
        self.terminator = terminator # HplEvent | None

    @property
    def is_scope(self):
        return True

    @classmethod
    def globally(cls):
        return cls(cls.GLOBAL)

    @classmethod
    def after(cls, activator):
        return cls(cls.AFTER, activator=activator)

    @classmethod
    def until(cls, terminator):
        return cls(cls.UNTIL, terminator=terminator)

    @classmethod
    def after_until(cls, activator, terminator):
        return cls(cls.AFTER_UNTIL, activator=activator, terminator=terminator)

    @property
    def is_global(self):
        return self.scope_type == self.GLOBAL

    @property
    def is_after(self):
        return self.scope_type == self.AFTER

    @property
    def is_until(self):
        return self.scope_type == self.UNTIL

    @property
    def is_after_until(self):
        return self.scope_type == self.AFTER_UNTIL

    def children(self):
        if self.activator is None and self.terminator is None:
            return ()
        if self.activator is None:
            return (self.terminator,)
        if self.terminator is None:
            return (self.activator,)
        return (self.activator, self.terminator)

    def clone(self):
        p = None if self.activator is None else self.activator.clone()
        q = None if self.terminator is None else self.terminator.clone()
        return HplScope(self.scope_type, activator=p, terminator=q)

    def __eq__(self, other):
        if not isinstance(other, HplScope):
            return False
        return (self.scope_type == other.scope_type
                and self.activator == other.activator
                and self.terminator == other.terminator)

    def __hash__(self):
        h = 31 * hash(self.scope_type) + hash(self.activator)
        h = 31 * h + hash(self.terminator)
        return h

    def __str__(self):
        if self.scope_type == self.GLOBAL:
            return "globally"
        if self.scope_type == self.AFTER:
            return "after {}".format(self.activator)
        if self.scope_type == self.UNTIL:
            return "until {}".format(self.terminator)
        if self.scope_type == self.AFTER_UNTIL:
            return "after {} until {}".format(self.activator, self.terminator)
        assert False, "unexpected scope type"

    def __repr__(self):
        return "{}({}, activator={}, terminator={})".format(
            type(self).__name__, repr(self.scope_type),
            repr(self.activator), repr(self.terminator))


class HplPattern(HplAstObject):
    __slots__ = ("pattern_type", "behaviour", "trigger", "min_time", "max_time")

    EXISTENCE = 1
    ABSENCE = 2
    RESPONSE = 3
    REQUIREMENT = 4
    PREVENTION = 5

    def __init__(self, pattern, behaviour, trigger, min_time=0.0, max_time=INF):
        if pattern == self.EXISTENCE or pattern == self.ABSENCE:
            if trigger is not None:
                raise ValueError(trigger)
        elif (pattern != self.RESPONSE and pattern != self.REQUIREMENT
                and pattern != self.PREVENTION):
            raise ValueError(pattern)
        self.pattern_type = pattern
        self.behaviour = behaviour # HplEvent
        self.trigger = trigger # HplEvent | None
        self.min_time = min_time
        self.max_time = max_time

    @property
    def is_pattern(self):
        return True

    @classmethod
    def existence(cls, behaviour, min_time=0.0, max_time=INF):
        return cls(cls.EXISTENCE, behaviour, None,
            min_time=min_time, max_time=max_time)

    @classmethod
    def absence(cls, behaviour, min_time=0.0, max_time=INF):
        return cls(cls.ABSENCE, behaviour, None,
            min_time=min_time, max_time=max_time)

    @classmethod
    def response(cls, event, response, min_time=0.0, max_time=INF):
        return cls(cls.RESPONSE, response, event,
            min_time=min_time, max_time=max_time)

    @classmethod
    def requirement(cls, event, requirement, min_time=0.0, max_time=INF):
        return cls(cls.REQUIREMENT, event, requirement,
            min_time=min_time, max_time=max_time)

    @classmethod
    def prevention(cls, event, forbidden, min_time=0.0, max_time=INF):
        return cls(cls.PREVENTION, forbidden, event,
            min_time=min_time, max_time=max_time)

    @property
    def is_safety(self):
        return (self.pattern_type == self.ABSENCE
                or self.pattern_type == self.REQUIREMENT
                or self.pattern_type == self.PREVENTION)

    @property
    def is_liveness(self):
        return (self.pattern_type == self.EXISTENCE
                or self.pattern_type == self.RESPONSE)

    @property
    def is_absence(self):
        return self.pattern_type == self.ABSENCE

    @property
    def is_existence(self):
        return self.pattern_type == self.EXISTENCE

    @property
    def is_requirement(self):
        return self.pattern_type == self.REQUIREMENT

    @property
    def is_response(self):
        return self.pattern_type == self.RESPONSE

    @property
    def is_prevention(self):
        return self.pattern_type == self.PREVENTION

    @property
    def has_min_time(self):
        return self.min_time > 0.0 and self.min_time < INF

    @property
    def has_max_time(self):
        return self.max_time >= 0.0 and self.max_time < INF

    def children(self):
        if self.trigger is None:
            return (self.behaviour,)
        return (self.trigger, self.behaviour)

    def clone(self):
        b = self.behaviour.clone()
        a = None if self.trigger is None else self.trigger.clone()
        return HplPattern(self.pattern_type, b, a, min_time=self.min_time,
                          max_time=self.max_time)

    def __eq__(self, other):
        if not isinstance(other, HplPattern):
            return False
        return (self.pattern_type == other.pattern_type
                and self.behaviour == other.behaviour
                and self.trigger == other.trigger
                and isclose(self.min_time, other.min_time)
                and ((self.max_time == INF and other.max_time == INF)
                    or isclose(self.max_time, other.max_time)))

    def __hash__(self):
        h = 31 * hash(self.pattern_type) + hash(self.behaviour)
        h = 31 * h + hash(self.trigger)
        h = 31 * h + hash(self.min_time)
        h = 31 * h + hash(self.max_time)
        return h

    def __str__(self):
        t = ""
        if self.max_time < INF:
            t = " within {}s".format(self.max_time)
        if self.pattern_type == self.EXISTENCE:
            return "some {}{}".format(self.behaviour, t)
        if self.pattern_type == self.ABSENCE:
            return "no {}{}".format(self.behaviour, t)
        if self.pattern_type == self.RESPONSE:
            return "{} causes {}{}".format(self.trigger, self.behaviour, t)
        if self.pattern_type == self.REQUIREMENT:
            return "{} requires {}{}".format(self.behaviour, self.trigger, t)
        if self.pattern_type == self.PREVENTION:
            return "{} forbids {}{}".format(self.trigger, self.behaviour, t)
        assert False, "unexpected observable pattern"

    def __repr__(self):
        return "{}({}, {}, {}, min_time={}, max_time={})".format(
            type(self).__name__, repr(self.pattern_type), repr(self.behaviour),
            repr(self.trigger), repr(self.min_time), repr(self.max_time))


###############################################################################
# Events and Event Operators
###############################################################################

class HplEvent(HplAstObject):
    @property
    def is_event(self):
        return True

    @property
    def is_simple_event(self):
        return False

    @property
    def is_event_disjunction(self):
        return False

    def aliases(self):
        return ()

    def external_references(self):
        return set()

    def contains_reference(self, alias):
        return False

    def simple_events(self):
        raise NotImplementedError()


class HplSimpleEvent(HplEvent):
    __slots__ = ("event_type", "predicate", "topic", "alias", "msg_type")

    PUBLISH = 1

    def __init__(self, event_type, predicate, topic, alias=None):
        if event_type != self.PUBLISH:
            raise ValueError(event_type)
        if not predicate.is_predicate:
            raise TypeError("not a predicate: " + str(predicate))
        self.event_type = event_type
        self.predicate = predicate # HplExpression
        self.topic = topic # string
        self.alias = alias # string
        self.msg_type = None # ROS Type Token
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
