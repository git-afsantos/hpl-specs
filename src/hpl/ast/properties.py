# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from typing import Final, Iterator, Mapping, Optional, Tuple

from enum import Enum, auto

from attrs import field, frozen
from attrs.validators import ge, in_, instance_of, optional

from hpl.ast.base import HplAstObject
from hpl.ast.events import HplEvent, HplSimpleEvent
from hpl.errors import HplSanityError, expected_not_none, invalid_attr
from hpl.types import TypeToken

###############################################################################
# Constants
###############################################################################

INF: Final[float] = float('inf')

###############################################################################
# Scopes
###############################################################################


class ScopeType(Enum):
    GLOBAL = auto()
    AFTER_UNTIL = auto()
    AFTER = auto()
    UNTIL = auto()

    @property
    def is_after(self) -> bool:
        return self is ScopeType.AFTER or self is ScopeType.AFTER_UNTIL

    @property
    def is_until(self) -> bool:
        return self is ScopeType.UNTIL or self is ScopeType.AFTER_UNTIL

    @property
    def is_global(self) -> bool:
        return self is ScopeType.GLOBAL

    @property
    def should_have_activator(self) -> bool:
        return self.is_after

    @property
    def should_have_terminator(self) -> bool:
        return self.is_until


@frozen
class HplScope(HplAstObject):
    scope_type: ScopeType = field(validator=in_(ScopeType))
    activator: Optional[HplEvent] = field(
        default=None,
        validator=optional(instance_of(HplEvent)),
    )
    terminator: Optional[HplEvent] = field(
        default=None,
        validator=optional(instance_of(HplEvent)),
    )

    @activator.validator
    def _check_activator(self, attribute, event: Optional[HplEvent]):
        if self.scope_type.should_have_activator:
            if event is None:
                raise expected_not_none(attribute.name, self)
        else:
            if event is not None:
                raise invalid_attr(attribute.name, None, event, self)

    @terminator.validator
    def _check_terminator(self, attribute, event: Optional[HplEvent]):
        if self.scope_type.should_have_terminator:
            if event is None:
                raise expected_not_none(attribute.name, self)
        else:
            if event is not None:
                raise invalid_attr(attribute.name, None, event, self)

    @property
    def is_scope(self) -> bool:
        return True

    @classmethod
    def globally(cls) -> 'HplScope':
        return cls(ScopeType.GLOBAL)

    @classmethod
    def after(cls, activator: HplEvent) -> 'HplScope':
        return cls(ScopeType.AFTER, activator=activator)

    @classmethod
    def until(cls, terminator: HplEvent) -> 'HplScope':
        return cls(ScopeType.UNTIL, terminator=terminator)

    @classmethod
    def after_until(cls, activator: HplEvent, terminator: HplEvent) -> 'HplScope':
        return cls(ScopeType.AFTER_UNTIL, activator=activator, terminator=terminator)

    @property
    def is_global(self) -> bool:
        return self.scope_type.is_global

    @property
    def is_after(self) -> bool:
        return self.scope_type.is_after

    @property
    def is_until(self) -> bool:
        return self.scope_type.is_until

    @property
    def has_activator(self) -> bool:
        return self.activator is not None

    @property
    def has_terminator(self) -> bool:
        return self.terminator is not None

    def children(self) -> Tuple[HplEvent]:
        if self.activator is None and self.terminator is None:
            return ()
        if self.activator is None:
            return (self.terminator,)
        if self.terminator is None:
            return (self.activator,)
        return (self.activator, self.terminator)

    def __str__(self) -> str:
        if self.scope_type == ScopeType.GLOBAL:
            return 'globally'
        if self.scope_type == ScopeType.AFTER:
            return f'after {self.activator}'
        if self.scope_type == ScopeType.UNTIL:
            return f'until {self.terminator}'
        if self.scope_type == ScopeType.AFTER_UNTIL:
            return f'after {self.activator} until {self.terminator}'
        return self.scope_type.name


###############################################################################
# Patterns
###############################################################################


