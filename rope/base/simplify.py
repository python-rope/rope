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
        if match.group().startswith('#'):
            replacement = ' ' * (end - start)
        else:
            replacement = '"%s"' % (' ' * (end - start - 2))
        collector.add_change(start, end, replacement)
    return collector.get_changed() or source

_str = re.compile('%s|%s' % (codeanalyze.get_comment_pattern(),
                             codeanalyze.get_string_pattern()))
