import compiler

import rope.pynames
from rope.codeanalyze import SourceLinesAdapter


class ImportTools(object):
    
    def __init__(self, project):
        self.project = project
        self.pycore = project.get_pycore()
    
    def get_import_for_module(self, module):
        resource = module.get_resource()
        if resource.get_name() == '__init__.py':
            module_name = resource.get_parent().get_name()
            source_folder = resource.get_parent().get_parent()
        else:
            module_name = resource.get_name()[:-3]
            source_folder = resource.get_parent()
        
        source_folders = self.pycore.get_source_folders()
        while source_folder != self.project.get_root_folder() and \
              source_folder not in source_folders:
            module_name = source_folder.get_name() + '.' + module_name
            source_folder = source_folder.get_parent()
        return NormalImport(([module_name, None], ))
    
    def get_module_with_imports(self, module):
        return ModuleWithImports(self.pycore, module)


class ModuleWithImports(object):
    
    def __init__(self, pycore, pymodule):
        self.pycore = pycore
        self.pymodule = pymodule
        self.import_statements = None
    
    def get_import_statements(self):
        if self.import_statements is None:
            current_folder = None
            if self.pymodule.get_resource():
                current_folder = self.pymodule.get_resource().get_parent()
            visitor = _GlobalImportVisitor(current_folder, self.pycore)
            compiler.walk(self.pymodule._get_ast(), visitor)
            self.import_statements = visitor.imports
        return self.import_statements
    
    def _get_unbound_names(self, defined_pyobject):
        visitor = _GlobalUnboundNameFinder(self.pymodule, defined_pyobject)
        compiler.walk(self.pymodule._get_ast(), visitor)
        return visitor.unbound
    
    def remove_unused_imports(self):
        unbound_names = self._get_unbound_names(self.pymodule)
        def can_select(name):
            return name in unbound_names
        for import_statement in self.get_import_statements():
            import_statement.filter_names(can_select)
    
    def get_used_imports(self, defined_pyobject):
        all_import_statements = self.get_import_statements()
        unbound_names = self._get_unbound_names(defined_pyobject)
        def can_select(name):
            return name in unbound_names
        result = []
        for import_statement in all_import_statements:
            new_import = import_statement.import_info.filter_names(can_select)
            if not new_import.is_empty():
                result.append(new_import)
        return result

    def get_changed_source(self):
        lines = self.pymodule.source_code.splitlines(True)
        result = []
        last_index = 0
        for import_statement in self.import_statements:
            start = import_statement.start_line - 1
            result.extend(lines[last_index:start])
            last_index = import_statement.end_line - 1
            if not import_statement.import_info.is_empty():
                result.append(import_statement.import_info.get_import_statement() + '\n')
        result.extend(lines[last_index:])
        return ''.join(result)
    
    def add_import(self, import_info):
        pass
    
    def relative_to_absolute(self):
        pass
    
    def relative_to_new_relative(self):
        pass
    
    def expand_star(self):
        pass
    

class ImportStatement(object):
    
    def __init__(self, import_info, start_line, end_line):
        self.import_info = import_info
        self.start_line = start_line
        self.end_line = end_line
    
    def filter_names(self, can_select):
        self.import_info = self.import_info.filter_names(can_select)
    

class ImportInfo(object):
    
    def get_imported_names(self):
        pass
    
    def get_import_statement(self):
        pass
    
    def filter_names(can_select):
        pass
    
    def is_empty(self):
        pass


class NormalImport(ImportInfo):
    
    def __init__(self, names_and_aliases):
        self.names_and_aliases = names_and_aliases
    
    def get_imported_names(self):
        result = []
        for name, alias in self.names_and_aliases:
            if alias:
                result.append(alias)
            else:
                result.append(name.split('.')[0])
        return result
    
    def get_import_statement(self):
        result = 'import '
        for name, alias in self.names_and_aliases:
            result += name
            if alias:
                result += ' as ' + alias
            result += ', '
        return result[:-2]
    
    def filter_names(self, can_select):
        new_pairs = []
        for name, alias in self.names_and_aliases:
            imported = name
            if alias:
                imported = alias
            if can_select(imported):
                new_pairs.append((name, alias))
        return NormalImport(new_pairs)
    
    def is_empty(self):
        return len(self.names_and_aliases) == 0


