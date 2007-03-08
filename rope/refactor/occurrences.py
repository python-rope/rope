import re

from rope.base import pynames, codeanalyze


class OccurrenceFinder(object):
    """For finding textual occurrences of a name"""

    def __init__(self, pycore, name):
        self.pycore = pycore
        self.name = name
        self.comment_pattern = OccurrenceFinder.any('comment', [r'#[^\n]*'])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = OccurrenceFinder.any(
            'string', [sq3string, dq3string, sqstring, dqstring])
        self.pattern = self._get_occurrence_pattern(self.name)

    def find_occurrences(self, resource=None, pymodule=None):
        """Generate `Occurrence` instances"""
        tools = _OccurrenceToolsCreator(self.pycore, resource, pymodule)
        for match in self.pattern.finditer(tools.source_code):
            for key, value in match.groupdict().items():
                if value and key == 'occurrence':
                    yield Occurrence(tools, match.start(key) + 1)

    def _get_source(self, resource, pymodule):
        if resource is not None:
            return resource.read()
        else:
            return pymodule.source_code

    def _get_occurrence_pattern(self, name):
        occurrence_pattern = OccurrenceFinder.any('occurrence',
                                                 ['\\b' + name + '\\b'])
        pattern = re.compile(occurrence_pattern + "|" + self.comment_pattern +
                             "|" + self.string_pattern)
        return pattern

    @staticmethod
    def any(name, list_):
        return "(?P<%s>" % name + "|".join(list_) + ")"


class Occurrence(object):

    def __init__(self, tools, offset):
        self.tools = tools
        self.offset = offset

    def get_word_range(self):
        start = self.tools.word_finder._find_word_start(self.offset - 1)
        end = self.tools.word_finder._find_word_end(self.offset - 1) + 1
        return (start, end)

    def get_primary_range(self):
        start = self.tools.word_finder._find_primary_start(self.offset - 1)
        end = self.tools.word_finder._find_word_end(self.offset - 1) + 1
        return (start, end)

    def get_pyname(self):
        return self.tools.name_finder.get_pyname_at(self.offset)

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


class FilteredFinder(object):

    def __init__(self, pycore, name, pynames, only_calls=False, imports=True):
        self.pycore = pycore
        self.pynames = pynames
        self.name = name
        self.only_calls = only_calls
        self.imports = imports
        self.occurrence_finder = OccurrenceFinder(pycore, name)

    def find_occurrences(self, resource=None, pymodule=None):
        for occurrence in self.occurrence_finder.find_occurrences(
            resource, pymodule):
            if self._is_a_match(occurrence):
                yield occurrence

    def _is_a_match(self, occurrence):
        if self.only_calls and not occurrence.is_called():
            return False
        if not self.imports and occurrence.is_in_import_statement():
            return False
        new_pyname = occurrence.get_pyname()
        for pyname in self.pynames:
            if self._are_pynames_the_same(pyname, new_pyname):
                return True
        return False

    def _are_pynames_the_same(self, pyname1, pyname2):
        if pyname1 is None or pyname2 is None:
            return False
        if pyname1 == pyname2:
            return True
        if type(pyname1) not in (pynames.ImportedModule, pynames.ImportedName) and \
           type(pyname2) not in (pynames.ImportedModule, pynames.ImportedName):
            return False
        return pyname1.get_definition_location() == pyname2.get_definition_location() and \
               pyname1.get_object() == pyname2.get_object()


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
            self._name_finder = codeanalyze.ScopeNameFinder(self.pymodule)
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
