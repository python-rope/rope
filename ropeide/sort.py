from rope.base import change


class SortScopes(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.resource = resource
        self.pymodule = self.pycore.resource_to_pyobject(resource)
        self.scope = self.pymodule.get_scope().\
                     get_inner_scope_for_offset(offset)
        if self.scope.parent is not None and not self.scope.get_scopes():
            self.scope = self.scope.parent

    def get_changes(self, sorter=None):
        if sorter is None:
            sorter = AlphaSorter()
        changes = change.ChangeSet('Sorting scopes (%s) in <%s>' %
                                   (sorter, self._get_scope_name()))
        scopes = self._get_scopes()
        stmts = self._get_statements(scopes)
        if not scopes:
            return changes
        blanks = scopes[0].blanks
        scopes[-1].blanks = blanks
        start = scopes[0].start
        end = scopes[-1].end

        scopes.sort(cmp=sorter)
        pieces = self._mix_scopes_and_stmts(scopes, stmts)

        pieces[-1].blanks = 0
        result = []
        result.append(self._get_text(1, start - 1))
        for piece in pieces:
            extracted = self._get_text(piece.start, piece.end)
            result.append(extracted + '\n' * piece.blanks)
        result.append(self._get_text(end + 1))
        source = ''.join(result)
        if source != self.resource.read():
            changes.add_change(change.ChangeContents(self.resource, source))
        return changes

    def _get_scope_name(self):
        if self.scope.get_kind() == 'Module':
            return self.scope.pyobject.resource.path + ' file'
        return self.scope.pyobject.get_name() + ' scope'

    def _mix_scopes_and_stmts(self, scopes, stmts):
        result = []
        for scope in reversed(scopes):
            while stmts and scope.start < stmts[-1].start:
                result.append(stmts.pop())
            result.append(scope)
        for stmt in stmts:
            result.append(stmt)
        result.reverse()
        return result

    def _get_scopes(self):
        subs = self.scope.get_scopes()
        if not subs:
            return []
        result = []
        for scope in subs:
            start = scope.get_start()
            end = scope.get_end()
            blanks = self._count_blanks(end + 1)
            result.append(_Scope(scope, start, end, blanks))
        result[-1].blanks = 0
        return result

    def _get_statements(self, scopes):
        if not scopes:
            return []
        start = scopes[0].end + 1 + scopes[0].blanks
        result = []
        for scope in scopes[1:]:
            end = scope.start - 1
            if self._get_text(start, end).strip() != '':
                blanks = self._count_blanks_reversed(end)
                result.append(_Statements(start, end - blanks, blanks))
            start = scope.end + 1 + scope.blanks
        return result

    def _count_blanks(self, start):
        lines = self.pymodule.lines
        blanks = 0
        for lineno in range(start, lines.length() + 1):
            line = lines.get_line(lineno)
            if not line.strip():
                blanks += 1
            else:
                break
        return blanks

    def _count_blanks_reversed(self, start):
        lines = self.pymodule.lines
        blanks = 0
        for lineno in range(start, 0, -1):
            line = lines.get_line(lineno)
            if not line.strip():
                blanks += 1
            else:
                break
        return blanks

    def _get_text(self, start_line, end_line=None):
        lines = self.pymodule.lines
        source = self.pymodule.source_code
        if end_line is None:
            end_line = lines.length()
        if start_line > end_line:
            return ''
        start = lines.get_line_start(start_line)
        end = min(lines.get_line_end(end_line) + 1, len(source))
        return source[start:end]


def get_sorter(kind, reverse=False):
    """Return a sorter that can be passed to `SortScopes.get_changes()`

    Kind can be:

    * 'alpha': for sorting alphabetically
    * 'kind': classes first
    * 'underlined': underlined first
    * 'special': special methods first
    * 'pydocs': with-pydocs first

    """
    try:
        return eval(kind.title() + 'Sorter')(reverse=reverse)
    except NameError:
        raise RuntimeError('No such sort kind')


class _Scope(object):

    def __init__(self, scope, start, end, blanks):
        self.start = start
        self.end = end
        self.blanks = blanks
        self.name = scope.pyobject.get_name()
        self.kind = scope.get_kind()
        self.has_pydoc = scope.pyobject.get_doc() is not None


class _Statements(object):

    def __init__(self, start, end, blanks):
        self.start = start
        self.end = end
        self.blanks = blanks


class _Sorter(object):

    def __init__(self, reverse=False):
        self.coef = 1
        if reverse:
            self.coef = -1

    def __str__(self):
        reverse = ''
        if self.coef == -1:
            reverse = 'reversed '
        return '%sbased on %s' % (reverse, self.kind)

    kind = ''


class AlphaSorter(_Sorter):

    def __call__(self, scope1, scope2):
        return self.coef * cmp(scope1.name.lower() + scope1.name,
                               scope2.name.lower() + scope1.name)

    kind = 'name'


class KindSorter(_Sorter):

    def __call__(self, scope1, scope2):
        return self.coef * cmp(scope1.kind, scope2.kind)

    kind = 'kind'


class UnderlinedSorter(_Sorter):

    def __call__(self, scope1, scope2):
        return self.coef * -cmp(self._is_underlined(scope1.name),
                                self._is_underlined(scope2.name))

    def _is_underlined(self, name):
        return name.startswith('_') and not name.endswith('_')

    kind = 'being underlined'


class SpecialSorter(_Sorter):

    def __call__(self, scope1, scope2):
        return self.coef * -cmp(self._is_special(scope1.name),
                                self._is_special(scope2.name))

    def _is_special(self, name):
        return name.startswith('__') and name.endswith('__')

    kind = 'being special method'


class PydocSorter(_Sorter):

    def __call__(self, scope1, scope2):
        return self.coef * -cmp(scope1.has_pydoc, scope2.has_pydoc)

    kind = 'having pydoc'