class PatternType(Enum):
    ABSENCE = auto()
    EXISTENCE = auto()
    REQUIREMENT = auto()
    RESPONSE = auto()
    PREVENTION = auto()

    @property
    def is_safety(self) -> bool:
        return (
            self is PatternType.ABSENCE
            or self is PatternType.REQUIREMENT
            or self is PatternType.PREVENTION
        )

    @property
    def is_liveness(self) -> bool:
        return self is PatternType.EXISTENCE or self is PatternType.RESPONSE

    @property
    def is_absence(self) -> bool:
        return self is PatternType.ABSENCE

    @property
    def is_existence(self) -> bool:
        return self is PatternType.EXISTENCE

    @property
    def is_requirement(self) -> bool:
        return self is PatternType.REQUIREMENT

    @property
    def is_response(self) -> bool:
        return self is PatternType.RESPONSE

    @property
    def is_prevention(self) -> bool:
        return self is PatternType.PREVENTION

    @property
    def should_have_trigger(self) -> bool:
        return (
            self is PatternType.REQUIREMENT
            or self is PatternType.RESPONSE
            or self is PatternType.PREVENTION
        )


@frozen
class HplPattern(HplAstObject):
    pattern_type: PatternType = field(validator=in_(PatternType))
    behaviour: HplEvent = field(validator=instance_of(HplEvent))
    trigger: Optional[HplEvent] = field(default=None, validator=optional(instance_of(HplEvent)))
    min_time: float = field(default=0.0, validator=ge(0.0))
    max_time: float = field(default=INF, converter=float)

    @trigger.validator
    def _check_trigger(self, attribute, event: Optional[HplEvent]):
        if self.pattern_type.should_have_trigger:
            if event is None:
                raise expected_not_none(attribute.name, self)
        else:
            if event is not None:
                raise invalid_attr(attribute.name, None, event, self)

    @max_time.validator
    def _check_max_time(self, attribute, value: float):
        if value < self.min_time:
            raise ValueError(f'{attribute.name}={value!r} < {self.min_time}')

    @property
    def is_pattern(self) -> bool:
        return True

    @classmethod
    def existence(
        cls,
        behaviour: HplEvent,
        min_time: float = 0.0,
        max_time: float = INF,
    ) -> 'HplPattern':
        return cls(
            PatternType.EXISTENCE,
            behaviour,
            trigger=None,
            min_time=min_time,
            max_time=max_time,
        )

    @classmethod
    def absence(
        cls,
        behaviour: HplEvent,
        min_time: float = 0.0,
        max_time: float = INF,
    ) -> 'HplPattern':
        return cls(
            PatternType.ABSENCE,
            behaviour,
            trigger=None,
            min_time=min_time,
            max_time=max_time,
        )

    @classmethod
    def response(
        cls, trigger: HplEvent, response: HplEvent, min_time: float = 0.0, max_time: float = INF
    ) -> 'HplPattern':
        return cls(
            PatternType.RESPONSE,
            response,
            trigger=trigger,
            min_time=min_time,
            max_time=max_time,
        )

    @classmethod
    def requirement(
        cls,
        behaviour: HplEvent,
        requirement: HplEvent,
        min_time: float = 0.0,
        max_time: float = INF,
    ) -> 'HplPattern':
        return cls(
            PatternType.REQUIREMENT,
            behaviour,
            requirement,
            min_time=min_time,
            max_time=max_time,
        )

    @classmethod
    def prevention(
        cls,
        trigger: HplEvent,
        forbidden: HplEvent,
        min_time: float = 0.0,
        max_time: float = INF,
    ) -> 'HplPattern':
        return cls(
            PatternType.PREVENTION,
            forbidden,
            trigger,
            min_time=min_time,
            max_time=max_time,
        )

    @property
    def is_safety(self) -> bool:
        return self.pattern_type.is_safety

    @property
    def is_liveness(self) -> bool:
        return self.pattern_type.is_liveness

    @property
    def is_absence(self) -> bool:
        return self.pattern_type.is_absence

    @property
    def is_existence(self) -> bool:
        return self.pattern_type.is_existence

    @property
    def is_requirement(self) -> bool:
        return self.pattern_type.is_requirement

    @property
    def is_response(self) -> bool:
        return self.pattern_type.is_response

    @property
    def is_prevention(self) -> bool:
        return self.pattern_type.is_prevention

    @property
    def has_min_time(self) -> bool:
        return self.min_time > 0.0 and self.min_time < INF

    @property
    def has_max_time(self) -> bool:
        return self.max_time >= 0.0 and self.max_time < INF

    def children(self) -> Tuple[HplEvent]:
        if self.trigger is None:
            return (self.behaviour,)
        return (self.trigger, self.behaviour)

    def __str__(self) -> str:
        t = ''
        if self.max_time < INF:
            if self.max_time < 1.0:
                t = f' within {self.max_time * 1000}ms'
            else:
                t = f' within {self.max_time}s'
        if self.pattern_type.is_existence:
            return f'some {self.behaviour}{t}'
        if self.pattern_type.is_absence:
            return f'no {self.behaviour}{t}'
        if self.pattern_type.is_response:
            return f'{self.trigger} causes {self.behaviour}{t}'
        if self.pattern_type.is_requirement:
            return f'{self.behaviour} requires {self.trigger}{t}'
        if self.pattern_type.is_prevention:
            return f'{self.trigger} forbids {self.behaviour}{t}'
        return self.pattern_type.name


