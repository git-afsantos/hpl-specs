"""
HPL 2.0 Transformer (Updated)
Converts Lark parse tree to immutable typed AST nodes
"""

from lark import Transformer, Token
from typing import Any, List, Union
from hpl_ast_nodes import *


class HPLTransformer(Transformer):
    """Transform Lark parse tree into HPL AST"""
    
    # ==============================================
    # Top Level
    # ==============================================
    
    def start(self, items):
        """Build specification from top-level statements"""
        imports = []
        declarations = []
        groups = []
        statemachines = []
        properties = []
        
        for item in items:
            if isinstance(item, Import):
                imports.append(item)
            elif isinstance(item, (EventDecl, ComputedDecl, ConditionDecl)):
                declarations.append(item)
            elif isinstance(item, Group):
                groups.append(item)
            elif isinstance(item, StateMachine):
                statemachines.append(item)
            elif isinstance(item, Property):
                properties.append(item)
        
        return Specification(
            imports=tuple(imports),
            declarations=tuple(declarations),
            groups=tuple(groups),
            statemachines=tuple(statemachines),
            properties=tuple(properties)
        )
    
    # ==============================================
    # Imports
    # ==============================================
    
    def import_stmt(self, items):
        module, library = items
        return Import(module=str(module), library=self._extract_string(library))
    
    # ==============================================
    # Types
    # ==============================================
    
    def scalar_type(self, items):
        type_str = str(items[0]).lower()
        type_name = ScalarTypeName[type_str.upper()]
        return ScalarType(name=type_name)
    
    def array_type(self, items):
        element_type = items[0]
        return ArrayType(element_type=element_type)
    
    def qualified_type(self, items):
        components = tuple(str(item) for item in items)
        return QualifiedType(components=components)
    
    # ==============================================
    # Declarations
    # ==============================================
    
    def event_decl(self, items):
        source = items[0]
        alias = None
        predicate = None
        type_annotation = None
        
        i = 1
        if i < len(items) and isinstance(items[i], Expression):
            predicate = items[i]
            i += 1
        
        # Skip 'as' keyword, get alias
        if i < len(items):
            alias = str(items[i])
            i += 1
        
        if i < len(items) and isinstance(items[i], QualifiedType):
            type_annotation = items[i]
        
        return EventDecl(
            source=source,
            alias=alias,
            predicate=predicate,
            type_annotation=type_annotation
        )
    
    def event_source(self, items):
        token = items[0]
        if isinstance(token, Token):
            if token.type == 'TOPIC':
                return EventRef(name=str(token), is_topic=True)
            else:
                return EventRef(name=str(token), is_topic=False)
        return token
    
    def computed_decl(self, items):
        type_node = items[0]
        name = str(items[1])
        expression = items[2]
        reset_event = items[3] if len(items) > 3 else None
        
        return ComputedDecl(
            type=type_node,
            name=name,
            expression=expression,
            reset_event=reset_event
        )
    
    def computed_expr(self, items):
        return items[0]
    
    def condition_decl(self, items):
        name, pattern = items
        return ConditionDecl(name=str(name), pattern=pattern)
    
    def reset_clause(self, items):
        return items[0]  # event_ref
    
    # ==============================================
    # Event References
    # ==============================================
    
    def event_ref(self, items):
        token = items[0]
        if isinstance(token, Token):
            if token.type == 'AT':
                # @identifier
                return EventRef(name=str(items[1]), is_topic=False)
            elif token.type == 'TOPIC':
                return EventRef(name=str(token), is_topic=True)
        elif isinstance(token, str):
            if token.startswith('@'):
                return EventRef(name=token[1:], is_topic=False)
            elif token.startswith('/'):
                return EventRef(name=token, is_topic=True)
        return token
    
    # ==============================================
    # Aggregation Functions
    # ==============================================
    
    def aggregation_call(self, items):
        # The grammar should call specific methods based on function name
        # This is handled by the grammar structure
        return items[0]
    
    # Map token names to function creation
    def _make_count_call(self, items):
        return CountCall(event=items[0])
    
    def _make_sum_call(self, items):
        return SumCall(expression=items[0])
    
    def _make_max_call(self, items):
        return MaxCall(expression=items[0])
    
    def _make_min_call(self, items):
        return MinCall(expression=items[0])
    
    def _make_avg_call(self, items):
        return AvgCall(expression=items[0])
    
    def _make_age_call(self, items):
        return AgeCall(event=items[0])
    
    def _make_timestamp_call(self, items):
        return TimestampCall(event=items[0])
    
    def _make_buffer_call(self, items):
        return BufferCall(expression=items[0], size=items[1])
    
    def _make_last_call(self, items):
        return LastCall(expression=items[0])
    
    # ==============================================
    # Groups
    # ==============================================
    
    def group(self, items):
        name = str(items[0])
        declarations = []
        properties = []
        
        for item in items[1:]:
            if isinstance(item, (EventDecl, ComputedDecl, ConditionDecl)):
                declarations.append(item)
            elif isinstance(item, Property):
                properties.append(item)
        
        return Group(
            name=name,
            declarations=tuple(declarations),
            properties=tuple(properties)
        )
    
    # ==============================================
    # Properties
    # ==============================================
    
    def property(self, items):
        name = str(items[0])
        
        # Optional property block with declarations/metadata
        declarations = []
        metadata = []
        scope = None
        body = None
        
        i = 1
        if i < len(items) and isinstance(items[i], dict):
            # Property block present
            block = items[i]
            declarations = block.get('declarations', [])
            metadata = block.get('metadata', [])
            i += 1
        
        scope = items[i]
        body = items[i + 1]
        
        return Property(
            name=name,
            scope=scope,
            body=body,
            declarations=tuple(declarations),
            metadata=tuple(metadata)
        )
    
    def property_block(self, items):
        declarations = []
        metadata = []
        
        for item in items:
            if isinstance(item, (EventDecl, ComputedDecl, ConditionDecl)):
                declarations.append(item)
            elif isinstance(item, tuple) and len(item) == 2:
                # Metadata (key, value)
                metadata.append(item)
        
        return {'declarations': declarations, 'metadata': metadata}
    
    def metadata(self, items):
        key = str(items[0])
        value = self._extract_string(items[1])
        return (key, value)
    
    # ==============================================
    # Scopes
    # ==============================================
    
    def scope(self, items):
        if len(items) == 1:
            return items[0]
        else:
            # Nested scope: outer : inner
            return NestedScope(outer=items[0], inner=items[1])
    
    def always_scope(self, items):
        return AlwaysScope()
    
    def after_scope(self, items):
        return AfterScope(event=items[0])
    
    def until_scope(self, items):
        return UntilScope(event=items[0])
    
    def after_until_scope(self, items):
        return AfterUntilScope(start_event=items[0], end_event=items[1])
    
    def when_scope(self, items):
        state_condition = items[0]
        return state_condition
    
    def state_condition(self, items):
        statemachine = str(items[0])
        states = items[1]  # List of state names
        return WhenScope(statemachine=statemachine, states=tuple(states))
    
    def state_list(self, items):
        return tuple(self._extract_string(item) for item in items)
    
    def scope_body(self, items):
        return items[0]
    
    # ==============================================
    # Patterns
    # ==============================================
    
    def existence_pattern(self, items):
        event = items[0]
        within = items[1] if len(items) > 1 else None
        return ExistencePattern(event=event, within=within)
    
    def absence_pattern(self, items):
        event = items[0]
        within = items[1] if len(items) > 1 else None
        return AbsencePattern(event=event, within=within)
    
    def response_pattern(self, items):
        each = False
        i = 0
        
        if items[i] is True:  # EACH token transformed
            each = True
            i += 1
        
        trigger = items[i]
        response = items[i + 1]
        within = None
        unless_clause = None
        
        i += 2
        if i < len(items):
            if isinstance(items[i], TimeExpression):
                within = items[i]
                i += 1
            if i < len(items) and isinstance(items[i], UnlessClause):
                unless_clause = items[i]
        
        return ResponsePattern(
            trigger=trigger,
            response=response,
            each=each,
            within=within,
            unless_clause=unless_clause
        )
    
    def prevention_pattern(self, items):
        trigger = items[0]
        forbidden = items[1]
        within = None
        unless_clause = None
        
        i = 2
        if i < len(items):
            if isinstance(items[i], TimeExpression):
                within = items[i]
                i += 1
            if i < len(items) and isinstance(items[i], UnlessClause):
                unless_clause = items[i]
        
        return PreventionPattern(
            trigger=trigger,
            forbidden=forbidden,
            within=within,
            unless_clause=unless_clause
        )
    
    def requirement_pattern(self, items):
        consequent = items[0]
        antecedent = items[1]
        within = None
        unless_clause = None
        
        i = 2
        if i < len(items):
            if isinstance(items[i], TimeExpression):
                within = items[i]
                i += 1
            if i < len(items) and isinstance(items[i], UnlessClause):
                unless_clause = items[i]
        
        return RequirementPattern(
            consequent=consequent,
            antecedent=antecedent,
            within=within,
            unless_clause=unless_clause
        )
    
    def event_spec(self, items):
        event = items[0]
        alias = None
        predicate = None
        
        i = 1
        if i < len(items):
            if isinstance(items[i], str):
                # Alias
                alias = items[i]
                i += 1
            if i < len(items) and isinstance(items[i], Expression):
                predicate = items[i]
        
        return EventSpec(event=event, alias=alias, predicate=predicate)
    
    def within_clause(self, items):
        return items[0]
    
    def unless_clause(self, items):
        event = items[0]
        within = items[1] if len(items) > 1 else None
        return UnlessClause(event=event, within=within)
    
    def EACH(self, token):
        return True
    
    # ==============================================
    # State Machines
    # ==============================================
    
    def statemachine(self, items):
        name = str(items[0])
        initial_state = items[1]
        states = items[2:]
        return StateMachine(
            name=name,
            initial_state=initial_state,
            states=tuple(states)
        )
    
    def initial_state(self, items):
        return str(items[0])
    
    def state_def(self, items):
        name = str(items[0])
        transitions = items[1:]
        return State(name=name, transitions=tuple(transitions))
    
    def event_transition(self, items):
        event = items[0]
        predicate = None
        guard = None
        target = str(items[-1])  # Last item is always target
        
        i = 1
        if i < len(items) - 1:
            if isinstance(items[i], Expression):
                predicate = items[i]
                i += 1
            if i < len(items) - 1 and isinstance(items[i], Expression):
                guard = items[i]
        
        return EventTransition(
            event=event,
            predicate=predicate,
            guard=guard,
            target=target
        )
    
    def timeout_transition(self, items):
        timeout = items[0]
        target = str(items[1])
        return TimeoutTransition(timeout=timeout, target=target)
    
    def guard(self, items):
        return items[0]
    
    # ==============================================
    # Expressions
    # ==============================================
    
    def expression(self, items):
        return items[0]
    
    def or_expr(self, items):
        return self._build_binary_op(BinaryOperator.OR, items)
    
    def and_expr(self, items):
        return self._build_binary_op(BinaryOperator.AND, items)
    
    def not_expr(self, items):
        if len(items) == 1:
            return items[0]
        return UnaryOp(operator=UnaryOperator.NOT, operand=items[1])
    
    def implies_expr(self, items):
        if len(items) == 1:
            return items[0]
        return BinaryOp(operator=BinaryOperator.IMPLIES, left=items[0], right=items[1])
    
    def comparison_expr(self, items):
        if len(items) == 1:
            return items[0]
        
        # Handle chained comparisons: a < b < c
        result = items[0]
        for i in range(1, len(items), 2):
            op_str = str(items[i])
            op = self._string_to_binary_op(op_str)
            right = items[i + 1]
            result = BinaryOp(operator=op, left=result, right=right)
        return result
    
    def additive_expr(self, items):
        return self._build_binary_op_list(items)
    
    def multiplicative_expr(self, items):
        return self._build_binary_op_list(items)
    
    def unary_expr(self, items):
        if len(items) == 1:
            return items[0]
        return UnaryOp(operator=UnaryOperator.NEGATE, operand=items[1])
    
    def postfix_expr(self, items):
        result = items[0]
        for item in items[1:]:
            if isinstance(item, str):
                # Field access
                result = FieldAccess(object=result, field=item)
            elif isinstance(item, tuple):
                op_type, data = item
                if op_type == 'array':
                    result = ArrayAccess(array=result, index=data)
                elif op_type == 'call':
                    result = Call(function=result, arguments=tuple(data))
        return result
    
    def field_access(self, items):
        return str(items[0])
    
    def array_access(self, items):
        return ('array', items[0])
    
    def call(self, items):
        args = items[0] if items else []
        return ('call', args)
    
    def arguments(self, items):
        return list(items)
    
    def primary_expr(self, items):
        return items[0]
    
    def literal(self, items):
        return items[0]
    
    def reference(self, items):
        token = items[0]
        
        if isinstance(token, Token):
            if token.type == 'AT':
                # @identifier with potential field access
                name = str(items[1])
                result = AtIdentifier(name=name)
                
                # Handle field access chain: @event.field1.field2
                for i in range(2, len(items)):
                    field = str(items[i])
                    result = FieldAccess(object=result, field=field)
                
                return result
            elif token.type == 'TOPIC':
                return EventRef(name=str(token), is_topic=True)
            elif token.type == 'IDENTIFIER':
                return Identifier(name=str(token))
        
        return token
    
    def quantifier(self, items):
        quantifier_str = str(items[0]).lower()
        quantifier_enum = Quantifier[quantifier_str.upper()]
        variable = str(items[1])
        collection = items[2]
        predicate = items[3]
        
        return QuantifierExpr(
            quantifier=quantifier_enum,
            variable=variable,
            collection=collection,
            predicate=predicate
        )
    
    def lambda_expr(self, items):
        parameter = str(items[0])
        body = items[1]
        return LambdaExpr(parameter=parameter, body=body)
    
    def predicate(self, items):
        return items[0]
    
    # ==============================================
    # Time Expressions
    # ==============================================
    
    def time_expr(self, items):
        value = float(items[0])
        unit_str = str(items[1])
        unit = TimeUnit(unit_str)  # Create enum from string value
        return TimeExpression(value=value, unit=unit)
    
    # ==============================================
    # Literals
    # ==============================================
    
    def NUMBER(self, token):
        value = str(token)
        if '.' in value or 'e' in value.lower():
            return Literal(value=float(value))
        return Literal(value=int(value))
    
    def STRING_LITERAL(self, token):
        return Literal(value=self._extract_string(token))
    
    def TRUE(self, token):
        return Literal(value=True)
    
    def FALSE(self, token):
        return Literal(value=False)
    
    def IDENTIFIER(self, token):
        return str(token)
    
    def TOPIC(self, token):
        return str(token)
    
    # ==============================================
    # Helper Methods
    # ==============================================
    
    def _string_to_binary_op(self, op_str: str) -> BinaryOperator:
        """Convert operator string to enum"""
        op_map = {
            '+': BinaryOperator.ADD,
            '-': BinaryOperator.SUBTRACT,
            '*': BinaryOperator.MULTIPLY,
            '/': BinaryOperator.DIVIDE,
            '%': BinaryOperator.MODULO,
            '=': BinaryOperator.EQUAL,
            '!=': BinaryOperator.NOT_EQUAL,
            '<': BinaryOperator.LESS_THAN,
            '<=': BinaryOperator.LESS_EQUAL,
            '>': BinaryOperator.GREATER_THAN,
            '>=': BinaryOperator.GREATER_EQUAL,
            'and': BinaryOperator.AND,
            'or': BinaryOperator.OR,
            'implies': BinaryOperator.IMPLIES,
        }
        return op_map[op_str]
    
    def _build_binary_op(self, operator: BinaryOperator, items):
        """Build binary operation from list of items"""
        if len(items) == 1:
            return items[0]
        
        result = items[0]
        for i in range(1, len(items)):
            result = BinaryOp(operator=operator, left=result, right=items[i])
        return result
    
    def _build_binary_op_list(self, items):
        """Build binary operation from alternating expr, op, expr list"""
        if len(items) == 1:
            return items[0]
        
        result = items[0]
        for i in range(1, len(items), 2):
            op_str = str(items[i])
            op = self._string_to_binary_op(op_str)
            right = items[i + 1]
            result = BinaryOp(operator=op, left=result, right=right)
        return result
    
    def _extract_string(self, token):
        """Extract string content from quoted literal"""
        s = str(token)
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            return s[1:-1]
        return s
