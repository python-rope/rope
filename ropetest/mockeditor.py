from rope.editor import TextEditor, TextIndex, LineEditor

class MockLineEditor(LineEditor):
    def __init__(self, editor):
        self.editor = editor

    def get_line(self, number):
        return self.editor.get_text().split('\n')[number - 1]

    def set_line(self, number, string):
        lines = self.editor.get_text().split('\n')
        lines[number - 1] = string
        self.editor.set_text('\n'.join(lines))


class MockEditor(TextEditor):
    '''A mock editor for testing editing commands'''
    def __init__(self):
        self.content = ''
        self.insertIndex = MockTextIndex(self, 0)
        self.status_bar_manager = None
    
    def get_text(self):
        return self.content
    
    def set_text(self, text):
        self.content = text

    def get_start(self):
        return MockTextIndex(self, 0)

    def get_end(self):
        return MockTextIndex(self, len(self.content))

    def get_insert(self):
        return self.insertIndex

    def get_relative(self, index, offset):
        newIndex = index._getIndex() + offset
        if newIndex < 0:
            newIndex = 0
        if newIndex > len(self.content):
            newIndex = len(self.content)
        return MockTextIndex(self, newIndex)

    def get_index(self, offset):
        return self.get_relative(self.get_start(), offset)

    def set_insert(self, index):
        self.insertIndex = index

    def get(self, start = None, end = None):
        sindex = start
        eindex = end
        if sindex is None:
            sindex = self.get_insert()
        if eindex is None:
            eindex = self.get_relative(sindex, 1)
        if sindex == self.get_end():
            return ''
        else:
            return self.content[sindex._getIndex() : eindex._getIndex()]

    def insert(self, textIndex, text):
        self.content = self.content[0 : textIndex._getIndex()] \
            + text + self.content[textIndex._getIndex() :]

    def delete(self, start = None, end = None):
        startIndex = self.insertIndex._getIndex()
        if start is not None:
            startIndex = start._getIndex()
        endIndex = startIndex + 1
        if end is not None:
            endIndex = end._getIndex()
        self.content = self.content[:startIndex] + self.content[endIndex:]

    def _getNextWordIndex(self):
        current = self.insertIndex._getIndex()
        while current < len(self.content) - 1 and not self.content[current].isalnum():
            current += 1
        while current < len(self.content) - 1:
            current += 1
            if (not self.content[current].isalnum()):
                break
        return current

    def next_word(self):
        self.insertIndex = MockTextIndex(self, self._getNextWordIndex())

    def delete_next_word(self):
        self.content = self.content[0 : self.insertIndex._getIndex()] + \
                       self.content[self._getNextWordIndex() :]

    def _getPrevWordIndex(self):
        current = self.insertIndex._getIndex()
        while current > 0 and not self.content[current - 1].isalnum():
            current -= 1
        while current > 0 and self.content[current - 1].isalnum():
            current -= 1
        return current

    def prev_word(self):
        self.insertIndex = MockTextIndex(self, self._getPrevWordIndex())

    def delete_prev_word(self):
        self.content = self.content[0 : self._getPrevWordIndex()] + \
                       self.content[self.insertIndex._getIndex() :]

    def goto_start(self):
        self.set_insert(self.get_start())

    def goto_end(self):
        self.set_insert(self.get_end())

    def set_highlighting(self, highlighting):
        pass

    def highlight_match(self, match):
        if not match:
            return
        if match.side == 'right':
            self.insertIndex = match.end
        else:
            self.insertIndex = match.start

    def search(self, keyword, start, case=True, forwards=True):
        content = self.content
        if not case:
            content = self.content.lower()
            keyword = keyword.lower()
        try:
            if forwards:
                found = content.index(keyword, start._getIndex())
            else:
                found = content.rindex(keyword, 0, start._getIndex())
            return MockTextIndex(self, found)
        except ValueError:
            return None

    def line_editor(self):
        return MockLineEditor(self)


class MockTextIndex(TextIndex):
    def __init__(self, editor, index):
        self.editor = editor
        self.index = index

    def __cmp__(self, index):
        assert self.editor == index.editor
        return self.index - index.index
    
    def _getIndex(self):
        return self.index

    def __str__(self):
        return '<%s, %s>' % (self.__class__.__name__, str(self.index))

