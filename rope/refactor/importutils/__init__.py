"""A package for handling imports

This package provides tools for modifing module imports after
refactorings or as a separate task.

"""


import rope.base.pynames
import rope.refactor.rename

from rope.refactor.importutils.importinfo import \
     (NormalImport, FromImport, get_module_name)
from rope.refactor.importutils import module_imports


class ImportTools(object):
    
    def __init__(self, pycore):
        self.pycore = pycore
    
    def get_import_for_module(self, module):
        module_name = get_module_name(self.pycore, module.get_resource())
        return NormalImport(((module_name, None), ))
    
    def get_from_import_for_module(self, module, name):
        module_name = get_module_name(self.pycore, module.get_resource())
        return FromImport(module_name, 0, ((name, None),),
                          module.get_resource().get_parent(), self.pycore)

    def get_module_with_imports(self, module):
        return module_imports.ModuleImports(self.pycore, module)
    
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
            pymodule = self._rename_in_module(pymodule, name, absolute_name)
        return pymodule.source_code
    
    def _can_import_be_transformed_to_normal_import(self, import_info):
        if not isinstance(import_info, FromImport):
            return False
        return True
    
    def organize_imports(self, pymodule):
        module_with_imports = self.get_module_with_imports(pymodule)
        module_with_imports.remove_unused_imports()
        module_with_imports.remove_duplicates()
        before_removing_self_import = module_with_imports.get_changed_source()
        to_be_fixed, to_be_renamed = module_with_imports.get_self_import_fix_and_rename_list()
        source = module_with_imports.get_changed_source()
        if source is not None:
            pymodule = self.pycore.get_string_module(source, pymodule.get_resource())
        for name in to_be_fixed:
            try:
                pymodule = self._rename_in_module(pymodule, name, '', till_dot=True)
            except ValueError:
                # There is a self import with direct access to it
                return before_removing_self_import
        for name, new_name in to_be_renamed:
            pymodule = self._rename_in_module(pymodule, name, new_name)
        return pymodule.source_code

    def _rename_in_module(self, pymodule, name, new_name, till_dot=False):
        old_name = name.split('.')[-1]
        old_pyname = rope.base.codeanalyze.StatementEvaluator.get_string_result(
            pymodule.get_scope(), name)
        occurrence_finder = rope.refactor.occurrences.FilteredOccurrenceFinder(
            self.pycore, old_name, [old_pyname], imports=False)
        changes = rope.refactor.sourceutils.ChangeCollector(pymodule.source_code)
        for occurrence in occurrence_finder.find_occurrences(pymodule=pymodule):
            start, end = occurrence.get_primary_range()
            if till_dot:
                new_end = pymodule.source_code.index('.', end) + 1
                space = pymodule.source_code[end:new_end - 1].strip()
                if not space == '':
                    for c in space:
                        if not c.isspace() and c not in '\\':
                            raise ValueError()
                end = new_end
            changes.add_change(start, end, new_name)
        source = changes.get_changed()
        if source is not None:
            pymodule = self.pycore.get_string_module(source, pymodule.get_resource())
        return pymodule
