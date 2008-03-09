import re

from rope.base import pynames, pyobjects, codeanalyze, evaluate


class Finder(object):
    """For finding occurrences of a name

    The constructor takes a `filters` argument.  It should be a list
    of functions that take a single argument.  For each possible
    occurrence, these functions are called in order with the an
    instance of `Occurrence`:

      * If it returns `None` other filters are tried.
      * If it returns `True`, the occurrence will be a match.
      * If it returns `False`, the occurrence will be skipped.
      * If all of the filters return `None`, it is skipped also.

    """

    def __init__(self, pycore, name, filters=[lambda o: True], docs=False):
        self.pycore = pycore
        self.name = name
        self.filters = filters
        self._textual_finder = _TextualFinder(name, docs=docs)

    def find_occurrences(self, resource=None, pymodule=None):
        """Generate `Occurrence` instances"""
        tools = _OccurrenceToolsCreator(self.pycore, resource=resource,
                                        pymodule=pymodule)
        for offset in self._textual_finder.find_offsets(tools.source_code):
            occurrence = Occurrence(tools, offset)
            for filter in self.filters:
                result = filter(occurrence)
                if result is None:
                    continue
                if result:
                    yield occurrence
                else:
                    break


class PyNameFilter(object):
    """For finding occurrences of a name"""

    def __init__(self, pynames, only_calls=False, imports=True, unsure=None):
        self.pynames = pynames
        self.only_calls = only_calls
        self.imports = imports
        self.unsure = unsure

    def __call__(self, occurrence):
        if self.only_calls and not occurrence.is_called():
            return False
        if not self.imports and occurrence.is_in_import_statement():
            return False
        try:
            new_pyname = occurrence.get_pyname()
        except evaluate.BadIdentifierError:
            return False
        for pyname in self.pynames:
            if same_pyname(pyname, new_pyname):
                return True
            elif self.unsure is not None and \
                 unsure_pyname(new_pyname):
                occurrence._unsure = self.unsure(occurrence)
                return occurrence._unsure
        return False


class FilteredFinder(object):
    """For finding occurrences of a name"""

    def __init__(self, pycore, name, pynames, only_calls=False,
                 imports=True, unsure=None, docs=False):
        filters = [PyNameFilter(pynames, only_calls, imports, unsure)]
        self.finder = Finder(pycore, name, filters=filters, docs=docs)

    def find_occurrences(self, resource=None, pymodule=None):
        """Generate `Occurrence` instances"""
        return self.finder.find_occurrences(resource, pymodule)


class Occurrence(object):

    def __init__(self, tools, offset):
        self.tools = tools
        self.offset = offset
        self.resource = tools.resource

    _unsure = False

    def get_word_range(self):
        return self.tools.word_finder.get_word_range(self.offset)

    def get_primary_range(self):
        return self.tools.word_finder.get_primary_range(self.offset)

    def get_pyname(self):
        return self.tools.name_finder.get_pyname_at(self.offset)

    def get_primary_and_pyname(self):
        return self.tools.name_finder.get_primary_and_pyname_at(self.offset)

    def is_in_import_statement(self):
        return (self.tools.word_finder.is_from_statement(self.offset) or
                self.tools.word_finder.is_import_statement(self.offset))

    def is_called(self):
        return self.tools.word_finder.is_a_function_being_called(self.offset)

    def is_defined(self):
        return self.tools.word_finder.is_a_class_or_function_name_in_header(self.offset)

    def is_a_fixed_primary(self):
        return self.tools.word_finder.is_a_class_or_function_name_in_header(self.offset) or \
               self.tools.word_finder.is_a_name_after_from_import(self.offset)

    def is_written(self):
        return self.tools.word_finder.is_assigned_here(self.offset)

    def is_unsure(self):
        return self._unsure


