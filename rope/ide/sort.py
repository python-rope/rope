from rope.base import change


class SortScopes(object):

    def __init__(self, project, resource, offset):
        self.pycore = project.pycore
        self.resource = resource
        self.pymodule = self.pycore.resource_to_pyobject(resource)
        self.scope = self.pymodule.get_scope().\
                     get_inner_scope_for_offset(offset)

    def get_changes(self):
        changes = change.ChangeSet('Sorting scopes')
        scopes = self._get_scopes()
        if not scopes:
            return changes
        start = scopes[0].start
        end = scopes[-1].end
        blanks = scopes[0].blanks
        scopes[-1].blanks = blanks
        self._sort_scopes(scopes)
        scopes[-1].blanks = 0
        result = []
        result.append(self._get_text(1, start - 1))
        for scope in scopes:
            extracted = self._get_text(scope.start, scope.end)
            result.append(extracted + '\n' * scope.blanks)
        result.append(self._get_text(end + 1))
        changes.add_change(change.ChangeContents(self.resource,
                                                 ''.join(result)))
        return changes

    def _sort_scopes(self, scopes):
        def compare_scopes(scope1, scope2):
            return cmp(scope1.name, scope2.name)
        scopes.sort(cmp=compare_scopes)

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


class _Scope(object):

    def __init__(self, scope, start, end, blanks):
        self.start = start
        self.end = end
        self.blanks = blanks
        self.name = scope.pyobject.get_name()


class _Statements(object):

    def __init__(self, start, end, blanks):
        self.start = start
        self.end = end
        self.blanks = blanks
