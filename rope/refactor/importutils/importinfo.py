class ImportStatement(object):

    def __init__(self, import_info, start_line, end_line,
                 main_statement=None, blank_lines=0):
        self.start_line = start_line
        self.end_line = end_line
        self.main_statement = main_statement
        self._import_info = None
        self.import_info = import_info
        self._is_changed = False
        self.new_start = None
        self.blank_lines = blank_lines

    def _get_import_info(self):
        return self._import_info

    def _set_import_info(self, new_import):
        if new_import is not None and not new_import == self._import_info:
            self._is_changed = True
            self._import_info = new_import

    import_info = property(_get_import_info, _set_import_info)

    def get_import_statement(self):
        if self._is_changed or self.main_statement is None:
            return self.import_info.get_import_statement()
        else:
            return self.main_statement

    def empty_import(self):
        self.import_info = ImportInfo.get_empty_import()

    def move(self, lineno, blank_lines=0):
        self.new_start = lineno
        self.blank_lines = blank_lines

    def get_old_location(self):
        return self.start_line, self.end_line

    def get_new_start(self):
        return self.new_start

    def is_changed(self):
        return self._is_changed or (self.new_start is not None or
                                    self.new_start != self.start_line)

    def accept(self, visitor):
        return visitor.dispatch(self)


class ImportInfo(object):

    def get_imported_primaries(self):
        pass

    def get_imported_names(self):
        return [primary.split('.')[0]
                for primary in self.get_imported_primaries()]

    def get_import_statement(self):
        pass

    def is_empty(self):
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

    def is_empty(self):
        return len(self.names_and_aliases) == 0


class FromImport(ImportInfo):

    def __init__(self, module_name, level, names_and_aliases, current_folder, pycore):
        self.module_name = module_name
        self.level = level
        self.names_and_aliases = names_and_aliases
        self.current_folder = current_folder
        self.pycore = pycore

    def get_imported_primaries(self):
        if self.names_and_aliases[0][0] == '*':
            module = self.get_imported_module()
            return [name for name in module.get_attributes().keys()
                    if not name.startswith('_')]
        result = []
        for name, alias in self.names_and_aliases:
            if alias:
                result.append(alias)
            else:
                result.append(name)
        return result

    def get_imported_module(self):
        if self.level == 0:
            return self.pycore.get_module(self.module_name,
                                          self.current_folder)
        else:
            return self.pycore.get_relative_module(
                self.module_name, self.current_folder, self.level)

    def get_imported_resource(self):
        if self.level == 0:
            return self.pycore.find_module(self.module_name,
                                           current_folder=self.current_folder)
        else:
            return self.pycore.find_relative_module(
                self.module_name, self.current_folder, self.level)

    def get_import_statement(self):
        result = 'from ' + '.' * self.level + self.module_name + ' import '
        for name, alias in self.names_and_aliases:
            result += name
            if alias:
                result += ' as ' + alias
            result += ', '
        return result[:-2]

    def is_empty(self):
        return len(self.names_and_aliases) == 0

    def is_star_import(self):
        return len(self.names_and_aliases) > 0 and self.names_and_aliases[0][0] == '*'


class EmptyImport(ImportInfo):

    names_and_aliases = []

    def is_empty(self):
        return True

    def get_imported_primaries(self):
        return []


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
