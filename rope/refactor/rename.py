import re

import rope.codeanalyze
import rope.pynames
import rope.pyobjects
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)

class RenameRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def local_rename(self, resource, offset, new_name):
        return self._rename(resource, offset, new_name, True)
    
    def rename(self, resource, offset, new_name):
        return self._rename(resource, offset, new_name)
    
    def _rename(self, resource, offset, new_name, in_file=False):
        files = [resource]
        if not in_file:
            files = self.pycore.get_python_files()
        old_name, old_pyname = rope.codeanalyze.\
                               get_name_and_pyname_at(self.pycore, resource, offset)
        if old_pyname is None:
            return None
        old_pynames = [old_pyname]
        if self._is_it_a_class_method(old_pyname) and not in_file:
            old_pynames = self._get_all_methods_in_hierarchy(old_pyname.get_object().
                                                             parent, old_name)
        changes = ChangeSet()
        for file_ in files:
            new_content = RenameInModule(self.pycore, old_pynames, old_name, new_name).\
                          get_changed_module(file_)
            if new_content is not None:
                changes.add_change(ChangeFileContents(file_, new_content))
        
        if old_pyname.get_object().get_type() == rope.pycore.PyObject.get_base_type('Module'):
            changes.add_change(self._rename_module(old_pyname.get_object(), new_name))
        return changes
    
    def _is_it_a_class_method(self, pyname):
        return isinstance(pyname, rope.pynames.DefinedName) and \
               pyname.get_object().get_type() == rope.pyobjects.PyObject.get_base_type('Function') and \
               pyname.get_object().parent.get_type() == rope.pyobjects.PyObject.get_base_type('Type')
    
    def _get_superclasses_defining_method(self, pyclass, attr_name):
        result = set()
        for superclass in pyclass.get_superclasses():
            if attr_name in superclass.get_attributes():
                result.update(self._get_superclasses_defining_method(superclass, attr_name))
        if not result:
            return set([pyclass])
        return result
    
    def _get_all_methods_in_subclasses(self, pyclass, attr_name):
        result = set([pyclass.get_attribute(attr_name)])
        for subclass in self.pycore.get_subclasses(pyclass):
            result.update(self._get_all_methods_in_subclasses(subclass, attr_name))
        return result
    
    def _get_all_methods_in_hierarchy(self, pyclass, attr_name):
        superclasses = self._get_superclasses_defining_method(pyclass, attr_name)
        methods = set()
        for superclass in superclasses:
            methods.update(self._get_all_methods_in_subclasses(superclass, attr_name))
        return methods
    
    def _rename_module(self, pyobject, new_name):
        resource = pyobject.get_resource()
        if not resource.is_folder():
            new_name = new_name + '.py'
        parent_path = resource.get_parent().get_path()
        if parent_path == '':
            new_location = new_name
        else:
            new_location = parent_path + '/' + new_name
        return MoveResource(resource, new_location)
    

class RenameInModule(object):
    
    def __init__(self, pycore, old_pynames, old_name, new_name,
                 only_function_calls=False, replace_primary=False):
        self.pycore = pycore
        self.old_pynames = old_pynames
        self.old_name = old_name
        self.new_name = new_name
        self.only_function_calls = only_function_calls
        self.replace_primary = replace_primary
        self.comment_pattern = RenameInModule.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = RenameInModule.any(
            "string", [sq3string, dq3string, sqstring, dqstring])
        self.pattern = self._get_occurance_pattern(self.old_name)
    
    def get_changed_module(self, resource=None, pymodule=None):
        if resource is not None:
            source_code = resource.read()
        else:
            source_code = pymodule.source_code
        result = []
        last_modified_char = 0
        pyname_finder = None
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        for match in self.pattern.finditer(source_code):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    start = match_start = match.start(key)
                    end = match_end = match.end(key)
                    if pyname_finder == None:
                        pyname_finder = self._create_pyname_finder(source_code, resource, pymodule)
                    new_pyname = pyname_finder.get_pyname_at(match_start + 1)
                    
                    if self.replace_primary:
                        start = word_finder._find_primary_start(match_start + 1)
                        end = word_finder._find_word_end(match_start + 1) + 1
                    for old_pyname in self.old_pynames:
                        if self.only_function_calls and \
                           not word_finder.is_a_function_being_called(match_start + 1):
                            continue
                        if self._are_pynames_the_same(old_pyname, new_pyname):
                            result.append(source_code[last_modified_char:start]
                                          + self.new_name)
                            last_modified_char = end
        if last_modified_char != 0:
            result.append(source_code[last_modified_char:])
            return ''.join(result)
        return None

    def _create_pyname_finder(self, source_code, resource, pymodule):
        if resource is not None:
            pymodule = self.pycore.resource_to_pyobject(resource)
        pyname_finder = rope.codeanalyze.ScopeNameFinder(pymodule)
        return pyname_finder
    
    def _are_pynames_the_same(self, pyname1, pyname2):
        return pyname1 == pyname2 or \
               (pyname1 is not None and pyname2 is not None and 
                pyname1.get_object() == pyname2.get_object() and
                pyname1.get_definition_location() == pyname2.get_definition_location())
    
    def _get_occurance_pattern(self, name):
        occurance_pattern = RenameInModule.any('occurance', ['\\b' + name + '\\b'])
        pattern = re.compile(occurance_pattern + "|" + \
                             self.comment_pattern + "|" + self.string_pattern)
        return pattern

    @staticmethod
    def any(name, list_):
        return "(?P<%s>" % name + "|".join(list_) + ")"

