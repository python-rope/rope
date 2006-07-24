import re
import keyword


class Highlighting(object):

    def get_styles(self):
        """Returns the dictionary of styles used in highlighting texts by this highlighting"""

    def highlights(self, editor, startIndex, endIndex):
        """Generates highlighted ranges as (start, end, style) tuples"""


class HighlightingStyle(object):

    def __init__(self, color=None, bold=None, italic=None, strikethrough=None, underline=None):
        self.color = color
        self.bold = bold
        self.italic = italic
        self.strikethrough = strikethrough
        self.underline = underline


class PythonHighlighting(Highlighting):

    def __init__(self):
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
        self.pattern = re.compile(kw + "|" + builtin + '|' + comment + "|" + string, re.S)

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"

    def get_styles(self):
        return {'keyword': HighlightingStyle(color='blue', bold=True),
                'string' : HighlightingStyle(color='#004080'),
                'comment' : HighlightingStyle(color='#008000', italic=True),
                'builtin' : HighlightingStyle(color='#908080'),
                'definition' : HighlightingStyle(color='purple', bold=True)}

    def highlights(self, editor, start, end):
        text = editor.get(start, end)
        for match in self.pattern.finditer(text):
            for key, value in match.groupdict().items():
                if value:
                    a, b = match.span(key)
                    yield (editor.get_relative(start, a),
                           editor.get_relative(start, b), key)
                    if value in ("def", "class"):
                        idprog = re.compile(r"\s+(\w+)", re.S)
                        m1 = idprog.match(text, b)
                        if m1:
                            a, b = m1.span(1)
                            yield (editor.get_relative(start, a),
                                   editor.get_relative(start, b), 'definition')


class NoHighlighting(Highlighting):

    def get_styles(self):
        return {}

    def highlights(self, editor, startIndex, endIndex):
        if False:
            yield None

class ReSTHighlighting(Highlighting):
    
    def __init__(self):
        self.pattern = None
        
    def _get_pattern(self):
        if not self.pattern:
            self.pattern = self._make_pattern()
        return self.pattern
    
    def _make_pattern(self):
        title_pattern = '(?P<overline>^(([^\\w\\s\\d]+)\n))?' + \
                        '(?P<title>.+)\n' + \
                        '(?P<underline>(\\1|[^\\w\\s\\d])+)$'
        listsign_pattern = '^\\s*(?P<listsign>[*+-])\\s+.+$'
        directive_pattern = '(?P<directive>\\.\\. \\w+.+::)(\\s+.+)?'
        emphasis_pattern = '(?P<emphasis>\\*[^*\n]+\\*)'
        strongemphasis_pattern = '(?P<strongemphasis>\\*\\*[^*\n]+\\*\\*)'
        literal_pattern = '(?P<literal>``[^`]+``)'
        interpreted_pattern = '(?P<interpreted>`[^`]+`)(?P<role>:\\w+:)?'
        hyperlink_target_pattern = '(?P<hyperlink_target>\\w+://[^\\s]+)'
        hyperlink_pattern = '(?P<hyperlink>[^\\s]+_|`.+`_)'
        hyperlink_definition_pattern = '(?P<hyperlink_definition>\\.\\. _[^\\s:]+:)'
        all_patterns = title_pattern + '|' + listsign_pattern + '|' + \
                       directive_pattern + '|' + emphasis_pattern + '|' +\
                       strongemphasis_pattern + '|' + literal_pattern + '|' + \
                       hyperlink_pattern + '|' + hyperlink_target_pattern + '|' + \
                       interpreted_pattern + '|' + hyperlink_definition_pattern
        return re.compile(all_patterns, re.M)
    
    def get_styles(self):
        return {'title' : HighlightingStyle(color='purple', bold=True),
                'underline' : HighlightingStyle(color='green', bold=True),
                'overline' : HighlightingStyle(color='green', bold=True),
                'listsign' : HighlightingStyle(color='blue', bold=True),
                'directive' : HighlightingStyle(color='blue', bold=True),
                'emphasis' : HighlightingStyle(italic=True),
                'strongemphasis' : HighlightingStyle(bold=True),
                'literal' : HighlightingStyle(color='#908080'),
                'interpreted' : HighlightingStyle(color='#008000'),
                'role' : HighlightingStyle(color='blue'),
                'hyperlink_target' : HighlightingStyle(color='blue'),
                'hyperlink' : HighlightingStyle(color='blue'),
                'hyperlink_definition' : HighlightingStyle(color='blue')}

    def highlights(self, editor, start, end):
        text = editor.get(start, end)
        for match in self._get_pattern().finditer(text):
            for key, value in match.groupdict().items():
                if value:
                    a, b = match.span(key)
                    yield (editor.get_relative(start, a),
                           editor.get_relative(start, b), key)

