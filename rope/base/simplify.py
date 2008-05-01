"""A module to ease code analysis

This module is here to help source code analysis.
"""
import re

from rope.base import codeanalyze


def real_code(source):
    collector = codeanalyze.ChangeCollector(source)
    for start, end in ignored_regions(source):
        if source[start] == '#':
            replacement = ' ' * (end - start)
        else:
            replacement = '"%s"' % (' ' * (end - start - 2))
        collector.add_change(start, end, replacement)
    source = collector.get_changed() or source
    collector = codeanalyze.ChangeCollector(source)
    parens = 0
    for i, c in enumerate(source):
        if c in '({[':
            parens += 1
        if c in ')}]':
            parens -= 1
        if c == '\n' and parens > 0:
            collector.add_change(i, i + 1, ' ')
    source = collector.get_changed() or source
    return source.replace('\\\n', '  ').replace('\t', ' ')


def ignored_regions(source):
    return [(match.start(), match.end()) for match in _str.finditer(source)]


_str = re.compile('%s|%s' % (codeanalyze.get_comment_pattern(),
                             codeanalyze.get_string_pattern()))
