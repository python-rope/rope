import os
import sys

from rope.base import pyobjects, exceptions
from rope.refactor.importutils import importinfo
from rope.base import exceptions


class ImportInfoVisitor(object):

    def dispatch(self, import_):
        try:
            method = getattr(self, 'visit' + import_.import_info.__class__.__name__)
            return method(import_, import_.import_info)
        except exceptions.ModuleNotFoundException:
            pass

    def visitEmptyImport(self, import_stmt, import_info):
        pass

    def visitNormalImport(self, import_stmt, import_info):
        pass

    def visitFromImport(self, import_stmt, import_info):
        pass


class RelativeToAbsoluteVisitor(ImportInfoVisitor):

    def __init__(self, pycore, current_folder):
        self.to_be_absolute = []
        self.pycore = pycore
        self.current_folder = current_folder

    def visitNormalImport(self, import_stmt, import_info):
        self.to_be_absolute.extend(self._get_relative_to_absolute_list(import_info))
        new_pairs = []
        for name, alias in import_info.names_and_aliases:
            resource = self.pycore.find_module(name, current_folder=self.current_folder)
            if resource is None:
                new_pairs.append((name, alias))
                continue
            absolute_name = importinfo.get_module_name(self.pycore, resource)
            new_pairs.append((absolute_name, alias))
        if not import_info._are_name_and_alias_lists_equal(
            new_pairs, import_info.names_and_aliases):
            import_stmt.import_info = importinfo.NormalImport(new_pairs)

    def _get_relative_to_absolute_list(self, import_info):
        result = []
        for name, alias in import_info.names_and_aliases:
            if alias is not None:
                continue
            resource = self.pycore.find_module(name, current_folder=self.current_folder)
            if resource is None:
                continue
            absolute_name = importinfo.get_module_name(self.pycore, resource)
            if absolute_name != name:
                result.append((name, absolute_name))
        return result

    def visitFromImport(self, import_stmt, import_info):
        resource = import_info.get_imported_resource()
        if resource is None:
            return None
        absolute_name = importinfo.get_module_name(self.pycore, resource)
        if import_info.module_name != absolute_name:
            import_stmt.import_info = importinfo.FromImport(
                absolute_name, 0, import_info.names_and_aliases,
                self.current_folder, self.pycore)


class FilteringVisitor(ImportInfoVisitor):

    def __init__(self, pycore, can_select):
        self.to_be_absolute = []
        self.pycore = pycore
        self.can_select = self._transform_can_select(can_select)

    def _transform_can_select(self, can_select):
        def can_select_name_and_alias(name, alias):
            imported = name
            if alias is not None:
                imported = alias
            return can_select(imported)
        return can_select_name_and_alias

    def visitNormalImport(self, import_stmt, import_info):
        new_pairs = []
        for name, alias in import_info.names_and_aliases:
            if self.can_select(name, alias):
                new_pairs.append((name, alias))
        return importinfo.NormalImport(new_pairs)

    def visitFromImport(self, import_stmt, import_info):
        new_pairs = []
        if import_info.is_star_import():
            for name in import_info.get_imported_names():
                if self.can_select(name, None):
                    new_pairs.append(import_info.names_and_aliases[0])
                    break
        else:
            for name, alias in import_info.names_and_aliases:
                if self.can_select(name, alias):
                    new_pairs.append((name, alias))
        return importinfo.FromImport(
            import_info.module_name, import_info.level, new_pairs,
            import_info.current_folder, self.pycore)


class RemovingVisitor(ImportInfoVisitor):

    def __init__(self, pycore, can_select):
        self.to_be_absolute = []
        self.pycore = pycore
        self.filtering = FilteringVisitor(pycore, can_select)

    def dispatch(self, import_):
        result = self.filtering.dispatch(import_)
        if result is not None:
            import_.import_info = result


class AddingVisitor(ImportInfoVisitor):

    def __init__(self, pycore, import_info):
        self.pycore = pycore
        self.import_info = import_info

    def visitNormalImport(self, import_stmt, import_info):
        if not isinstance(self.import_info, import_info.__class__):
            return False
        # Adding ``import x`` and ``import x.y`` that results ``import x.y``
        if len(import_info.names_and_aliases) == len(self.import_info.names_and_aliases) == 1:
            imported1 = import_info.names_and_aliases[0]
            imported2 = self.import_info.names_and_aliases[0]
            if imported1[1] == imported2[1] == None:
                if imported1[0].startswith(imported2[0] + '.'):
                    return True
                if imported2[0].startswith(imported1[0] + '.'):
                    import_stmt.import_info = self.import_info
                    return True
        # Multiple imports using a single import statement is discouraged
        # so we won't bother adding them.
        if self.import_info._are_name_and_alias_lists_equal(
            import_info.names_and_aliases, self.import_info.names_and_aliases):
            return True

    def visitFromImport(self, import_stmt, import_info):
        if isinstance(self.import_info, import_info.__class__) and \
           import_info.module_name == self.import_info.module_name and \
           import_info.level == self.import_info.level:
            if import_info.is_star_import():
                return True
            if self.import_info.is_star_import():
                import_stmt.import_info = self.import_info
                return True
            new_pairs = list(import_info.names_and_aliases)
            for pair in self.import_info.names_and_aliases:
                if pair not in new_pairs:
                    new_pairs.append(pair)
            import_stmt.import_info = importinfo.FromImport(
                import_info.module_name, import_info.level, new_pairs,
                import_info.current_folder, import_info.pycore)
            return True


