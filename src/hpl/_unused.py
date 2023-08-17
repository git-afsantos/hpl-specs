# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos


def reshape(expr: HplExpression, f: Callable[[HplExpression], HplExpression]) -> HplExpression:
    diff = {}
    for attribute in fields(type(expr)):
        cls = attribute.type
        name: str = attribute.name
        is_expr = isinstance(cls, type) and issubclass(cls, HplExpression)
        is_expr = is_expr or (isinstance(cls, str) and cls in ('HplExpression', 'HplValue'))
        if is_expr:
            expr: HplExpression = getattr(expr, name)
            new: HplExpression = f(expr)
            if new is not expr:
                diff[name] = new
    if not diff:
        return expr
    return evolve(expr, **diff)


def replace(
    expr: HplExpression,
    test: Callable[['HplExpression'], bool],
    other: HplExpression,
) -> HplExpression:
    if test(expr):
        return other
    diff = {}
    for attribute in fields(type(expr)):
        cls = attribute.type
        name: str = attribute.name
        is_valid_type = isinstance(cls, type) and issubclass(cls, HplExpression)
        is_valid_type = is_valid_type or cls in ('HplExpression', 'HplValue')
        if is_valid_type:
            current: HplExpression = getattr(expr, name)
            new: HplExpression = replace(current, test, other)
            if new is not current:
                diff[name] = new
    if not diff:
        return expr
    return evolve(expr, **diff)
