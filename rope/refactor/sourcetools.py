

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
    
