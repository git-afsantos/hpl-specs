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
    pattern = r'(\w+_OPERATOR)(?:\.\d+)?\s*:\s*"(\w+?)"'
    for groups in re.findall(pattern, token_grammar):
        var, token = groups
        token_map[var] = token
    pattern = r'(\w+_OPERATOR)(?:\.\d+)?\s*:\s*/(?:\\b)?(\w+?)(?:\\b)?/'
    for groups in re.findall(pattern, token_grammar):
        var, token = groups
        token_map[var] = token
    return '\n'.join(f"{key} = '{value}'" for key, value in token_map.items())


# def distorted_tokens(token_grammar: str) -> str:
#     def repl(m: re.Match) -> str:
#         return f'{m.group(1)}: " {m.group(2)} "'
# 
#     pattern = r'^(\w+(?:\.\d+)?)\s*:\s*"(\w+?)"$'
#     g = re.sub(pattern, repl, token_grammar, flags=re.M)
#     pattern = r'^(\w+(?:\.\d+)?)\s*:\s*/\\b(\w+?)\\b/$'
#     return re.sub(pattern, repl, g, flags=re.M)


def distorted_tokens(token_grammar: str) -> str:
    def repl(m: re.Match) -> str:
        return f'" {m.group(1)} "'

    pattern = r'(?:"|/\\b)(\w+?)(?:"|\\b/)'
    return re.sub(pattern, repl, token_grammar)


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


# TEST_GRAMMAR_PY = f'''\
# # SPDX-License-Identifier: MIT
# # Copyright © 2023 André Santos
# 
# HPL_GRAMMAR = r"""
# {g_files}
# {g_properties}
# {g_predicates}
# {distorted_tokens(g_tokens)}
# """
# '''

# path = HERE.parent / 'tests' / 'grammar.py'
# path.write_text(TEST_GRAMMAR_PY, encoding='utf8')
