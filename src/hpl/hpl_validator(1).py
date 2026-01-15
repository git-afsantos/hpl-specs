"""
HPL 2.0 Semantic Validator
Performs semantic analysis on AST nodes without full type information
"""

from typing import Set, Dict, List, Optional
from collections import defaultdict

from hpl_ast_nodes import *


class ValidationError(Exception):
    """Semantic validation error"""
    
    def __init__(self, message: str, node: Optional[ASTNode] = None):
        self.message = message
        self.node = node
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        if self.node and self.node.line:
            return f"Line {self.node.line}: {self.message}"
        return self.message


class HPLValidator:
    """Semantic validator for HPL specifications"""
    
    def __init__(self):
        self.errors: List[ValidationError] = []
        self.warnings: List[str] = []
        
        # Symbol tables
        self.events: Dict[str, EventDecl] = {}
        self.computed: Dict[str, ComputedDecl] = {}
        self.conditions: Dict[str, ConditionDecl] = {}
        self.statemachines: Dict[str, StateMachine] = {}
        self.imports: Dict[str, Import] = {}
        
        # Scope tracking
        self.current_scope: List[str] = []
    
    def validate(self, spec: Specification) -> bool:
        """
        Validate specification and collect errors.
        
        Returns:
            True if valid, False otherwise
        """
        self.errors.clear()
        self.warnings.clear()
        
        try:
            self._build_symbol_tables(spec)
            self._check_references(spec)
            self._check_state_machines(spec)
            self._check_properties(spec)
            self._check_groups(spec)
            
        except ValidationError as e:
            self.errors.append(e)
        
        return len(self.errors) == 0
    
    def _build_symbol_tables(self, spec: Specification):
        """Build symbol tables from top-level declarations"""
        
        # Imports
        for imp in spec.imports:
            if imp.module in self.imports:
                self._error(f"Duplicate import: {imp.module}", imp)
            self.imports[imp.module] = imp
        
        # Global declarations
        for decl in spec.declarations:
            self._register_declaration(decl)
        
        # State machines
        for sm in spec.statemachines:
            if sm.name in self.statemachines:
                self._error(f"Duplicate state machine: {sm.name}", sm)
            self.statemachines[sm.name] = sm
    
    def _register_declaration(self, decl: Union[EventDecl, ComputedDecl, ConditionDecl]):
        """Register a declaration in symbol tables"""
        if isinstance(decl, EventDecl):
            if decl.alias in self.events:
                self._error(f"Duplicate event alias: {decl.alias}", decl)
            self.events[decl.alias] = decl
            
        elif isinstance(decl, ComputedDecl):
            if decl.name in self.computed:
                self._error(f"Duplicate computed value: {decl.name}", decl)
            self.computed[decl.name] = decl
            
        elif isinstance(decl, ConditionDecl):
            if decl.name in self.conditions:
                self._error(f"Duplicate condition: {decl.name}", decl)
            self.conditions[decl.name] = decl
    
    def _check_references(self, spec: Specification):
        """Check that all references are valid"""
        
        # Check computed value expressions
        for decl in spec.declarations:
            if isinstance(decl, ComputedDecl):
                self._check_expression(decl.expression)
                if decl.reset_event:
                    self._check_event_ref(decl.reset_event)
        
        # Check condition patterns
        for decl in spec.declarations:
            if isinstance(decl, ConditionDecl):
                self._check_pattern(decl.pattern)
    
    def _check_event_ref(self, ref: EventRef):
        """Check that event reference is valid"""
        if not ref.is_topic:
            # Declared event reference
            if ref.name not in self.events:
                self._error(f"Undefined event: @{ref.name}", ref)
        # Topic references always valid (inline events)
    
    def _check_expression(self, expr: Expression):
        """Recursively check expression for undefined references"""
        if isinstance(expr, AtIdentifier):
            # Could be event or computed value
            if expr.name not in self.events and expr.name not in self.computed:
                self._error(f"Undefined reference: @{expr.name}", expr)
        
        elif isinstance(expr, Identifier):
            # Check if it's a condition being used incorrectly
            if expr.name in self.conditions:
                self._warn(f"Condition '{expr.name}' used as value (should use @{expr.name})")
        
        elif isinstance(expr, FieldAccess):
            self._check_expression(expr.object)
        
        elif isinstance(expr, ArrayAccess):
            self._check_expression(expr.array)
            self._check_expression(expr.index)
        
        elif isinstance(expr, Call):
            self._check_expression(expr.function)
            for arg in expr.arguments:
                self._check_expression(arg)
        
        elif isinstance(expr, UnaryOp):
            self._check_expression(expr.operand)
        
        elif isinstance(expr, BinaryOp):
            self._check_expression(expr.left)
            self._check_expression(expr.right)
        
        elif isinstance(expr, Quantifier):
            self._check_expression(expr.collection)
            self._check_expression(expr.predicate)
        
        elif isinstance(expr, LambdaExpr):
            self._check_expression(expr.body)
        
        # Aggregation calls
        elif isinstance(expr, (CountCall, AgeCall, TimestampCall)):
            self._check_event_ref(expr.event)
        
        elif isinstance(expr, (SumCall, MaxCall, MinCall, AvgCall, LastCall)):
            self._check_expression(expr.expression)
        
        elif isinstance(expr, BufferCall):
            self._check_expression(expr.expression)
            self._check_expression(expr.size)
    
    def _check_pattern(self, pattern: Pattern):
        """Check pattern for semantic errors"""
        if isinstance(pattern, (ExistencePattern, AbsencePattern)):
            self._check_event_spec(pattern.event)
        
        elif isinstance(pattern, (ResponsePattern, PreventionPattern, RequirementPattern)):
            if isinstance(pattern, ResponsePattern):
                self._check_event_spec(pattern.trigger)
                self._check_event_spec(pattern.response)
            elif isinstance(pattern, PreventionPattern):
                self._check_event_spec(pattern.trigger)
                self._check_event_spec(pattern.forbidden)
            else:  # RequirementPattern
                self._check_event_spec(pattern.consequent)
                self._check_event_spec(pattern.antecedent)
            
            if pattern.unless_clause:
                self._check_event_spec(pattern.unless_clause.event)
    
    def _check_event_spec(self, spec: EventSpec):
        """Check event specification"""
        self._check_event_ref(spec.event)
        if spec.predicate:
            self._check_expression(spec.predicate)
    
    def _check_state_machines(self, spec: Specification):
        """Validate state machines"""
        for sm in spec.statemachines:
            states = {s.name for s in sm.states}
            
            # Check initial state exists
            if sm.initial_state not in states:
                self._error(
                    f"Initial state '{sm.initial_state}' not defined in state machine '{sm.name}'",
                    sm
                )
            
            # Check transition targets
            for state in sm.states:
                for transition in state.transitions:
                    if transition.target not in states:
                        self._error(
                            f"Transition target '{transition.target}' not defined in state machine '{sm.name}'",
                            transition
                        )
                    
                    if isinstance(transition, EventTransition):
                        self._check_event_ref(transition.event)
                        if transition.predicate:
                            self._check_expression(transition.predicate)
                        if transition.guard:
                            self._check_guard(transition.guard)
            
            # Check for unreachable states
            reachable = self._find_reachable_states(sm)
            unreachable = states - reachable
            if unreachable:
                self._warn(f"Unreachable states in '{sm.name}': {', '.join(sorted(unreachable))}")
    
    def _check_guard(self, guard: Expression):
        """Check guard expression - special rules"""
        # Guards can reference:
        # - Computed values: @computed.value
        # - Conditions: @condition (but these are patterns, not events!)
        
        if isinstance(guard, AtIdentifier):
            if guard.name in self.conditions:
                self._error(
                    f"Condition @{guard.name} cannot be used in guard (conditions are patterns, not events)",
                    guard
                )
        
        self._check_expression(guard)
    
    def _find_reachable_states(self, sm: StateMachine) -> Set[str]:
        """Find all reachable states using BFS"""
        reachable = {sm.initial_state}
        queue = [sm.initial_state]
        state_map = {s.name: s for s in sm.states}
        
        while queue:
            current = queue.pop(0)
            if current not in state_map:
                continue
            
            state = state_map[current]
            for transition in state.transitions:
                if transition.target not in reachable:
                    reachable.add(transition.target)
                    queue.append(transition.target)
        
        return reachable
    
    def _check_properties(self, spec: Specification):
        """Check standalone properties"""
        for prop in spec.properties:
            # Check local declarations
            local_events = {}
            local_computed = {}
            local_conditions = {}
            
            for decl in prop.declarations:
                if isinstance(decl, EventDecl):
                    if decl.alias in self.events or decl.alias in local_events:
                        self._error(f"Duplicate event alias in property: {decl.alias}", decl)
                    local_events[decl.alias] = decl
                elif isinstance(decl, ComputedDecl):
                    if decl.name in self.computed or decl.name in local_computed:
                        self._error(f"Duplicate computed value in property: {decl.name}", decl)
                    local_computed[decl.name] = decl
                elif isinstance(decl, ConditionDecl):
                    if decl.name in self.conditions or decl.name in local_conditions:
                        self._error(f"Duplicate condition in property: {decl.name}", decl)
                    local_conditions[decl.name] = decl
            
            # Check scope and body with local context
            self._push_scope(local_events, local_computed, local_conditions)
            self._check_scope(prop.scope)
            
            if isinstance(prop.body, Pattern):
                self._check_pattern(prop.body)
            else:
                self._check_expression(prop.body)
            
            self._pop_scope()
    
    def _check_groups(self, spec: Specification):
        """Check groups"""
        for group in spec.groups:
            # Similar to properties but with group-level sharing
            local_events = {}
            local_computed = {}
            local_conditions = {}
            
            for decl in group.declarations:
                if isinstance(decl, EventDecl):
                    if decl.alias in self.events or decl.alias in local_events:
                        self._error(f"Duplicate event alias in group: {decl.alias}", decl)
                    local_events[decl.alias] = decl
                elif isinstance(decl, ComputedDecl):
                    if decl.name in self.computed or decl.name in local_computed:
                        self._error(f"Duplicate computed value in group: {decl.name}", decl)
                    local_computed[decl.name] = decl
                elif isinstance(decl, ConditionDecl):
                    if decl.name in self.conditions or decl.name in local_conditions:
                        self._error(f"Duplicate condition in group: {decl.name}", decl)
                    local_conditions[decl.name] = decl
            
            # Check each property in group context
            self._push_scope(local_events, local_computed, local_conditions)
            
            for prop in group.properties:
                # Property can have additional local declarations
                prop_events = local_events.copy()
                prop_computed = local_computed.copy()
                prop_conditions = local_conditions.copy()
                
                for decl in prop.declarations:
                    if isinstance(decl, EventDecl):
                        if decl.alias in prop_events:
                            self._error(f"Duplicate event alias: {decl.alias}", decl)
                        prop_events[decl.alias] = decl
                    elif isinstance(decl, ComputedDecl):
                        if decl.name in prop_computed:
                            self._error(f"Duplicate computed value: {decl.name}", decl)
                        prop_computed[decl.name] = decl
                    elif isinstance(decl, ConditionDecl):
                        if decl.name in prop_conditions:
                            self._error(f"Duplicate condition: {decl.name}", decl)
                        prop_conditions[decl.name] = decl
                
                self._check_scope(prop.scope)
                
                if isinstance(prop.body, Pattern):
                    self._check_pattern(prop.body)
                else:
                    self._check_expression(prop.body)
            
            self._pop_scope()
    
    def _check_scope(self, scope: Scope):
        """Check scope for semantic errors"""
        if isinstance(scope, (AfterScope, UntilScope)):
            self._check_event_spec(scope.event)
        elif isinstance(scope, AfterUntilScope):
            self._check_event_spec(scope.start_event)
            self._check_event_spec(scope.end_event)
        elif isinstance(scope, WhenScope):
            if scope.statemachine not in self.statemachines:
                self._error(f"Undefined state machine: {scope.statemachine}", scope)
            else:
                sm = self.statemachines[scope.statemachine]
                state_names = {s.name for s in sm.states}
                for state in scope.states:
                    if state not in state_names:
                        self._error(
                            f"State '{state}' not defined in state machine '{scope.statemachine}'",
                            scope
                        )
        elif isinstance(scope, NestedScope):
            self._check_scope(scope.outer)
            self._check_scope(scope.inner)
    
    def _push_scope(self, events: dict, computed: dict, conditions: dict):
        """Push local scope context"""
        # Store original tables
        self._scope_stack = getattr(self, '_scope_stack', [])
        self._scope_stack.append((
            self.events.copy(),
            self.computed.copy(),
            self.conditions.copy()
        ))
        
        # Merge with local
        self.events.update(events)
        self.computed.update(computed)
        self.conditions.update(conditions)
    
    def _pop_scope(self):
        """Pop local scope context"""
        if hasattr(self, '_scope_stack') and self._scope_stack:
            self.events, self.computed, self.conditions = self._scope_stack.pop()
    
    def _error(self, message: str, node: Optional[ASTNode] = None):
        """Record validation error"""
        self.errors.append(ValidationError(message, node))
    
    def _warn(self, message: str):
        """Record warning"""
        self.warnings.append(message)
    
    def report(self) -> str:
        """Generate validation report"""
        lines = []
        
        if self.errors:
            lines.append(f"✗ {len(self.errors)} error(s):")
            for error in self.errors:
                lines.append(f"  - {error}")
        else:
            lines.append("✓ No errors")
        
        if self.warnings:
            lines.append(f"\n⚠ {len(self.warnings)} warning(s):")
            for warning in self.warnings:
                lines.append(f"  - {warning}")
        
        return "\n".join(lines)


# Convenience function
def validate_hpl(spec: Specification) -> HPLValidator:
    """
    Validate HPL specification.
    
    Returns:
        Validator with errors and warnings
    """
    validator = HPLValidator()
    validator.validate(spec)
    return validator
