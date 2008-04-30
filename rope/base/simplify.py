"""A module to ease code analysis

This module is here to help source code analysis.
"""
import re

from rope.base import codeanalyze


def real_code(source):
    import rope.refactor.sourceutils
    collector = rope.refactor.sourceutils.ChangeCollector(source)
    for match in _str.finditer(source):
        start = match.start()
        end = match.end()
        replacement = '"%s"' % (' ' * (end - start - 2))
        collector.add_change(start, end, replacement)
    return collector.get_changed() or source

_str = re.compile(codeanalyze.get_string_pattern())
