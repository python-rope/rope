import compiler

import rope.base.pynames
from rope.refactor.importutils import importinfo
from rope.refactor.importutils import actions


class ModuleImports(object):

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
        visitor = actions.RemovingVisitor(self.pycore, can_select)
        for import_statement in self.get_import_statements():
            import_statement.accept(visitor)

    def get_used_imports(self, defined_pyobject):
        all_import_statements = self.get_import_statements()
        result = []
        can_select = _OneTimeSelector(self._get_unbound_names(defined_pyobject))
        visitor = actions.FilteringVisitor(self.pycore, can_select)
        for import_statement in all_import_statements:
            new_import = import_statement.accept(visitor)
            if new_import is not None and not new_import.is_empty():
                result.append(new_import)
        return result

    def get_changed_source(self):
        imports = [stmt for stmt in self.get_import_statements()
                   if stmt.is_changed()]
        after_removing = self._remove_imports(imports)

        result = []
        last_index = 0
        for stmt in sorted(imports, self._compare_import_locations):
            start = self._get_import_location(stmt)
            result.extend(after_removing[last_index:start - 1])
            last_index = self._first_non_blank_line(after_removing, start - 1)
            if not stmt.import_info.is_empty():
                result.append(stmt.get_import_statement() + '\n')
                if self._first_non_blank_line(after_removing, last_index) < \
                   len(after_removing):
                    result.append('\n' * stmt.blank_lines)
        result.extend(after_removing[last_index:])
        return ''.join(result)

    def _get_import_location(self, stmt):
        start = stmt.get_new_start()
        if start is None:
            start = stmt.get_old_location()[0]
        return start

    def _compare_import_locations(self, stmt1, stmt2):
        def get_location(stmt):
            if stmt.get_new_start() is not None:
                return stmt.get_new_start()
            else:
                return stmt.get_old_location()[0]
        return cmp(get_location(stmt1), get_location(stmt2))

    def _remove_imports(self, imports):
        lines = self.pymodule.source_code.splitlines(True)
        after_removing = []
        last_index = 0
        for stmt in imports:
            start, end = stmt.get_old_location()
            after_removing.extend(lines[last_index:start - 1])
            last_index = end - 1
            for i in range(start, end):
                after_removing.append('')
        after_removing.extend(lines[last_index:])
        return after_removing
    
    def _first_non_blank_line(self, lines, lineno):
        result = lineno
        for line in lines[lineno:]:
            if line.strip() == '':
                result += 1
            else:
                break
        return result

    def add_import(self, import_info):
        visitor = actions.AddingVisitor(self.pycore, import_info)
        for import_statement in self.get_import_statements():
            if import_statement.accept(visitor):
                break
        else:
            all_imports = self.get_import_statements()
            last_line = 1
            blank_lines = 0
            if all_imports:
                last_line = all_imports[-1].end_line
                all_imports[-1].move(last_line)
                blank_lines = all_imports[-1].blank_lines
            all_imports.append(importinfo.ImportStatement(
                               import_info, last_line, last_line,
                               blank_lines=blank_lines))

    def filter_names(self, can_select):
        visitor = actions.RemovingVisitor(self.pycore, can_select)
        for import_statement in self.get_import_statements():
            import_statement.accept(visitor)

    def expand_stars(self):
        can_select = _OneTimeSelector(self._get_unbound_names(self.pymodule))
        visitor = actions.ExpandStarsVisitor(self.pycore, can_select)
        for import_statement in self.get_import_statements():
            import_statement.accept(visitor)

    def remove_duplicates(self):
        imports = self.get_import_statements()
        added_imports = []
        for import_stmt in imports:
            visitor = actions.AddingVisitor(self.pycore, import_stmt.import_info)
            for added_import in added_imports:
                if added_import.accept(visitor):
                    import_stmt.empty_import()
            else:
                added_imports.append(import_stmt)

    def get_relative_to_absolute_list(self):
        visitor = rope.refactor.importutils.actions.RelativeToAbsoluteVisitor(
            self.pycore, self._current_folder())
        for import_stmt in self.get_import_statements():
            import_stmt.accept(visitor)
        return visitor.to_be_absolute

    def get_self_import_fix_and_rename_list(self):
        visitor = rope.refactor.importutils.actions.SelfImportVisitor(
            self.pycore, self._current_folder(), self.pymodule.get_resource())
        for import_stmt in self.get_import_statements():
            import_stmt.accept(visitor)
        return visitor.to_be_fixed, visitor.to_be_renamed

    def _current_folder(self):
        return self.pymodule.get_resource().get_parent()

    def sort_imports(self):
        all_import_statements = self.get_import_statements()
        visitor = actions.SortingVisitor(self.pycore, self._current_folder())
        for import_statement in all_import_statements:
            import_statement.accept(visitor)
        last_index = 1
        if all_import_statements:
            last_index = all_import_statements[0].start_line
        in_projects = sorted(visitor.in_project, self._compare_imports)
        third_party = sorted(visitor.third_party, self._compare_imports)
        standards = sorted(visitor.standard, self._compare_imports)
        blank_lines = 1
        if not in_projects and not third_party:
            blank_lines = 2
        last_index = self._move_imports(standards, last_index, blank_lines)
        last_index = self._move_imports(third_party, last_index, blank_lines)
        last_index = self._move_imports(in_projects, last_index, 2)

    def _compare_imports(self, stmt1, stmt2):
        str1 = stmt1.get_import_statement()
        str2 = stmt2.get_import_statement()
        if str1.startswith('from ') and not str2.startswith('from '):
            return 1
        if not str1.startswith('from ') and str2.startswith('from '):
            return -1
        return cmp(str1, str2)

    def _move_imports(self, imports, index, blank_lines):
        if imports:
            for stmt in imports[:-1]:
                stmt.move(index)
                index += 1
            imports[-1].move(index, blank_lines)
            index += 1
        return index

    def handle_long_imports(self, maxdots, maxlength):
        visitor = actions.LongImportVisitor(
            self._current_folder(), self.pycore, maxdots, maxlength)
        for import_statement in self.get_import_statements():
            import_statement.accept(visitor)
        for import_info in visitor.new_imports:
            self.add_import(import_info)
        return visitor.to_be_renamed


