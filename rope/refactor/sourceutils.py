from rope.base import builtins, codeanalyze, exceptions
from rope.refactor import occurrences


def get_indents(lines, lineno):
    return codeanalyze.count_line_indents(lines.get_line(lineno))


def find_minimum_indents(source_code):
    result = 80
    lines = source_code.split("\n")
    for line in lines:
        if line.strip() == "":
            continue
        result = min(result, codeanalyze.count_line_indents(line))
    return result


def indent_lines(source_code, amount):
    if amount == 0:
        return source_code
    lines = source_code.splitlines(True)
    result = []
    for line in lines:
        if line.strip() == "":
            result.append("\n")
            continue
        if amount < 0:
            indents = codeanalyze.count_line_indents(line)
            result.append(max(0, indents + amount) * " " + line.lstrip())
        else:
            result.append(" " * amount + line)
    return "".join(result)


def fix_indentation(code: str, new_indents: int) -> str:
    """Change the indentation of `code` to `new_indents`"""
    min_indents = find_minimum_indents(code)
    return indent_lines(code, new_indents - min_indents)


def add_methods(pymodule, class_scope, methods_sources):
    source_code = pymodule.source_code
    lines = pymodule.lines
    insertion_line = class_scope.get_end()
    if class_scope.get_scopes():
        insertion_line = class_scope.get_scopes()[-1].get_end()
    insertion_offset = lines.get_line_end(insertion_line)
    methods = "\n\n" + "\n\n".join(methods_sources)
    indented_methods = fix_indentation(
        methods,
        get_indents(lines, class_scope.get_start())
        + get_indent(pymodule.pycore.project),
    )
    result = []
    result.append(source_code[:insertion_offset])
    result.append(indented_methods)
    result.append(source_code[insertion_offset:])
    return "".join(result)


def get_body(pyfunction):
    """Return unindented function body"""
    # FIXME scope = pyfunction.get_scope()
    pymodule = pyfunction.get_module()
    start, end = get_body_region(pyfunction)
    return fix_indentation(pymodule.source_code[start:end], 0)


def get_body_region(defined):
    """Return the start and end offsets of function body"""
    scope = defined.get_scope()
    pymodule = defined.get_module()
    lines = pymodule.lines
    node = defined.get_ast()
    start_line = node.lineno
    if defined.get_doc() is None:
        start_line = node.body[0].lineno
    elif len(node.body) > 1:
        start_line = node.body[1].lineno
    start = lines.get_line_start(start_line)
    scope_start = pymodule.logical_lines.logical_line_in(scope.start)
    if scope_start[1] >= start_line:
        # a one-liner!
        # XXX: what if colon appears in a string
        start = pymodule.source_code.index(":", start) + 1
        while pymodule.source_code[start].isspace():
            start += 1
    end = min(lines.get_line_end(scope.end) + 1, len(pymodule.source_code))
    return start, end


def get_indent(project):
    return project.prefs.get("indent_size", 4)


def check_new_name(pymodule, scope, name, replaced=None):
    """Raise `RefactoringError` if `name` is already in use in `scope`

    `name` is in use if it is defined in `scope`, or if defining it in
    `scope` would shadow a name that is used there.  Uses of `replaced`
    are ignored, because the refactoring replaces them with `name`.
    """
    pyname = scope.get_names().get(name)
    if pyname is not None and not isinstance(pyname, builtins.BuiltinName):
        raise exceptions.RefactoringError(
            f"Invalid refactoring target name. '{name}' is already defined"
            " in the target scope."
        )
    # Methods do not see the names defined in their class body
    if scope.get_kind() == "Class":
        return
    pyname = scope.lookup(name)
    if pyname is None or occurrences.same_pyname(replaced, pyname):
        return
    start = pymodule.lines.get_line_start(scope.get_body_start())
    end = pymodule.lines.get_line_end(scope.get_end())
    finder = occurrences.create_finder(
        pymodule.pycore.project, name, pyname, keywords=False
    )
    for occurrence in finder.find_occurrences(pymodule=pymodule):
        if start <= occurrence.offset <= end:
            raise exceptions.RefactoringError(
                f"Invalid refactoring target name. '{name}' would shadow"
                " a name used in the target scope."
            )
