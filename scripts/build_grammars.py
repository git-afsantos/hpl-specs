# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

###############################################################################
# Imports
###############################################################################

from pathlib import Path
import re

###############################################################################
# Constants
###############################################################################

HERE = Path(__file__).resolve(strict=True).parent
PKG = HERE.parent / 'src' / 'hpl'
GRAMMARS = PKG / 'grammars'

PREAMBLE = re.compile(r'\s*//\s*SPDX-License-Identifier:[^\n]+\s*//\s*Copyright[^\n]+\s*')


def skip_preamble(text: str) -> str:
    m = PREAMBLE.match(text)
    if m:
        i = m.end()
        return text[i:]
    return text


path = GRAMMARS / 'tokens.lark'
g_tokens = skip_preamble(path.read_text(encoding='utf8'))

path = GRAMMARS / 'predicates.lark'
g_predicates = skip_preamble(path.read_text(encoding='utf8'))

path = GRAMMARS / 'properties.lark'
g_properties = skip_preamble(path.read_text(encoding='utf8'))

path = GRAMMARS / 'files.lark'
g_files = skip_preamble(path.read_text(encoding='utf8'))


def get_keyword_list(token_grammar: str) -> str:
    token_map = {}
    for groups in re.findall(r'(\w+_OPERATOR)(?:\.\d+)?\s*:\s*"(\w+?)"', token_grammar):
        var, token = groups
        token_map[var] = token
    return '\n'.join(f"{key} = '{value}'" for key, value in token_map.items())


GRAMMAR_PY = f'''\
# SPDX-License-Identifier: MIT
# Copyright © 2021 André Santos

PREDICATE_GRAMMAR = r"""
{g_predicates}
{g_tokens}
"""

HPL_GRAMMAR = r"""
{g_files}
{g_properties}
{g_predicates}
{g_tokens}
"""

{get_keyword_list(g_tokens)}
'''

path = PKG / 'grammar.py'
path.write_text(GRAMMAR_PY, encoding='utf8')
