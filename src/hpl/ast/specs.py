# SPDX-License-Identifier: MIT
# Copyright © 2023 André Santos

###############################################################################
# Imports
###############################################################################

from attrs import field, frozen
from attrs.validators import instance_of

from hpl.ast.base import HplAstObject
from hpl.ast.properties import HplProperty

###############################################################################
# Specifications
###############################################################################


@frozen
class HplSpecification(HplAstObject):
    properties: tuple[HplProperty] = field(validator=instance_of(tuple))

    @property
    def is_specification(self) -> bool:
        return True

    def children(self) -> tuple[HplProperty]:
        return self.properties

    def sanity_check(self):
        for prop in self.properties:
            prop.sanity_check()

    def __str__(self) -> str:
        return '\n'.join(str(prop) for prop in self.properties)