class FromImport(ImportInfo):
    
    def __init__(self, module_name, level, names_and_aliases, current_folder, pycore):
        self.module_name = module_name
        self.level = level
        self.names_and_aliases = names_and_aliases
        self.current_folder = current_folder
        self.pycore = pycore

    def get_imported_names(self):
        if self.names_and_aliases[0][0] == '*':
            if self.level == 0:
                module = self.pycore.get_module(self.module_name,
                                                self.current_folder)
            else:
                module = self.pycore.get_relative_module(self.module_name,
                                                         self.current_folder,
                                                         self.level)
            return [name for name in module.get_attributes().keys()
                    if not name.startswith('_')]
        result = []
        for name, alias in self.names_and_aliases:
            if alias:
                result.append(alias)
            else:
                result.append(name)
        return result
    
    def get_import_statement(self):
        result = 'from ' + '.' * self.level + self.module_name + ' import '
        for name, alias in self.names_and_aliases:
            result += name
            if alias:
                result += ' as ' + alias
            result += ', '
        return result[:-2]

    def filter_names(self, can_select):
        new_pairs = []
        if self.names_and_aliases and self.names_and_aliases[0][0] == '*':
            for name in self.get_imported_names():
                if can_select(name):
                    new_pairs.append(self.names_and_aliases[0])
                    break
        else:
            for name, alias in self.names_and_aliases:
                imported = name
                if alias:
                    imported = alias
                if can_select(imported):
                    new_pairs.append((name, alias))
        return FromImport(self.module_name, self.level, new_pairs,
                          self.current_folder, self.pycore)
    
    def is_empty(self):
        return len(self.names_and_aliases) == 0


class _UnboundNameFinder(object):
    
    def __init__(self, pyobject):
        self.pyobject = pyobject
    
    def _visit_child_scope(self, node):
        pyobject = self.pyobject.get_scope().get_inner_scope_for_line(node.lineno).pyobject
        visitor = _LocalUnboundNameFinder(pyobject, self)
        for child in pyobject._get_ast().getChildNodes():
            compiler.walk(child, visitor)
    
    def visitFunction(self, node):
        self._visit_child_scope(node)

    def visitClass(self, node):
        self._visit_child_scope(node)
    
    def visitName(self, node):
        if self._get_root()._is_node_interesting(node) and not self.is_bound(node.name):
            self.add_unbound(node.name)

    def _get_root(self):
        pass
    
    def is_bound(self, name):
        pass
    
    def add_unbound(self, name):
        pass
    

class _GlobalUnboundNameFinder(_UnboundNameFinder):
    
    def __init__(self, pymodule, wanted_pyobject):
        super(_GlobalUnboundNameFinder, self).__init__(pymodule)
        self.unbound = set()
        self.names = set()
        for name, pyname in pymodule._get_structural_attributes().iteritems():
            if not isinstance(pyname, (rope.pynames.ImportedName,
                                       rope.pynames.ImportedModule)):
                self.names.add(name)
        wanted_scope = wanted_pyobject.get_scope()
        self.start = wanted_scope.get_start()
        self.end = wanted_scope.get_end()
    
    def _get_root(self):
        return self
    
    def is_bound(self, name):
        if name in self.names:
            return True
        return False
    
    def add_unbound(self, name):
        self.unbound.add(name)

    def _is_node_interesting(self, node):
        start = self.start
        end = self.end
        return start <= node.lineno < end


class _LocalUnboundNameFinder(_UnboundNameFinder):
    
    def __init__(self, pyobject, parent):
        super(_LocalUnboundNameFinder, self).__init__(pyobject)
        self.parent = parent
    
    def _get_root(self):
        return self.parent._get_root()
    
    def is_bound(self, name):
        if name in self.pyobject.get_attributes() or \
           self.parent.is_bound(name):
            return True
        return False
    
    def add_unbound(self, name):
        self.parent.add_unbound(name)


class _GlobalImportVisitor(object):
    
    def __init__(self, current_folder, pycore):
        self.current_folder = current_folder
        self.pycore = pycore
        self.imports = []
    
    def visitImport(self, node):
        import_statement = ImportStatement(NormalImport(node.names),
                                           node.lineno, node.lineno + 1)
        self.imports.append(import_statement)

    def visitFrom(self, node):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        import_info = FromImport(node.modname, level, node.names,
                                 self.current_folder, self.pycore)
        self.imports.append(ImportStatement(import_info, node.lineno, node.lineno + 1))
    
    def visitClass(self, node):
        pass
    
    def visitFunction(self, node):
        pass