class MultipleFinders(object):

    def __init__(self, finders):
        self.finders = finders

    def find_occurrences(self, resource=None, pymodule=None):
        all_occurrences = []
        for finder in self.finders:
            all_occurrences.extend(finder.find_occurrences(resource, pymodule))
        all_occurrences.sort(self._cmp_occurrences)
        return all_occurrences

    def _cmp_occurrences(self, o1, o2):
        return cmp(o1.get_primary_range(), o2.get_primary_range())


def same_pyname(expected, pyname):
    """Check whether `expected` and `pyname` are the same"""
    if expected is None or pyname is None:
        return False
    if expected == pyname:
        return True
    if type(expected) not in (pynames.ImportedModule, pynames.ImportedName) and \
       type(pyname) not in (pynames.ImportedModule, pynames.ImportedName):
        return False
    return expected.get_definition_location() == pyname.get_definition_location() and \
           expected.get_object() == pyname.get_object()

def unsure_pyname(pyname, unbound=True):
    """Return `True` if we don't know what this name references"""
    if pyname is None:
        return True
    if unbound and not isinstance(pyname, pynames.UnboundName):
        return False
    if pyname.get_object() == pyobjects.get_unknown():
        return True


class _TextualFinder(object):

    def __init__(self, name, docs=False):
        self.name = name
        self.docs = docs
        self.comment_pattern = _TextualFinder.any('comment', [r'#[^\n]*'])
        self.string_pattern = _TextualFinder.any(
            'string', [codeanalyze.get_string_pattern()])
        self.pattern = self._get_occurrence_pattern(self.name)

    def find_offsets(self, source):
        if not self._fast_file_query(source):
            return
        if self.docs:
            searcher = self._normal_search
        else:
            searcher = self._re_search
        for matched in searcher(source):
            yield matched

    def _re_search(self, source):
        for match in self.pattern.finditer(source):
            for key, value in match.groupdict().items():
                if value and key == 'occurrence':
                    yield match.start(key)

    def _normal_search(self, source):
        current = 0
        while True:
            try:
                found = source.index(self.name, current)
                current = found + len(self.name)
                if (found == 0 or not self._is_id_char(source[found - 1])) and \
                   (current == len(source) or not self._is_id_char(source[current])):
                    yield found
            except ValueError:
                break

    def _is_id_char(self, c):
        return c.isalnum() or c == '_'

    def _fast_file_query(self, source):
        try:
            source.index(self.name)
            return True
        except ValueError:
            return False

    def _get_source(self, resource, pymodule):
        if resource is not None:
            return resource.read()
        else:
            return pymodule.source_code

    def _get_occurrence_pattern(self, name):
        occurrence_pattern = _TextualFinder.any('occurrence',
                                                 ['\\b' + name + '\\b'])
        pattern = re.compile(occurrence_pattern + '|' + self.comment_pattern +
                             '|' + self.string_pattern)
        return pattern

    @staticmethod
    def any(name, list_):
        return '(?P<%s>' % name + '|'.join(list_) + ')'


class _OccurrenceToolsCreator(object):

    def __init__(self, pycore, resource=None, pymodule=None):
        self.pycore = pycore
        self.resource = resource
        self.pymodule = pymodule
        self._name_finder = None
        self._source_code = None
        self._word_finder = None

    def get_name_finder(self):
        if self._name_finder is None:
            if self.pymodule is None:
                self.pymodule = self.pycore.resource_to_pyobject(self.resource)
            self._name_finder = evaluate.ScopeNameFinder(self.pymodule)
        return self._name_finder

    def get_source_code(self):
        if self._source_code is None:
            if self.resource is not None:
                self._source_code = self.resource.read()
            else:
                self._source_code = self.pymodule.source_code
        return self._source_code

    def get_word_finder(self):
        if self._word_finder is None:
            self._word_finder = codeanalyze.WordRangeFinder(
                self.get_source_code())
        return self._word_finder

    name_finder = property(get_name_finder)
    word_finder = property(get_word_finder)
    source_code = property(get_source_code)
