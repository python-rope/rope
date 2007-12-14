from rope.base import ast, codeanalyze


class ChangeCollector(object):

    def __init__(self, text):
        self.text = text
        self.changes = []

    def add_change(self, start, end, new_text=None):
        if new_text is None:
            new_text = self.text[start:end]
        self.changes.append((start, end, new_text))

    def get_changed(self):
        if not self.changes:
            return None
        def compare_changes(change1, change2):
            return cmp(change1[:2], change2[:2])
        self.changes.sort(compare_changes)
        pieces = []
        last_changed = 0
        for change in self.changes:
            start, end, text = change
            pieces.append(self.text[last_changed:start] + text)
            last_changed = end
        if last_changed < len(self.text):
            pieces.append(self.text[last_changed:])
        result = ''.join(pieces)
        if result != self.text:
            return result


def get_indents(lines, lineno):
    return codeanalyze.count_line_indents(lines.get_line(lineno))


def find_minimum_indents(source_code):
    result = 80
    lines = source_code.split('\n')
    for line in lines:
        if line.strip() == '':
            continue
        result = min(result, codeanalyze.count_line_indents(line))
    return result


def indent_lines(source_code, amount):
    if amount == 0:
        return source_code
    lines = source_code.splitlines(True)
    result = []
    for l in lines:
        if l.strip() == '':
            result.append('\n')
            continue
        if amount < 0:
            indents = codeanalyze.count_line_indents(l)
            result.append(max(0, indents + amount) * ' ' + l.lstrip())
        else:
            result.append(' ' * amount + l)
    return ''.join(result)


def fix_indentation(code, new_indents):
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
    methods = '\n\n' + '\n\n'.join(methods_sources)
    indented_methods = fix_indentation(
        methods, get_indents(lines, class_scope.get_start()) +
        get_indent(pymodule.pycore))
    result = []
    result.append(source_code[:insertion_offset])
    result.append(indented_methods)
    result.append(source_code[insertion_offset:])
    return ''.join(result)


def get_body(pyfunction):
    """Return unindented function body"""
    scope = pyfunction.get_scope()
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

    end_line = codeanalyze.LogicalLineFinder(lines).\
               get_logical_line_in(scope.get_end())[1]
    start = lines.get_line_start(start_line)
    end = min(lines.get_line_end(end_line) + 1, len(pymodule.source_code))
    return start, end


def get_indent(pycore):
    project = pycore.project
    return project.get_prefs().get('indent_size', 4)
