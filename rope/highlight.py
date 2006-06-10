import re
import keyword


class Highlighting(object):
    def getStyles(self):
        '''Returns the dictionary of styles used in highlighting texts by this highlighting'''

    def highlights(self, startIndex, endIndex):
        '''Generates highlighted ranges as (start, end, style) tuples'''


class HighlightingStyle(object):
    def __init__(self, color=None, bold=None, italic=None, strikethrough=None, underline=None):
        self.color = color
        self.bold = bold
        self.italic = italic
        self.strikethrough = strikethrough
        self.underline = underline


class PythonHighlighting(Highlighting):
    def __init__(self, editor):
        self.editor = editor
        kw = r"\b" + PythonHighlighting.any("keyword", keyword.kwlist) + r"\b"
        import __builtin__
        builtinlist = [str(name) for name in dir(__builtin__)
                       if not name.startswith('_')]
        builtin = r"([^.'\"\\]\b|^)" + PythonHighlighting.any("builtin", builtinlist) + r"\b"
        comment = PythonHighlighting.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        string = PythonHighlighting.any("string", [sq3string, dq3string, sqstring, dqstring])
        self.pattern = re.compile(kw + "|" + builtin + '|' + comment + "|" + string)

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"

    def getStyles(self):
        return {'keyword': HighlightingStyle(color='blue', bold=True),
                'string' : HighlightingStyle(color='#004080'),
                'comment' : HighlightingStyle(color='#008000', italic=True),
                'builtin' : HighlightingStyle(color='#908080'),
                'definition' : HighlightingStyle(color='purple', bold=True)}

    def highlights(self, start, end):
        text = self.editor.get(start, end)
        for match in self.pattern.finditer(text):
            for key, value in match.groupdict().items():
                if value:
                    a, b = match.span(key)
                    yield (self.editor.get_relative(start, a),
                           self.editor.get_relative(start, b), key)
                    if value in ("def", "class"):
                        idprog = re.compile(r"\s+(\w+)", re.S)
                        m1 = idprog.match(text, b)
                        if m1:
                            a, b = m1.span(1)
                            yield (self.editor.get_relative(start, a),
                                   self.editor.get_relative(start, b), 'definition')


class NoHighlighting(Highlighting):
    def getStyles(self):
        return {}

    def highlights(self, startIndex, endIndex):
        if False:
            yield None

