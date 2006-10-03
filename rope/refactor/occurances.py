import re

import rope.codeanalyze
import rope.pynames
import rope.pyobjects
import rope.refactor.occurances


class OccurrenceFinder(object):
    
    def __init__(self, pycore, pynames, name,
                 function_calls=False, whole_primary=False,
                 imports=True):
        self.pycore = pycore
        self.pynames = pynames
        self.name = name
        self.function_calls = function_calls
        self.whole_primary = whole_primary
        self.imports = imports
        self.comment_pattern = OccurrenceFinder.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = OccurrenceFinder.any(
            "string", [sq3string, dq3string, sqstring, dqstring])
        self.pattern = self._get_occurance_pattern(self.name)
    
    def find_occurances(self, resource=None, pymodule=None):
        source_code = self._get_source(resource, pymodule)
        name_finder_creator = rope.refactor.occurances._LazyNameFinderCreator(self.pycore, resource, pymodule)
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        for match in self.pattern.finditer(source_code):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    start = match_start = match.start(key)
                    end = match_end = match.end(key)
                    if self.whole_primary:
                        start = word_finder._find_primary_start(match_start)
                        end = word_finder._find_word_end(match_start) + 1
                    if self._is_a_match(name_finder_creator, word_finder,
                                        match_start):
                        yield (start, end)

    def _get_source(self, resource, pymodule):
        if resource is not None:
            return resource.read()
        else:
            return pymodule.source_code

    def _is_a_match(self, name_finder_creator, word_finder, match_start):
        if self.function_calls and \
           not word_finder.is_a_function_being_called(match_start + 1):
            return False
        if self.whole_primary and \
           word_finder.is_a_class_or_function_name_in_header(match_start + 1):
            return False
        if not self.imports and \
           (word_finder.is_from_statement(match_start + 1) or
            word_finder.is_import_statement(match_start + 1)):
            return False
        new_pyname = name_finder_creator.get_name_finder().get_pyname_at(match_start + 1)
        for pyname in self.pynames:
            if self._are_pynames_the_same(pyname, new_pyname):
                return True
        return False

    def _are_pynames_the_same(self, pyname1, pyname2):
        return pyname1 == pyname2 or \
               (pyname1 is not None and pyname2 is not None and 
                pyname1.get_object() == pyname2.get_object() and
                pyname1.get_definition_location() == pyname2.get_definition_location())
    
    def _get_occurance_pattern(self, name):
        occurance_pattern = OccurrenceFinder.any('occurance', ['\\b' + name + '\\b'])
        pattern = re.compile(occurance_pattern + "|" + \
                             self.comment_pattern + "|" + self.string_pattern)
        return pattern

    @staticmethod
    def any(name, list_):
        return "(?P<%s>" % name + "|".join(list_) + ")"


class _LazyNameFinderCreator(object):
    
    def __init__(self, pycore, resource=None, pymodule=None):
        self.pycore = pycore
        self.resource = resource
        self.pymodule = pymodule
        self.name_finder = None
    
    def get_name_finder(self):
        if self.name_finder is None:
            if self.pymodule is None:
                self.pymodule = self.pycore.resource_to_pyobject(self.resource)
            self.pyname_finder = rope.codeanalyze.ScopeNameFinder(self.pymodule)
        return self.pyname_finder
