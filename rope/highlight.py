import re
import keyword


class Highlighting(object):
    
    def __init__(self):
        self.pattern = None

    def get_styles(self):
        """Returns the dictionary of styles used in highlighting texts by this highlighting"""

    def highlights(self, text, start, end):
        """Generates highlighted ranges as (start, end, style) tuples"""
        if end == None:
            end = len(text)
        for match in self._get_pattern().finditer(text[start:end]):
            for key, value in match.groupdict().items():
                if value:
                    a, b = match.span(key)
#                    print a, b, key
                    yield (start + a, start + b, key)
    
    def _get_pattern(self):
        if not self.pattern:
            self.pattern = self._make_pattern()
        return self.pattern
    
    def _make_pattern(self):
        """Returns highlighting patterns"""


class HighlightingStyle(object):

    def __init__(self, color=None, bold=None, italic=None, strikethrough=None, underline=None):
        self.color = color
        self.bold = bold
        self.italic = italic
        self.strikethrough = strikethrough
        self.underline = underline


class PythonHighlighting(Highlighting):

    @staticmethod
    def any(name, list):
        return "(?P<%s>" % name + "|".join(list) + ")"
    
    def _make_pattern(self):
        keyword_pattern = r"\b" + PythonHighlighting.any("keyword", keyword.kwlist) + r"\b"
        import __builtin__
        builtinlist = [str(name) for name in dir(__builtin__)
                       if not name.startswith('_')]
        builtin_pattern = r"([^.'\"\\]\b|^)" + \
                          PythonHighlighting.any("builtin", builtinlist) + r"\b"
        comment_pattern = PythonHighlighting.any("comment", [r"#[^\n]*"])
        sqstring = r"(\b[rR])?'[^'\\\n]*(\\.[^'\\\n]*)*'?"
        dqstring = r'(\b[rR])?"[^"\\\n]*(\\.[^"\\\n]*)*"?'
        sq3string = r"(\b[rR])?'''[^'\\]*((\\.|'(?!''))[^'\\]*)*(''')?"
        dq3string = r'(\b[rR])?"""[^"\\]*((\\.|"(?!""))[^"\\]*)*(""")?'
        string_pattern = PythonHighlighting.any("string", [sq3string, dq3string, sqstring, dqstring])
        definition_pattern = r'^\s*(?P<defkeyword>def|class)\s+(?P<definition>\w+)'
        all_patterns = definition_pattern + '|' + keyword_pattern + '|' + \
                       builtin_pattern + '|' + comment_pattern + '|' + string_pattern
        return re.compile(all_patterns, re.S | re.M)

    def get_styles(self):
        return {'keyword': HighlightingStyle(color='blue', bold=True),
                'defkeyword': HighlightingStyle(color='blue', bold=True),
                'string': HighlightingStyle(color='#004080'),
                'comment': HighlightingStyle(color='#008000', italic=True),
                'builtin': HighlightingStyle(color='#908080'),
                'definition': HighlightingStyle(color='purple', bold=True)}


class NoHighlighting(Highlighting):

    def get_styles(self):
        return {}

    def highlights(self, editor, startIndex, endIndex):
        if False:
            yield None


class ReSTHighlighting(Highlighting):
    
    def _make_pattern(self):
        title_pattern = '(?P<overline>^(([^\\w\\s\\d]+)\n))?' + \
                        '(?P<title>.+)\n' + \
                        '(?P<underline>(\\1|[^\\w\\s\\d])+)$'
        listsign_pattern = '^\\s*(?P<listsign>[*+-]|\\d*\\.)(?=\\s+.+$)'
        directive_pattern = '(?P<directive>\\.\\. \\w+.+::)'
        emphasis_pattern = '(?P<emphasis>\\*[^*\n]+\\*)'
        strongemphasis_pattern = '(?P<strongemphasis>\\*\\*[^*\n]+\\*\\*)'
        literal_pattern = '(?P<literal>``([^`]|`[^`])+``)'
        interpreted_pattern = '(?P<interpreted>`[^`]+`)(?P<role>:\\w+:)?'
        hyperlink_target_pattern = '(?P<hyperlink_target>\\w+://[^\\s]+)'
        hyperlink_pattern = '(?P<hyperlink>[\\w]+_|`[^`]+`_)\\b'
        hyperlink_definition_pattern = '(?P<hyperlink_definition>\\.\\. _([^`\n:]|`.+`)+:)'
        field_pattern = '^\\s*(?P<field>:[^\n:]+:)'
        escaped_pattern = '(?P<escaped>\\\\.)'
        all_patterns = literal_pattern + '|' + escaped_pattern + '|' + hyperlink_pattern + '|' + \
                       interpreted_pattern + '|' + \
                       title_pattern + '|' + listsign_pattern + '|' + \
                       directive_pattern + '|' + emphasis_pattern + '|' + \
                       strongemphasis_pattern + '|' + \
                       hyperlink_target_pattern + '|' + field_pattern + '|' + \
                       hyperlink_definition_pattern
        return re.compile(all_patterns, re.M)
    
    def get_styles(self):
        return {'title' : HighlightingStyle(color='purple', bold=True),
                'underline' : HighlightingStyle(color='blue', bold=True),
                'overline' : HighlightingStyle(color='blue', bold=True),
                'listsign' : HighlightingStyle(color='blue', bold=True),
                'directive' : HighlightingStyle(color='#00AAAA'),
                'emphasis' : HighlightingStyle(color='#000033', italic=True),
                'strongemphasis' : HighlightingStyle(color='#330000', bold=True),
                'literal' : HighlightingStyle(color='#605050'),
                'interpreted' : HighlightingStyle(color='#208820'),
                'role' : HighlightingStyle(color='#409000'),
                'hyperlink_target' : HighlightingStyle(color='#002299'),
                'hyperlink' : HighlightingStyle(color='#2200FF'),
                'hyperlink_definition' : HighlightingStyle(color='#2222FF'),
                'field' : HighlightingStyle(color='#005555'),
                'escaped' : HighlightingStyle()}