class ExpandStarsVisitor(ImportInfoVisitor):

    def __init__(self, pycore, can_select):
        self.pycore = pycore
        self.filtering = FilteringVisitor(pycore, can_select)

    def visitNormalImport(self, import_stmt, import_info):
        self.filtering.dispatch(import_stmt)

    def visitFromImport(self, import_stmt, import_info):
        if import_info.is_star_import():
            new_pairs = []
            for name in import_info.get_imported_names():
                new_pairs.append((name, None))
            new_import = importinfo.FromImport(
                import_info.module_name, import_info.level, new_pairs,
                import_info.current_folder, self.pycore)
            import_stmt.import_info = self.filtering.visitFromImport(None, new_import)
        else:
            self.filtering.dispatch(import_stmt)


class SelfImportVisitor(ImportInfoVisitor):

    def __init__(self, pycore, current_folder, resource):
        self.pycore = pycore
        self.current_folder = current_folder
        self.resource = resource
        self.to_be_fixed = set()
        self.to_be_renamed = set()

    def visitNormalImport(self, import_stmt, import_info):
        new_pairs = []
        for name, alias in import_info.names_and_aliases:
            resource = self.pycore.find_module(name, current_folder=self.current_folder)
            if resource is not None and resource == self.resource:
                imported = name
                if alias is not None:
                    imported = alias
                self.to_be_fixed.add(imported)
            else:
                new_pairs.append((name, alias))
        if not import_info._are_name_and_alias_lists_equal(
            new_pairs, import_info.names_and_aliases):
            import_stmt.import_info = importinfo.NormalImport(new_pairs)

    def visitFromImport(self, import_stmt, import_info):
        resource = import_info.get_imported_resource()
        if resource is None:
            return
        if resource == self.resource:
            self._importing_names_from_self(import_info, import_stmt)
            return
        pymodule = self.pycore.resource_to_pyobject(resource)
        new_pairs = []
        for name, alias in import_info.names_and_aliases:
            try:
                result = pymodule.get_attribute(name).get_object()
                if isinstance(result, pyobjects.PyModule) and \
                   result.get_resource() == self.resource:
                    imported = name
                    if alias is not None:
                        imported = alias
                    self.to_be_fixed.add(imported)
                else:
                    new_pairs.append((name, alias))
            except exceptions.AttributeNotFoundException:
                new_pairs.append((name, alias))
        if not import_info._are_name_and_alias_lists_equal(
            new_pairs, import_info.names_and_aliases):
            import_stmt.import_info = importinfo.FromImport(
                import_info.module_name, import_info.level, new_pairs,
                import_info.current_folder, self.pycore)

    def _importing_names_from_self(self, import_info, import_stmt):
        if not import_info.is_star_import():
            for name, alias in import_info.names_and_aliases:
                if alias is not None:
                    self.to_be_renamed.add((alias, name))
        import_stmt.empty_import()


class SortingVisitor(ImportInfoVisitor):

    def __init__(self, pycore, current_folder):
        self.pycore = pycore
        self.current_folder = current_folder
        self.standard = set()
        self.third_party = set()
        self.in_project = set()

    def visitNormalImport(self, import_stmt, import_info):
        if import_info.names_and_aliases:
            name, alias = import_info.names_and_aliases[0]
            resource = self.pycore.find_module(
                name, current_folder=self.current_folder)
            self._check_imported_resource(import_stmt, resource, name)

    def visitFromImport(self, import_stmt, import_info):
        resource = import_info.get_imported_resource()
        self._check_imported_resource(import_stmt, resource,
                                      import_info.module_name)

    def _check_imported_resource(self, import_stmt, resource, imported_name):
        if resource is not None and resource.project == self.pycore.project:
            self.in_project.add(import_stmt)
        else:
            if imported_name.split('.')[0] in SortingVisitor.standard_modules():
                self.standard.add(import_stmt)
            else:
                self.third_party.add(import_stmt)

    @classmethod
    def standard_modules(cls):
        if not hasattr(cls, '_standard_modules'):
            result = set(sys.builtin_module_names)
            lib_path = os.path.join(
                sys.prefix, 'lib%spython%s' % (os.sep, sys.version[:3]))
            for name in os.listdir(lib_path):
                path = os.path.join(lib_path, name)
                if os.path.isdir(path):
                    if '-' not in name:
                        result.add(name)
                else:
                    if name.endswith('.py'):
                        result.add(name[:-3])
            cls._standard_modules = result
        return cls._standard_modules


class LongImportVisitor(ImportInfoVisitor):

    def __init__(self, current_folder, pycore, maxdots, maxlength):
        self.maxdots = maxdots
        self.maxlength = maxlength
        self.to_be_renamed = set()
        self.current_folder = current_folder
        self.pycore = pycore
        self.new_imports = []

    def visitNormalImport(self, import_stmt, import_info):
        new_pairs = []
        for name, alias in import_info.names_and_aliases:
            if alias is None and self._is_long(name):
                self.to_be_renamed.add(name)
                last_dot = name.rindex('.')
                from_ = name[:last_dot]
                imported = name[last_dot + 1:]
                self.new_imports.append(
                    importinfo.FromImport(from_, 0, ((imported, None), ),
                                          self.current_folder, self.pycore))

    def _is_long(self, name):
        return name.count('.') > self.maxdots or \
               ('.' in name and len(name) > self.maxlength)
