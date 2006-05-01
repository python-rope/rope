from Tkinter import *
from tkFont import *
from ScrolledText import ScrolledText

import rope.highlight
import rope.searching
import rope.indenter


class TextEditor(object):
    '''A class representing a text editor'''
    def get_text(self):
        pass
    
    def set_text(self, text):
        pass

    def get_start(self):
        pass
    
    def get_insert(self):
        pass

    def get_end(self):
        pass
    
    def get_relative(self, base_index, offset):
        pass
    
    def get_index(self, offset):
        pass
    
    def set_insert(self, index):
        pass

    def get(self, start=None, end=None):
        pass
    
    def insert(self, index, text):
        pass

    def delete(self, start=None, end=None):
        pass

    def nextWord(self):
        pass

    def prevWord(self):
        pass

    def deleteNextWord(self):
        pass

    def deletePrevWord(self):
        pass

    def goToTheStart(self):
        pass

    def goToTheEnd(self):
        pass

    def set_highlighting(self, highlighting):
        pass

    def highlight_match(self, match):
        pass

    def search(self, keyword, start, case=True, forwards=True):
        pass

    def undo_separator(self):
        pass

class TextIndex(object):
    '''A class for pointing to a position in a text'''


class GraphicalEditor(TextEditor):
    def __init__(self, parent):
        self.text = ScrolledText(parent, bg='white', 
                         font=Font(family='Typewriter', size=14), 
                         undo=True, maxundo=20, highlightcolor='#99A')
        self.searcher = rope.searching.Searcher(self)
        self._bind_keys()
        self._initialize_highlighting()
        self.highlighting = rope.highlight.NoHighlighting()
        self.indenter = rope.indenter.NullIndenter()

    def _initialize_highlighting(self):
        def colorize(event):
            start = 'insert linestart-2c'
            end = 'insert lineend'
            start_tags = self.text.tag_names(start)
            if start_tags:
                tag = start_tags[0]
                range = self.text.tag_prevrange(tag, start + '+1c')
                if self.text.compare(range[0], '<', start):
                    start = range[0]
                if self.text.compare(range[1], '>', end):
                    end = range[1]
            end_tags = self.text.tag_names(end)
            if end_tags:
                tag = end_tags[0]
                range = self.text.tag_prevrange(tag, end + '+1c')
                if self.text.compare(range[1], '>', end):
                    end = range[1]
            self._highlight_range(start, end)
        self.text.bind('<Any-KeyRelease>', colorize, '+')

    def _highlight_range(self, startIndex, endIndex):
        for style in self.highlighting.getStyles().keys():
            self.text.tag_remove(style, startIndex, endIndex)
        for start, end, kind in self.highlighting.highlights(GraphicalTextIndex(self, startIndex),
                                                             GraphicalTextIndex(self, endIndex)):
            self.text.tag_add(kind, start._getIndex(), end._getIndex())

    def _bind_keys(self):
        self.text.bind('<Alt-f>', lambda event: self.nextWord())
        self.text.bind('<Alt-b>', lambda event: self.prevWord())
        self.text.bind('<Alt-d>', lambda event: self.deleteNextWord())
        def deletePrevWordListener(event):
            self.deletePrevWord()
            return 'break'
        self.text.bind('<Alt-BackSpace>', deletePrevWordListener)
        def doUndo(event):
            self.undo()
            return 'break'
        def doRedo(event):
            self.redo()
            return 'break'
        self.text.bind('<Control-x><u>', doUndo)
        self.text.bind('<Control-x><r>', doRedo)
        def doGoToTheStart(event):
            self.goToTheStart()
            self.text.see(INSERT)
        def doGoToTheEnd(event):
            self.goToTheEnd()
            self.text.see(INSERT)
        self.text.bind('<Alt-less>', doGoToTheStart)
        self.text.bind('<Alt-KeyPress->>', doGoToTheEnd)
        def doSetMark(event):
            self.setMark()
            return 'break'
        self.text.bind('<Control-space>', doSetMark)
        def doCopy(event):
            self.copyRegion()
            return 'break'
        self.text.bind('<Alt-w>', doCopy)
        def doCut(event):
            self.cutRegion()
            return 'break'
        self.text.bind('<Control-w>', doCut)
        def doPaste(event):
            self.paste()
            return 'break'
        self.text.bind('<Control-y>', doPaste)
        def escape(event):
            self.clearMark()
            if self.get_searcher().is_searching():
                self.get_searcher().cancel_searching()
        self.text.bind('<Control-g>', escape)
        def do_swap_mark_and_insert(event):
            self.swapMarkAndInsert()
            return 'break'
        self.text.bind('<Control-x><Control-x>', do_swap_mark_and_insert)
        def goNextPage(event):
            self.nextPage()
            return 'break'
        self.text.bind('<Control-v>', goNextPage)
        def goPrevPage(event):
            self.prevPage()
            return 'break'
        self.text.bind('<Alt-v>', goPrevPage)
        def doInsertTab(event):
            self.insertTab()
            return 'break'
        def indent_line(event):
            self.indenter.indent_line(self.get_insert())
            return 'break'
        self.text.bind('<Control-i>', indent_line)
        self.text.bind('<Tab>', doInsertTab)
        def return_handler(event):
            if self.searcher.is_searching():
                self.searcher.end_searching()
                return 'break'
            self.text.insert(INSERT, '\n')
            self.indenter.indent_line(self.get_insert())
            self.text.see(INSERT)
            return 'break'
        def backspace(event):
            if self.searcher.is_searching():
                self.searcher.shorten_keyword()
                return 'break'
            line_starting = self.text.get('insert linestart', 'insert')
            current_char = self.text.get(INSERT)
            if line_starting.isspace() and (not current_char.isspace() 
                                            or current_char == '' or current_char == '\n'):
                self.indenter.deindent(self.get_insert())
                return 'break'
        self.text.bind('<Return>', return_handler)
        self.text.event_add('<<ForwardSearch>>', '<Control-s>')
        self.text.event_add('<<BackwardSearch>>', '<Control-r>')
        self.text.bind('<<ForwardSearch>>',
                       lambda event: self._search_event(True), '+')
        self.text.bind('<<BackwardSearch>>',
                       lambda event: self._search_event(False))
        self.text.bind('<Any-KeyPress>', self._search_handler)
        self.text.bind('<BackSpace>', backspace, '+')


    def get_text(self):
        return self.text.get('1.0', 'end-1c')
    
    def set_text(self, text):
        self.text.delete('1.0', END)
        self.text.insert('1.0', text)
        self.text.mark_set(INSERT, '1.0')
        self._highlight_range('0.0', 'end')
        self.text.edit_reset()

    def get_start(self):
        return GraphicalTextIndex(self, '1.0')

    def get_insert(self):
        return GraphicalTextIndex(self, INSERT)

    def get_end(self):
        return GraphicalTextIndex(self, END)

    def get_relative(self, textIndex, offset):
        return GraphicalTextIndex(self, self._go(textIndex._getIndex(), offset))

    def get_index(self, offset):
        return GraphicalTextIndex(self, self._go('1.0', offset))

    def _go(self, fromIndex, count):
        if count >= 0:
            return fromIndex + ('+%dc' % count)
        else:
            return fromIndex + ('%dc' % count)

    def _get_line_from_index(self, index):
        return int(self.text.index(index).split('.')[0])
        
    def _get_column_from_index(self, index):
        return int(self.text.index(index).split('.')[1])
    
    def set_insert(self, textIndex):
        self.text.mark_set(INSERT, textIndex._getIndex())

    def get(self, start=None, end=None):
        startIndex = INSERT
        endIndex = None
        if start is not None:
            startIndex = start._getIndex()
            if start == self.get_end():
                return ''
        if end is not None:
            endIndex = end._getIndex()
        return self.text.get(startIndex, endIndex)
    
    def insert(self, textIndex, text):
        self.text.insert(textIndex._getIndex(), text)

    def delete(self, start = None, end = None):
        startIndex = INSERT
        if start is not None:
            startIndex = start._getIndex()
            if start == self.get_end():
                return
        endIndex = None
        if end is not None:
            endIndex = end._getIndex()
        self.text.delete(startIndex, endIndex)
        
    def _get_next_word_index(self):
        result = INSERT
        while self.text.compare(result, '!=', 'end-1c') and \
              not self.text.get(result)[0].isalnum():
            result = self.text.index(result + '+1c')
        return result + ' wordend'

    def nextWord(self):
        self.text.mark_set(INSERT, self._get_next_word_index())
        self.text.see(INSERT)

    def _get_prev_word_index(self):
        result = INSERT
        while not self.text.compare(result, '==', '1.0') and \
              not self.text.get(result + '-1c')[0].isalnum():
            result = self.text.index(result + '-1c')
        return result + '-1c wordstart'

    def prevWord(self):
        self.text.mark_set(INSERT, self._get_prev_word_index())
        self.text.see(INSERT)

    def deleteNextWord(self):
        self.text.delete(INSERT, self._get_next_word_index())

    def deletePrevWord(self):
        self.text.delete(self._get_prev_word_index(), INSERT)

    def getWidget(self):
        return self.text

    def undo_separator(self):
        self.text.edit_separator()

    def undo(self):
        try:
            self.text.edit_undo()
        except TclError:
            pass

    def redo(self):
        try:
            self.text.edit_redo()
        except TclError:
            pass

    def goToTheStart(self):
        self.set_insert(self.get_start())
    
    def goToTheEnd(self):
        self.set_insert(self.get_end())

    def generate_event(self, event):
        self.text.event_generate(event)

    def setMark(self):
        self.text.mark_set('mark', INSERT)

    def clearMark(self):
        self.text.mark_unset('mark')

    def _selectRegion(self):
        start = 'mark'
        end = INSERT
        if self.text.compare(start, '>', end):
            start, end = end, start
        self.text.tag_add(SEL, start, end)

    def copyRegion(self):
        try:
            self._selectRegion()
            self.text.event_generate('<<Copy>>')
            self.text.tag_remove(SEL, '1.0', END)
        except TclError:
            pass

    def cutRegion(self):
        try:
            self._selectRegion()
            self.text.event_generate('<<Cut>>')
            self.text.see(INSERT)
        except TclError:
            pass

    def paste(self):
        self.text.event_generate('<<Paste>>')
        self.text.see(INSERT)

    def swapMarkAndInsert(self):
        try:
            mark = self.text.index('mark')
            self.setMark()
            self.text.mark_set(INSERT, mark)
        except TclError:
            pass

    def nextPage(self):
        self.text.event_generate('<Next>')

    def prevPage(self):
        self.text.event_generate('<Prior>')

    def insertTab(self, textIndex = None):
        index = INSERT
        if textIndex is not None:
            index = textIndex._getIndex()
        self.text.insert(INSERT, ' ' * 4)

    def set_highlighting(self, highlighting):
        self.highlighting = highlighting
        for name, style in self.highlighting.getStyles().iteritems():
            fontKWs = {}
            if style.italic is not None:
                if style.italic:
                    fontKWs['slant'] = 'italic'
                else:
                    fontKWs['slant'] = 'roman'
            if style.bold is not None:
                if style.bold:
                    fontKWs['weight'] = 'bold'
                else:
                    fontKWs['weight'] = 'normal'
            if style.underline is not None:
                if style.underline:
                    fontKWs['underline'] = 1
                else:
                    fontKWs['underline'] = 0
            if style.strikethrough is not None:
                if style.strikethrough:
                    fontKWs['overstrike'] = 1
                else:
                    fontKWs['overstrike'] = 0
            font = Font(font=self.text['font']).copy()
            font.configure(**fontKWs)
            configKWs = {}
            if style.color is not None:
                configKWs['foreground'] = style.color
            configKWs['font'] = font
            self.text.tag_config(name, **configKWs)
        self._highlight_range('0.0', 'end')

    def get_searcher(self):
        return self.searcher

    def highlight_match(self, match):
        if not match:
            return
        self.text.tag_remove(SEL, '1.0', END)
        self.text.tag_add(SEL, match.start._getIndex(), match.end._getIndex())
        if match.side == 'right':
            self.text.mark_set(INSERT, match.end._getIndex())
        else:
            self.text.mark_set(INSERT, match.start._getIndex())
        self.text.see(INSERT)


    def _search_event(self, forward):
        if self.searcher.is_searching():
            self.searcher.configure_search(forward)
            self.searcher.next_match()
        else:
            self.searcher.start_searching()
            self.searcher.configure_search(forward)

    def _search_handler(self, event):
        if not self.searcher.is_searching():
            return
        import string
        if len(event.char) == 1 and (event.char.isalnum() or
                                     event.char in string.punctuation):
            self.searcher.append_keyword(event.char)
            return 'break'
        if event.keysym == 'space':
            self.searcher.append_keyword(event.char)
            return 'break'
        if event.keysym == 'BackSpace':
            self.searcher.shorten_keyword()
            return 'break'
        if event.keysym == 'Return':
            self.searcher.end_searching()
            return 'break'
        return 'break'

    def search(self, keyword, start, case=True, forwards=True):
        found = self.text.search(keyword, start._getIndex(),
                                 nocase=int(not case), backwards=int(not forwards))
        if not found:
            return None
        return GraphicalTextIndex(self, found)

    def set_indenter(self, text_indenter):
        self.indenter = text_indenter

    def get_indenter(self):
        return self.indenter

    def get_current_line_number(self):
        return self._get_line_from_index(INSERT)


class GraphicalTextIndex(TextIndex):
    '''An immutable class for pointing to a position in a text'''
    def __init__(self, editor, index):
        self.index = index
        self.editor = editor
        if self.editor.text.compare(index, '==', 'end'):
            self.index = 'end-1c'
        self.index = editor.text.index(self.index)

    def __cmp__(self, index):
        assert self.editor == index.editor
        if self.editor.text.compare(self.index, '<', index.index):
            return -1
        if self.editor.text.compare(self.index, '>', index.index):
            return +1
        return 0

    def _getIndex(self):
        return self.index

    def __str__(self):
        return '<%s, %s>' % (self.__class__.__name__, self.index)

