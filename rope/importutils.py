import compiler

import rope.pynames
import rope.refactor.rename
from rope.codeanalyze import SourceLinesAdapter


class ImportTools(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def get_import_for_module(self, module):
        module_name = ImportTools.get_module_name(self.pycore, module.get_resource())
        return NormalImport(((module_name, None), ))
    
    def get_from_import_for_module(self, module, name):
        module_name = ImportTools.get_module_name(self.pycore, module.get_resource())
        return FromImport(module_name, 0, ((name, None),),
                          module.get_resource().get_parent(), self.pycore)

    def get_module_with_imports(self, module):
        return ModuleWithImports(self.pycore, module)
    
    def transform_froms_to_normal_imports(self, pymodule):
        resource = pymodule.get_resource()
        pymodule = self._clean_up_imports(pymodule)
        module_with_imports = self.get_module_with_imports(pymodule)
        for import_stmt in module_with_imports.get_import_statements():
            if not self._can_import_be_transformed_to_normal_import(import_stmt.import_info):
                continue
            pymodule = self._from_to_normal(pymodule, import_stmt)
        
        # Adding normal imports in place of froms
        module_with_imports = self.get_module_with_imports(pymodule)
        for import_stmt in module_with_imports.get_import_statements():
            if self._can_import_be_transformed_to_normal_import(import_stmt.import_info):
                import_stmt.import_info = \
                    NormalImport(((import_stmt.import_info.module_name, None),))
        module_with_imports.remove_duplicates()
        return module_with_imports.get_changed_source()

    def _from_to_normal(self, pymodule, import_stmt):
        resource = pymodule.get_resource()
        from_import = import_stmt.import_info
        module_name = from_import.module_name
        imported_pymodule = self.pycore.get_module(module_name)
        for name, alias in from_import.names_and_aliases:
            imported = name
            if alias is not None:
                imported = alias
            rename_in_module = rope.refactor.rename.RenameInModule(
                self.pycore, [imported_pymodule.get_attribute(name)], imported,
                module_name + '.' + name, replace_primary=True, imports=False)
            source = rename_in_module.get_changed_module(pymodule=pymodule)
            if source is not None:
                pymodule = self.pycore.get_string_module(source, resource)
        return pymodule

    def _clean_up_imports(self, pymodule):
        resource = pymodule.get_resource()
        module_with_imports = self.get_module_with_imports(pymodule)
        module_with_imports.expand_stars()
        source = module_with_imports.get_changed_source()
        if source is not None:
            pymodule = self.pycore.get_string_module(source, resource)
        source = self.transform_relative_imports_to_absolute(pymodule)
        if source is not None:
            pymodule = self.pycore.get_string_module(source, resource)

        module_with_imports = self.get_module_with_imports(pymodule)
        module_with_imports.remove_duplicates()
        module_with_imports.remove_unused_imports()
        source = module_with_imports.get_changed_source()
        if source is not None:
            pymodule = self.pycore.get_string_module(source, resource)
        return pymodule
    
    def transform_relative_imports_to_absolute(self, pymodule):
        module_with_imports = self.get_module_with_imports(pymodule)
        to_be_absolute_list = module_with_imports.get_relative_to_absolute_list()
        source = module_with_imports.get_changed_source()
        if source is not None:
            pymodule = self.pycore.get_string_module(source, pymodule.get_resource())
        for name, absolute_name in to_be_absolute_list:
            old_name = name.split('.')[-1]
            old_pyname = rope.codeanalyze.StatementEvaluator.get_string_result(
                pymodule.get_scope(), name)
            rename_in_module = rope.refactor.rename.RenameInModule(
                self.pycore, [old_pyname], old_name,
                absolute_name, replace_primary=True, imports=False)
            source = rename_in_module.get_changed_module(pymodule=pymodule)
            if source is not None:
                pymodule = self.pycore.get_string_module(source, pymodule.get_resource())
        return pymodule.source_code
    
    def _can_import_be_transformed_to_normal_import(self, import_info):
        if not isinstance(import_info, FromImport):
            return False
        return True

    @staticmethod
    def get_module_name(pycore, resource):
        if resource.is_folder():
            module_name = resource.get_name()
            source_folder = resource.get_parent()
        elif resource.get_name() == '__init__.py':
            module_name = resource.get_parent().get_name()
            source_folder = resource.get_parent().get_parent()
        else:
            module_name = resource.get_name()[:-3]
            source_folder = resource.get_parent()

        source_folders = pycore.get_source_folders()
        source_folders.extend(pycore.get_python_path_folders())
        while source_folder != source_folder.get_parent() and \
              source_folder not in source_folders:
            module_name = source_folder.get_name() + '.' + module_name
            source_folder = source_folder.get_parent()
        return module_name


class ModuleWithImports(object):
    
    def __init__(self, pycore, pymodule):
        self.pycore = pycore
        self.pymodule = pymodule
        self.import_statements = None
    
    def get_import_statements(self):
        if self.import_statements is None:
            self.import_statements = _GlobalImportFinder(self.pymodule,
                                                         self.pycore).\
                                     find_import_statements()
        return self.import_statements
    
    def _get_unbound_names(self, defined_pyobject):
        visitor = _GlobalUnboundNameFinder(self.pymodule, defined_pyobject)
        compiler.walk(self.pymodule._get_ast(), visitor)
        return visitor.unbound
    
    def remove_unused_imports(self):
        can_select = _OneTimeSelector(self._get_unbound_names(self.pymodule))
        for import_statement in self.get_import_statements():
            import_statement.filter_names(can_select)
    
    def get_used_imports(self, defined_pyobject):
        all_import_statements = self.get_import_statements()
        result = []
        can_select = _OneTimeSelector(self._get_unbound_names(defined_pyobject))
        for import_statement in all_import_statements:
            new_import = import_statement.import_info.filter_names(can_select)
            if new_import is not None and not new_import.is_empty():
                result.append(new_import)
        return result

    def get_changed_source(self):
        lines = self.pymodule.source_code.splitlines(True)
        result = []
        last_index = 0
        for import_statement in self.get_import_statements():
            start = import_statement.start_line - 1
            result.extend(lines[last_index:start])
            last_index = import_statement.end_line - 1
            if not import_statement.import_info.is_empty():
                result.append(import_statement.get_import_statement() + '\n')
        result.extend(lines[last_index:])
        return ''.join(result)
    
    def add_import(self, import_info):
        for import_statement in self.get_import_statements():
            if import_statement.add_import(import_info):
                break
        else:
            all_imports = self.get_import_statements()
            last_line = 1
            if all_imports:
                last_line = all_imports[-1].end_line
            all_imports.append(ImportStatement(import_info, last_line, last_line))
    
    def filter_names(self, can_select):
        all_import_statements = self.get_import_statements()
        for import_statement in all_import_statements:
            new_import = import_statement.filter_names(can_select)
    
    def expand_stars(self):
        can_select = _OneTimeSelector(self._get_unbound_names(self.pymodule))
        for import_statement in self.get_import_statements():
            import_statement.expand_star(can_select)
    
    def remove_duplicates(self):
        imports = self.get_import_statements()
        added_imports = []
        for import_stmt in imports:
            for added_import in added_imports:
                if added_import.add_import(import_stmt.import_info):
                    import_stmt.empty_import()
            else:
                added_imports.append(import_stmt)
    
    def get_relative_to_absolute_list(self):
        visitor = _ImportInfoRelativeToAbsoluteVisitor(
            self.pycore, self.pymodule.get_resource().get_parent())
        for import_stmt in self.get_import_statements():
            import_stmt.accept_visitor(visitor)
        return visitor.to_be_absolute


class _ImportInfoRelativeToAbsoluteVisitor(object):
    
    def __init__(self, pycore, current_folder):
        self.to_be_absolute = []
        self.pycore = pycore
        self.current_folder = current_folder
    
    def visitFromImport(self, import_info):
        return import_info.relative_to_absolute(self.pycore, self.current_folder)
    
    def visitNormalImport(self, import_info):
        self.to_be_absolute.extend(import_info.get_relative_to_absolute_list(
                                   self.pycore, self.current_folder))
        return import_info.relative_to_absolute(
            self.pycore, self.current_folder)
    
    def visitEmptyImport(self, import_info):
        pass
    
    def dispatch(self, import_info):
        method = getattr(self, 'visit' + import_info.__class__.__name__)
        return method(import_info)


class _OneTimeSelector(object):
    
    def __init__(self, names):
        self.names = names
        self.selected_names = set()
    
    def __call__(self, imported_primary):
        name = imported_primary.split('.')[0]
        if name in self.names and imported_primary not in self.selected_names:
            for imported_name in self.selected_names:
                if imported_name.startswith(imported_primary + '.'):
                    return False
            self.selected_names.add(imported_primary)
            return True
        return False


class ImportStatement(object):
    
    def __init__(self, import_info, start_line, end_line, main_statement=None):
        self.start_line = start_line
        self.end_line = end_line
        self.main_statement = main_statement
        self._import_info = None
        self.import_info = import_info
        self.is_changed = False
    
    def _get_import_info(self):
        return self._import_info
    
    def _set_import_info(self, new_import):
        if new_import is not None and not new_import == self._import_info:
            self.is_changed = True
            self._import_info = new_import
    
    import_info = property(_get_import_info, _set_import_info)
    
    def filter_names(self, can_select):
        new_import = self.import_info.filter_names(can_select)
        self.import_info = new_import
    
    def add_import(self, import_info):
        result = self.import_info.add_import(import_info)
        if result is not None:
            self.import_info = result
            return True
        return False
    
    def get_import_statement(self):
        if self.is_changed or self.main_statement is None:
            return self.import_info.get_import_statement()
        else:
            return self.main_statement
    
    def expand_star(self, can_select):
        if isinstance(self.import_info, FromImport) and \
           self.import_info.is_star_import():
            self.import_info = self.import_info.expand_star(can_select)
        else:
            for primary in self.import_info.get_imported_primaries():
                can_select(primary)
    
    def empty_import(self):
        self.import_info = ImportInfo.get_empty_import()
    
    def accept_visitor(self, visitor):
        self.import_info = visitor.dispatch(self.import_info)


class ImportInfo(object):
    
    def get_imported_primaries(self):
        pass
    
    def get_imported_names(self):
        return [primary.split('.')[0]
                for primary in self.get_imported_primaries()]
    
    def get_import_statement(self):
        pass
    
    def filter_names(self, can_select):
        def can_select_name_and_alias(name, alias):
            imported = name
            if alias:
                imported = alias
            return can_select(imported)
        return self.filter_names_and_aliases(can_select_name_and_alias)
    
    def filter_names_and_aliases(can_select):
        pass
    
    def is_empty(self):
        pass
    
    def add_import(self, import_info):
        pass
    
    def __hash__(self):
        return hash(self.get_import_statement())
    
    def _are_name_and_alias_lists_equal(self, list1, list2):
        if len(list1) != len(list2):
            return False
        for pair1, pair2 in zip(list1, list2):
            if pair1 != pair2:
                return False
        return True
    
    def __eq__(self, obj):
        return isinstance(obj, self.__class__) and \
               self.get_import_statement() == obj.get_import_statement()

    @staticmethod
    def get_empty_import():
        class EmptyImport(ImportInfo):
            names_and_aliases = []
            def is_empty(self):
                return True
            def get_imported_primaries(self):
                return []
        return EmptyImport()
    

class NormalImport(ImportInfo):
    
    def __init__(self, names_and_aliases):
        self.names_and_aliases = names_and_aliases
    
    def get_imported_primaries(self):
        result = []
        for name, alias in self.names_and_aliases:
            if alias:
                result.append(alias)
            else:
                result.append(name)
        return result
    
    def get_import_statement(self):
        result = 'import '
        for name, alias in self.names_and_aliases:
            result += name
            if alias:
                result += ' as ' + alias
            result += ', '
        return result[:-2]
    
    def filter_names_and_aliases(self, can_select):
        new_pairs = []
        for name, alias in self.names_and_aliases:
            if can_select(name, alias):
                new_pairs.append((name, alias))
        return NormalImport(new_pairs)
    
    def is_empty(self):
        return len(self.names_and_aliases) == 0

    def add_import(self, import_info):
        if not isinstance(import_info, self.__class__):
            return None
        # Adding ``import x`` and ``import x.y`` that results ``import x.y``
        if len(self.names_and_aliases) == len(import_info.names_and_aliases) == 1:
            imported1 = self.names_and_aliases[0]
            imported2 = import_info.names_and_aliases[0]
            if imported1[1] == imported2[1] == None:
                if imported1[0].startswith(imported2[0] + '.'):
                    return self
                if imported2[0].startswith(imported1[0] + '.'):
                    return import_info
        # Multiple imports using a single import statement is discouraged
        # so we won't bother adding them.
        if self._are_name_and_alias_lists_equal(self.names_and_aliases,
                                                import_info.names_and_aliases):
            return self
        return None
    
    def relative_to_absolute(self, pycore, current_folder):
        new_pairs = []
        for name, alias in self.names_and_aliases:
            resource = pycore.find_module(name, current_folder=current_folder)
            if resource is None:
                new_pairs.append((name, alias))
                continue
            absolute_name = ImportTools.get_module_name(pycore, resource)
            new_pairs.append((absolute_name, alias))
        if not self._are_name_and_alias_lists_equal(new_pairs, self.names_and_aliases):
            return NormalImport(new_pairs)
        return None
    
    def get_relative_to_absolute_list(self, pycore, current_folder):
        result = []
        for name, alias in self.names_and_aliases:
            if alias is not None:
                continue
            resource = pycore.find_module(name, current_folder=current_folder)
            if resource is None:
                continue
            absolute_name = ImportTools.get_module_name(pycore, resource)
            if absolute_name != name:
                result.append((name, absolute_name))
        return result
    

class FromImport(ImportInfo):
    
    def __init__(self, module_name, level, names_and_aliases, current_folder, pycore):
        self.module_name = module_name
        self.level = level
        self.names_and_aliases = names_and_aliases
        self.current_folder = current_folder
        self.pycore = pycore

    def get_imported_primaries(self):
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

    def filter_names_and_aliases(self, can_select):
        new_pairs = []
        if self.names_and_aliases and self.names_and_aliases[0][0] == '*':
            for name in self.get_imported_names():
                if can_select(name, None):
                    new_pairs.append(self.names_and_aliases[0])
                    break
        else:
            for name, alias in self.names_and_aliases:
                if can_select(name, alias):
                    new_pairs.append((name, alias))
        return FromImport(self.module_name, self.level, new_pairs,
                          self.current_folder, self.pycore)
    
    def is_empty(self):
        return len(self.names_and_aliases) == 0
    
    def add_import(self, import_info):
        if isinstance(import_info, self.__class__) and \
           self.module_name == import_info.module_name and \
           self.level == import_info.level:
            if self.is_star_import():
                return self
            if import_info.is_star_import():
                return import_info
            new_pairs = list(self.names_and_aliases)
            for pair in import_info.names_and_aliases:
                if pair not in new_pairs:
                    new_pairs.append(pair)
            return FromImport(self.module_name, self.level, new_pairs,
                              self.current_folder, self.pycore)
        return None
    
    def is_star_import(self):
        return len(self.names_and_aliases) > 0 and self.names_and_aliases[0][0] == '*'
    
    def expand_star(self, can_select):
        if not self.is_star_import():
            return None
        new_pairs = []
        for name in self.get_imported_names():
            new_pairs.append((name, None))
        new_import = FromImport(self.module_name, self.level, new_pairs,
                                self.current_folder, self.pycore)
        return new_import.filter_names(can_select)

    def relative_to_absolute(self, pycore, current_folder):
        if self.level == 0:
            resource = pycore.find_module(self.module_name,
                                          current_folder=current_folder)
        else:
            resource = pycore.find_relative_module(
                self.module_name, current_folder, self.level)
        if resource is None:
            return None
        absolute_name = ImportTools.get_module_name(pycore, resource)
        if self.module_name != absolute_name:
            return FromImport(absolute_name, 0, self.names_and_aliases,
                              current_folder, pycore)
        return None
    

class _UnboundNameFinder(object):
    
    def __init__(self, pyobject):
        self.pyobject = pyobject
    
    def _visit_child_scope(self, node):
        pyobject = self.pyobject.get_module().get_scope().\
                   get_inner_scope_for_line(node.lineno).pyobject
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
        self.end = wanted_scope.get_end() + 1
    
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


class _GlobalImportFinder(object):
    
    def __init__(self, pymodule, pycore):
        self.current_folder = None
        if pymodule.get_resource():
            self.current_folder = pymodule.get_resource().get_parent()
            self.pymodule = pymodule
        self.pycore = pycore
        self.imports = []
        self.lines = SourceLinesAdapter(self.pymodule.source_code)
    
    def visit_import(self, node, end_line):
        start_line = node.lineno
        import_statement = ImportStatement(NormalImport(node.names),
                                           start_line, end_line,
                                           self._get_text(start_line, end_line))
        self.imports.append(import_statement)
    
    def _get_text(self, start_line, end_line):
        result = []
        for index in range(start_line, end_line):
            result.append(self.lines.get_line(index))
        return '\n'.join(result)

    def visit_from(self, node, end_line):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        import_info = FromImport(node.modname, level, node.names,
                                 self.current_folder, self.pycore)
        start_line = node.lineno
        self.imports.append(ImportStatement(import_info, node.lineno, end_line,
                                            self._get_text(start_line, end_line)))
    
    def find_import_statements(self):
        nodes = self.pymodule._get_ast().node.nodes
        for index, node in enumerate(nodes):
            if isinstance(node, (compiler.ast.Import, compiler.ast.From)):
                end_line = self.lines.length() + 1
                if index + 1 < len(nodes):
                    end_line = nodes[index + 1].lineno
                while self.lines.get_line(end_line - 1).strip() == '':
                    end_line -= 1
            if isinstance(node, compiler.ast.Import):
                self.visit_import(node, end_line)
            if isinstance(node, compiler.ast.From):
                self.visit_from(node, end_line)
        return self.imports
