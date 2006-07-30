import re
import keyword

import rope.codeanalyze
import rope.codeanalyze


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

    def get_suspected_region_after_change(self, text, change_start, change_end):
        """Returns the range that needs to be updated after a change"""
        start = min(change_start, len(text) - 1)
        start = self._get_line_start(text, start)
        start = max(0, start - 2)
        end = self._get_line_end(text, change_end)
        return (start, end)

    def _make_pattern(self):
        """Returns highlighting patterns"""

    def _get_line_start(self, text, index):
        current = index - 1
        while current > 0:
            if text[current] == '\n':
                return current + 1
            current -= 1
        return 0
    
    def _get_line_end(self, text, index):
        current = index
        while current < len(text):
            if text[current] == '\n':
                return current
            current += 1
        return len(text)
    
    def _get_pattern(self):
        if not self.pattern:
            self.pattern = self._make_pattern()
        return self.pattern
    

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
    
    def get_suspected_region_after_change(self, text, change_start, change_end):
        start, end = super(PythonHighlighting, self).\
                     get_suspected_region_after_change(text, change_start, change_end)
        line = text[start:end]
        if '"""' in line or "'''" in line:
            block_start = self._find_block_start(text, change_start)
            block_end = self._find_block_end(text, change_end)
            return (block_start, block_end)
        return (start, end)
    
    def _find_block_start(self, text, index):
        block_start_pattern = rope.codeanalyze.StatementRangeFinder.get_block_start_patterns()
        index = self._get_line_start(text, index)
        while index > 0:
            new_index = self._get_line_start(text, index - 1)
            line = text[new_index:index]
            if block_start_pattern.search(line) is not None:
                return new_index
            index = new_index
        return 0

    def _find_block_end(self, text, index):
        block_start_pattern = rope.codeanalyze.StatementRangeFinder.get_block_start_patterns()
        index = self._get_line_end(text, index)
        while index < len(text) - 1:
            new_index = self._get_line_end(text, index + 1)
            line = text[index:new_index]
            if block_start_pattern.search(line) is not None:
                return index
            index = new_index
        return len(text)


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

    def get_suspected_region_after_change(self, text, change_start, change_end):
        start = self._find_paragraph_start(text, change_start)
        end = self._find_paragraph_end(text, change_end)
        return (start, end)
    
    def _find_paragraph_start(self, text, index):
        index = self._get_line_start(text, index)
        while index > 0:
            new_index = self._get_line_start(text, index - 1)
            line = text[new_index:index]
            if line.strip() == '':
                return new_index
            index = new_index
        return 0

    def _find_paragraph_end(self, text, index):
        index = self._get_line_end(text, index)
        while index < len(text) - 1:
            new_index = self._get_line_end(text, index + 1)
            line = text[index:new_index]
            if line.strip() == '':
                return new_index
            index = new_index
        return len(text)