###############################################################################
# Properties
###############################################################################


@frozen
class HplProperty(HplAstObject):
    scope: HplScope = field(validator=instance_of(HplScope))
    pattern: HplPattern = field(validator=instance_of(HplPattern))

    def __attrs_post_init__(self):
        self.sanity_check()

    @property
    def is_property(self) -> bool:
        return True

    @property
    def is_safety(self) -> bool:
        return self.pattern.is_safety

    @property
    def is_liveness(self) -> bool:
        return self.pattern.is_liveness

    @property
    def uid(self) -> Optional[str]:
        return self.metadata.get('id', None)

    def children(self) -> Tuple[HplScope, HplPattern]:
        return (self.scope, self.pattern)

    def is_fully_typed(self) -> bool:
        for event in self.events():
            for simple_event in event.simple_events():
                e: HplSimpleEvent = simple_event
                if not e.predicate.is_fully_typed():
                    return False
        return True

    def type_check_references(self, msg_types: Mapping[str, TypeToken]) -> None:
        for event in self.events():
            event.type_check_references(msg_types)

    def events(self) -> Iterator[HplEvent]:
        if self.scope.activator is not None:
            yield self.scope.activator
        yield self.pattern.behaviour
        if self.pattern.trigger is not None:
            yield self.pattern.trigger
        if self.scope.terminator is not None:
            yield self.scope.terminator

    def sanity_check(self) -> None:
        initial: Tuple[str] = self._check_activator()
        if self.pattern.is_absence or self.pattern.is_existence:
            self._check_behaviour(initial)
        elif self.pattern.is_requirement:
            aliases = self._check_behaviour(initial)
            self._check_trigger(aliases)
        elif self.pattern.is_response or self.pattern.is_prevention:
            aliases = self._check_trigger(initial)
            self._check_behaviour(aliases)
        else:
            raise TypeError(f'unexpected pattern type: {self.pattern!r}')
        self._check_terminator(initial)

    def _check_activator(self) -> Tuple[str]:
        p = self.scope.activator
        if p is not None:
            self._check_refs_defined(p, ())
            return p.aliases()
        return ()

    def _check_trigger(self, available: Tuple[str]) -> Tuple[str]:
        a = self.pattern.trigger
        assert a is not None
        self._check_refs_defined(a, available)
        aliases = a.aliases()
        self._check_duplicates(aliases, available)
        return aliases + available

    def _check_behaviour(self, available: Tuple[str]) -> Tuple[str]:
        b = self.pattern.behaviour
        self._check_refs_defined(b, available)
        aliases = b.aliases()
        self._check_duplicates(aliases, available)
        return aliases + available

    def _check_terminator(self, available: Tuple[str]) -> None:
        q = self.scope.terminator
        if q is not None:
            self._check_refs_defined(q, available)
            self._check_duplicates(q.aliases(), available)

    def _check_refs_defined(self, event: HplEvent, available: Tuple[str]) -> None:
        for ref in event.external_references():
            if ref not in available:
                raise HplSanityError.ref_undefined_event(ref, event)

    def _check_duplicates(self, aliases: Tuple[str], available: Tuple[str]) -> None:
        for alias in aliases:
            if alias in available:
                raise HplSanityError.already_defined(alias, self)

    def __str__(self) -> str:
        return f'{self.scope}: {self.pattern}'