class _OneTimeSelector(object):

    def __init__(self, names):
        self.names = names
        self.selected_names = set()

    def __call__(self, imported_primary):
        if self._can_name_be_added(imported_primary):
            for name in self._get_dotted_tokens(imported_primary):
                self.selected_names.add(name)
            return True
        return False

    def _get_dotted_tokens(self, imported_primary):
        tokens = imported_primary.split('.')
        for i in range(len(tokens)):
            yield '.'.join(tokens[:i + 1])

    def _can_name_be_added(self, imported_primary):
        for name in self._get_dotted_tokens(imported_primary):
            if name in self.names and name not in self.selected_names:
                return True
        return False


class _UnboundNameFinder(object):

    def __init__(self, pyobject):
        self.pyobject = pyobject

    def _visit_child_scope(self, node):
        pyobject = self.pyobject.get_module().get_scope().\
                   get_inner_scope_for_line(node.lineno).pyobject
        visitor = _LocalUnboundNameFinder(pyobject, self)
        for child in node.getChildNodes():
            compiler.walk(child, visitor)

    def visitFunction(self, node):
        self._visit_child_scope(node)

    def visitClass(self, node):
        self._visit_child_scope(node)

    def visitName(self, node):
        if self._get_root()._is_node_interesting(node) and not self.is_bound(node.name):
            self.add_unbound(node.name)

    def visitGetattr(self, node):
        result = []
        while isinstance(node, compiler.ast.Getattr):
            result.append(node.attrname)
            node = node.expr
        if isinstance(node, compiler.ast.Name):
            result.append(node.name)
            primary = '.'.join(reversed(result))
            if self._get_root()._is_node_interesting(node) and not self.is_bound(primary):
                self.add_unbound(primary)
        else:
            compiler.walk(node, self)

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
            if not isinstance(pyname, (rope.base.pynames.ImportedName,
                                       rope.base.pynames.ImportedModule)):
                self.names.add(name)
        wanted_scope = wanted_pyobject.get_scope()
        self.start = wanted_scope.get_start()
        self.end = wanted_scope.get_end() + 1

    def _get_root(self):
        return self

    def is_bound(self, primary):
        name = primary.split('.')[0]
        if name in self.names:
            return True
        return False

    def add_unbound(self, name):
        names = name.split('.')
        for i in range(len(names)):
            self.unbound.add('.'.join(names[:i + 1]))

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

    def is_bound(self, primary):
        name = primary.split('.')[0]
        if name in self.pyobject.get_scope().get_names() or \
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
        self.lines = self.pymodule.lines

    def visit_import(self, node, end_line):
        start_line = node.lineno
        import_statement = importinfo.ImportStatement(
            importinfo.NormalImport(node.names),start_line, end_line,
            self._get_text(start_line, end_line),
            blank_lines=self._count_empty_lines_after(start_line))
        self.imports.append(import_statement)
    
    def _count_empty_lines_after(self, lineno):
        result = 0
        for current in range(lineno + 1, self.lines.length()):
            line = self.lines.get_line(current)
            if line.strip() == '':
                result += 1
            else:
                break
        return result

    def _get_text(self, start_line, end_line):
        result = []
        for index in range(start_line, end_line):
            result.append(self.lines.get_line(index))
        return '\n'.join(result)

    def visit_from(self, node, end_line):
        level = 0
        if hasattr(node, 'level'):
            level = node.level
        import_info = importinfo.FromImport(node.modname, level, node.names,
                                            self.current_folder, self.pycore)
        start_line = node.lineno
        self.imports.append(importinfo.ImportStatement(
                            import_info, node.lineno, end_line,
                            self._get_text(start_line, end_line),
                            blank_lines=self._count_empty_lines_after(start_line)))

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
