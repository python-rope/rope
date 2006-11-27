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
        self.changes.sort()
        result = []
        last_changed = 0
        for change in self.changes:
            start, end, text = change
            result.append(self.text[last_changed:start] + text)
            last_changed = end
        if last_changed < len(self.text):
            result.append(self.text[last_changed:])
        return ''.join(result)


def get_indents(lines, lineno):
    indents = 0
    for c in lines.get_line(lineno):
        if c == ' ':
            indents += 1
        else:
            break
    return indents

def find_minimum_indents(source_code):
    result = 80
    lines = source_code.split('\n')
    for line in lines:
        if line.strip() == '':
            continue
        indents = 0
        for c in line:
            if c == ' ':
                indents += 1
            else:
                break
        result = min(result, indents)
    return result

def indent_lines(source_code, amount):
    if amount == 0:
        return source_code
    lines = source_code.splitlines(True)
    result = []
    for l in lines:
        if amount < 0 and len(l) > -amount:
            indents = 0
            while indents < len(l) and l[indents] == ' ':
                indents += 1
            result.append(l[-min(amount, indents):])
        elif amount > 0 and l.strip() != '':
            result.append(' ' * amount + l)
        else:
            result.append('\n')
    return ''.join(result)


def fix_indentation(code, new_indents):
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
    unindented_methods = indent_lines(methods, -find_minimum_indents(methods))
    indented_methods = indent_lines(unindented_methods,
                                    get_indents(lines, class_scope.get_start()) + 4)
    result = []
    result.append(source_code[:insertion_offset])
    result.append(indented_methods)
    result.append(source_code[insertion_offset:])
    return ''.join(result)
