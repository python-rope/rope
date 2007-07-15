from rope.base import change, taskhandle, builtins, exceptions
from rope.refactor import patchedast, similarfinder, sourceutils
from rope.refactor.importutils import module_imports


class Restructure(object):
    """A class to perform python restructurings"""

    def __init__(self, project, pattern, goal):
        self.pycore = project.pycore
        self.pattern = pattern
        self.goal = goal
        self.template = similarfinder.CodeTemplate(self.goal)

    def get_changes(self, checks={}, imports=[],
                    task_handle=taskhandle.NullTaskHandle()):
        """Get the changes needed by this restructuring
        
        `checks` is the checks that should hold for changing an
        occurrence.  `imports` are the imports that should be added
        modules that have at least one occurrence.

        """
        changes = change.ChangeSet('Restructuring <%s> to <%s>' %
                                   (self.pattern, self.goal))
        files = self.pycore.get_python_files()
        job_set = task_handle.create_job_set('Collecting Changes', len(files))
        for resource in files:
            job_set.started_job('Working on <%s>' % resource.path)
            pymodule = self.pycore.resource_to_pyobject(resource)
            finder = similarfinder.CheckingFinder(pymodule, checks)
            collector = sourceutils.ChangeCollector(pymodule.source_code)
            last_end = -1
            for match in finder.get_matches(self.pattern):
                start, end = match.get_region()
                if start < last_end:
                    raise exceptions.RefactoringError(
                        'Pattern matched recursively in <%s:%s>; Rope cannot'
                        ' handle recursive restructurings, yet.' %
                        (resource.path, start))
                last_end = end
                replacement = self._get_text(pymodule.source_code, match)
                replacement = self._auto_indent(pymodule, start, replacement)
                collector.add_change(start, end, replacement)
            result = collector.get_changed()
            if result is not None:
                imported_source = self._add_imports(resource, result, imports)
                changes.add_change(change.ChangeContents(resource,
                                                         imported_source))
            job_set.finished_job()
        return changes

    def _auto_indent(self, pymodule, offset, text):
        lineno = pymodule.lines.get_line_number(offset)
        indents = sourceutils.get_indents(pymodule.lines, lineno)
        result = []
        for index, line in enumerate(text.splitlines(True)):
            if index != 0 and line.strip():
                result.append(' ' * indents)
            result.append(line)
        return ''.join(result)

    def _add_imports(self, resource, source, imports):
        if not imports:
            return source
        import_infos = self._get_import_infos(resource, imports)
        pymodule = self.pycore.get_string_module(source, resource)
        imports = module_imports.ModuleImports(self.pycore, pymodule)
        for import_info in import_infos:
            imports.add_import(import_info)
        return imports.get_changed_source()

    def _get_import_infos(self, resource, imports):
        pymodule = self.pycore.get_string_module('\n'.join(imports),
                                                 resource)
        imports = module_imports.ModuleImports(self.pycore, pymodule)
        return [imports.import_info
                for imports in imports.get_import_statements()]

    def _get_text(self, source, match):
        mapping = {}
        for name in self.template.get_names():
            ast = match.get_ast(name)
            if ast is None:
                raise similarfinder.BadNameInCheckError(
                    'Unknown name <%s>' % name)
            start, end = patchedast.node_region(ast)
            mapping[name] = source[start:end]
        return self.template.substitute(mapping)


    def make_checks(self, string_checks):
        """Convert str to str dicts to str to PyObject dicts

        This function is here to ease writing a UI.

        """
        checks = {}
        for key, value in string_checks.items():
            is_pyname = not key.endswith('.object') and \
                        not key.endswith('.type')
            evaluated = self._evaluate(value, is_pyname=is_pyname)
            if evaluated is not None:
                checks[key] = evaluated
        return checks

    def _evaluate(self, code, is_pyname=True):
        attributes = code.split('.')
        pyname = None
        if attributes[0] in ('__builtin__', '__builtins__'):
            class _BuiltinsStub(object):
                def get_attribute(self, name):
                    return builtins.builtins[name]
            pyobject = _BuiltinsStub()
        else:
            pyobject = self.pycore.get_module(attributes[0])
        for attribute in attributes[1:]:
            pyname = pyobject.get_attribute(attribute)
            if pyname is None:
                return None
            pyobject = pyname.get_object()
        return pyname if is_pyname else pyobject
