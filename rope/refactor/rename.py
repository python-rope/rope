import re

import rope.codeanalyze
import rope.pyobjects
from rope.refactor.change import (ChangeSet, ChangeFileContents,
                                  MoveResource, CreateFolder)

class RenameRefactoring(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
        self.comment_pattern = RenameRefactoring.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        self.string_pattern = RenameRefactoring.any("string",
                                                    [sq3string, dq3string, sqstring, dqstring])
    
    def local_rename(self, resource, offset, new_name):
        result = []
        source_code = resource.read()
        module_scope = self.pycore.get_string_scope(source_code, resource)
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        pattern = self._get_occurance_pattern(old_name)
        def scope_retriever():
            return module_scope
        new_contents = self._rename_occurance_in_file(source_code, scope_retriever, [old_pyname],
                                                     pattern, new_name)
        changes = ChangeSet()
        changes.add_change(ChangeFileContents(resource, new_contents))
        return changes
        
    def rename(self, resource, offset, new_name):
        module_scope = self.pycore.resource_to_pyobject(resource).get_scope()
        source_code = resource.read()
        word_finder = rope.codeanalyze.WordRangeFinder(source_code)
        old_name = word_finder.get_primary_at(offset).split('.')[-1]
        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
        old_pyname = pyname_finder.get_pyname_at(offset)
        if old_pyname is None:
            return None
        old_pynames = [old_pyname]
        if self._is_it_a_class_method(old_pyname):
            old_pynames = self._get_all_methods_in_hierarchy(old_pyname.get_object().
                                                             parent, old_name)
        pattern = self._get_occurance_pattern(old_name)
        changes = ChangeSet()
        for file_ in self.pycore.get_python_files():
            def scope_retriever():
                return self.pycore.resource_to_pyobject(file_).get_scope()
            new_content = self._rename_occurance_in_file(file_.read(), scope_retriever, 
                                                         old_pynames, pattern, new_name)
            if new_content is not None:
                changes.add_change(ChangeFileContents(file_, new_content))
        
        if old_pyname.get_object().get_type() == rope.pycore.PyObject.get_base_type('Module'):
            changes.add_change(self._rename_module(old_pyname.get_object(), new_name))
        return changes
    
    def _is_it_a_class_method(self, pyname):
        return pyname.has_block() and \
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
    
    def _rename_occurance_in_file(self, source_code, scope_retriever, old_pynames,
                                  pattern, new_name):
        result = []
        last_modified_char = 0
        pyname_finder = None
        for match in pattern.finditer(source_code):
            for key, value in match.groupdict().items():
                if value and key == "occurance":
                    match_start = match.start(key)
                    match_end = match.end(key)
                    if pyname_finder == None:
                        module_scope = scope_retriever()
                        pyname_finder = rope.codeanalyze.ScopeNameFinder(source_code, module_scope)
                    new_pyname = pyname_finder.get_pyname_at(match_start + 1)
                    for old_pyname in old_pynames:
                        if self._are_pynames_the_same(old_pyname, new_pyname):
                            result.append(source_code[last_modified_char:match_start] + new_name)
                            last_modified_char = match_end
        if last_modified_char != 0:
            result.append(source_code[last_modified_char:])
            return ''.join(result)
        return None
    
    def _are_pynames_the_same(self, pyname1, pyname2):
        return pyname1 == pyname2 or \
               (pyname1 is not None and pyname2 is not None and 
                pyname1.get_object() == pyname2.get_object() and
                pyname1.get_definition_location() == pyname2.get_definition_location())
    
    def _get_occurance_pattern(self, name):
        occurance_pattern = RenameRefactoring.any('occurance', ['\\b' + name + '\\b'])
        pattern = re.compile(occurance_pattern + "|" + \
                             self.comment_pattern + "|" + self.string_pattern)
        return pattern

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"

