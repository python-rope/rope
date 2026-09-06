"""A module to ease code analysis

This module is here to help source code analysis.
"""

import io
import re
import sys
import tokenize

from rope.base import codeanalyze, utils


@utils.cached(7)
def real_code(source):
    """Simplify `source` for analysis

    It replaces:

    * comments with spaces
    * strs with a new str filled with spaces
    * implicit and explicit continuations with spaces
    * tabs and semicolons with spaces

    The resulting code is a lot easier to analyze if we are interested
    only in offsets.
    """
    collector = codeanalyze.ChangeCollector(source)
    has_fstring = False
    for start, end, matchgroups in ignored_regions(source):
        if source[start] == "#":
            replacement = " " * (end - start)
        elif "f" in matchgroups.get("prefix", "").lower():
            replacement = None
            has_fstring = True
        else:
            replacement = '"%s"' % (" " * (end - start - 2))
        if replacement is not None:
            collector.add_change(start, end, replacement)
    source = collector.get_changed() or source
    if has_fstring:
        # f-strings are left untouched above so their expression parts keep
        # their real offsets, but that leaves any literal or format-spec
        # `()[]{}` text (e.g. the `[` in `f"[{x}"`) sitting in `source`,
        # where the `_parens` pass below would miscount it as a real
        # unmatched bracket and corrupt every following offset. Blank it.
        source = _blank_fstring_literal_brackets(source)
    collector = codeanalyze.ChangeCollector(source)
    parens = 0
    for match in _parens.finditer(source):
        i = match.start()
        c = match.group()
        if c in "({[":
            parens += 1
        if c in ")}]":
            parens -= 1
        if c == "\n" and parens > 0:
            collector.add_change(i, i + 1, " ")
    source = collector.get_changed() or source
    return source.replace("\\\n", "  ").replace("\t", " ").replace(";", "\n")


def _blank_fstring_literal_brackets(source):
    """Blank `()[]{}` chars that are f-string literal/format-spec text.

    Blanked characters become a single space each, so length and every
    character offset are preserved exactly.

    Approach: tokenize `source` and protect every character covered by an
    `OP` token. A `()[]{}` character that no `OP` token covers cannot be
    real syntax -- comments and non-f strings are already blanked, so the
    only place it can occur is inside an f-string's literal or format-spec
    text. Real expression brackets living inside an f-string (e.g. the
    `[`/`]` in `f"{[1,2][0]}"`, or `{width}` in `f"{x:{width}}"`) are `OP`
    tokens, so they stay untouched. A bracket *character* that is literal
    data inside a nested string (the `}` in `f"{d['}']}"`) is not an `OP`
    token, so it is blanked to a space -- correct, since it is data, not a
    real bracket, and must not sway the `_parens` continuation count. This
    also handles `{{`/`}}` escapes: tokenize covers the doubled brace with
    a single FSTRING_MIDDLE token, leaving the escaping second brace under
    no token span -- and, not being an `OP` either, the complement-of-OP
    rule correctly blanks it.

    Only Python 3.12+ can make this distinction (PEP 701 added
    FSTRING_START/MIDDLE/END; earlier an f-string is one opaque STRING
    token). On earlier versions this is a no-op and the pre-existing
    behaviour is unchanged.
    """
    if sys.version_info < (3, 12):
        return source
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError, ValueError):
        # `source` may be incomplete/invalid mid-edit (e.g. an unterminated
        # f-string or an unbalanced paren -- exactly what the `_parens` pass
        # handles). Fall back to the pre-existing behaviour.
        return source

    lines = codeanalyze.SourceLinesAdapter(source)

    def offset(position):
        row, col = position
        return lines.get_line_start(row) + col

    protected = set()
    for tok in tokens:
        if tok.type == tokenize.OP:
            protected.update(range(offset(tok.start), offset(tok.end)))

    collector = codeanalyze.ChangeCollector(source)
    for i, c in enumerate(source):
        if c in "()[]{}" and i not in protected:
            collector.add_change(i, i + 1, " ")
    return collector.get_changed() or source


@utils.cached(7)
def ignored_regions(source):
    """Return ignored regions like strings and comments in `source`"""
    return [
        (match.start(), match.end(), match.groupdict())
        for match in _str.finditer(source)
    ]


_str = re.compile(
    "|".join(
        [
            codeanalyze.get_comment_pattern(),
            codeanalyze.get_any_string_pattern(),
        ]
    )
)
_parens = re.compile(r"[\({\[\]}\)\n]")
