import os

import ScrolledText
import tkFont
import Tkinter
from Tkinter import END, TclError, SEL_FIRST, SEL, SEL_LAST, INSERT, Toplevel, Text

import rope.contrib.codeassist
import ropeide.editingtools
import ropeide.searcher
import ropeide.tkhelpers


class GraphicalEditor(object):

    def __init__(self, parent, editorcontext, font=None):
        if font is None:
            if os.name == 'posix':
                font = tkFont.Font(family='Typewriter', size=14)
            else:
                font = tkFont.Font(family='Courier', size=14)
        self.text = ScrolledText.ScrolledText(
            parent, bg='white', font=font, undo=True,
            maxundo=100, highlightcolor='#99A')
        self.change_inspector = _TextChangeInspector(self, self._text_changed)
        self.searcher = ropeide.searcher.Searcher(self)
        self._set_editingcontexts(editorcontext)
        self._bind_keys()
        self.status_bar_manager = None
        self.modification_observers = []
        self.change_observers = []
        self.modified_flag = False
        self.kill_ring = KillRingManager()
        self.text.bind('<<Modified>>', self._editor_modified)
        self.text.edit_modified(False)

    def _text_changed(self):
        if not self.change_inspector.is_changed():
            return
        start, end = self.change_inspector.get_changed_region()
        self.change_inspector.clear_changed()
        self._colorize(start, end)
        if self.modified_flag:
            for observer in self.change_observers:
                observer(end)

    def _colorize(self, start, end):
        start_offset, end_offset = \
            self.highlighting.get_suspected_region_after_change(
            self.get_text(), self.get_offset(start), self.get_offset(end))
        start = self.text.index('1.0 +%dc' % start_offset)
        end = self.text.index(start + ' +%dc' % (end_offset - start_offset))
        start_tags = self.text.tag_names(start)
        if start_tags:
            tag = start_tags[0]
            range_ = self.text.tag_prevrange(tag, start + '+1c')
            if range_ and self.text.compare(range_[0], '<', start):
                start = range_[0]
            if range_ and self.text.compare(range_[1], '>', end):
                end = range_[1]
        end_tags = self.text.tag_names(end)
        if end_tags:
            tag = end_tags[0]
            range_ = self.text.tag_prevrange(tag, end + '+1c')
            if range_ and self.text.compare(range_[1], '>', end):
                end = range_[1]
        self._highlight_range(start, end)

    def _highlight_range(self, start_index, end_index):
        for style in self.highlighting.get_styles().keys():
            self.text.tag_remove(style, start_index, end_index)
        start_offset = self.get_offset(start_index)
        end_offset = self.get_offset(end_index)
        indexer = _OffsetToIndexCacher(self.text)
        for start, end, kind in self.highlighting.highlights(self.get_text(),
                                                             start_offset,
                                                             end_offset):
            self.text.tag_add(kind, indexer.get_index(start),
                              indexer.get_index(end))

    def select_range(self, start_index, end_index):
        self.text.tag_remove(SEL, '1.0', END)
        self.text.tag_add(SEL, start_index._getIndex(),
                          end_index._getIndex())
        self.text.see(start_index._getIndex())

    def _bind_keys(self):
        def escape(event):
            self.clear_mark()
            if self.get_searcher().is_searching():
                self.get_searcher().cancel_searching()
        self.text.bind('<Control-g>', escape)
        self.text.bind('<Escape>', escape)
        def do_insert_tab(event):
            self.insert_tab()
            return 'break'
        self.text.bind('<Tab>', do_insert_tab)
        def return_handler(event):
            if self.searcher.is_searching():
                self.searcher.end_searching()
                return 'break'
            self._insert_new_line()
            return 'break'
        def backspace(event):
            if self.searcher.is_searching():
                self.searcher.shorten_keyword()
                return 'break'
            line_starting = self.text.get('insert linestart', 'insert')
            current_char = self.text.get(INSERT)
            if line_starting.isspace() and (not current_char.isspace()
                                            or current_char == '' or current_char == '\n'):
                self.indenter.deindent(self.get_current_line_number())
                return 'break'
        self.text.bind('<Return>', return_handler)
        self.text.bind('<Any-KeyPress>', self._search_handler)
        self.text.bind('<BackSpace>', backspace, '+')
        self.text.bind('<FocusOut>', lambda event: self._focus_went_out())
        self.text.bind('<Destroy>', lambda event: self._focus_went_out(False))

    def center_line(self):
        mid = self._get_center_line()
        current = self._get_line_from_index(self.text.index(INSERT))
        diffs = current - mid
        self.text.yview_scroll(diffs, Tkinter.UNITS)

    def goto_center_line(self):
        mid = self._get_center_line()
        self.goto_line(mid)

    def _get_center_line(self):
        start = self._get_line_from_index(self.text.index('@0,0'))
        end = self._get_line_from_index(
            self.text.index('@0,%d' % self.text.winfo_height()))
        return (start + end) // 2

    def get_region_offset(self):
        start, end = self._get_region_index()
        start_offset = self.get_offset(start)
        end_offset = self.get_offset(end)
        return (start_offset, end_offset)

    def _get_region_index(self):
        start = ''
        end = ''
        try:
            start = self.text.index(SEL_FIRST)
            end = self.text.index(SEL_LAST)
        except TclError:
            pass
        if start == '' or end == '':
            start = self.text.index('mark')
            end = self.text.index(INSERT)
            if start == '':
                start = end
        if self.text.compare(start, '>', end):
            start, end = end, start
        return start, end

    def _focus_went_out(self, save=True):
        if self.searcher.is_searching():
            self.searcher.end_searching(save)

    def goto_line(self, lineno, colno=0):
        self.text.mark_set(INSERT, '%d.%d' % (lineno, colno))
        self.text.see(INSERT)

    def _insert_new_line(self):
        self.text.insert(INSERT, '\n')
        lineno = self.get_current_line_number()
        self.indenter.entering_new_line(lineno)
        first_non_space = 0
        while self.text.get('%d.%d' % (lineno, first_non_space)) == ' ':
            first_non_space += 1
        self.text.mark_set(INSERT, '%d.%d' % (lineno, first_non_space))
        self.text.see(INSERT)

    def _editor_modified(self, event):
        if self.modified_flag:
            self.modified_flag = False
        else:
            self.modified_flag = True
        for observer in self.modification_observers:
            observer()

    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def add_change_observer(self, observer):
        self.change_observers.append(observer)

    def is_modified(self):
        return self.modified_flag

    def correct_line_indentation(self):
        lineno = self.get_current_line_number()
        cols_from_end = len(self.text.get(INSERT, 'insert lineend'))
        self.indenter.correct_indentation(lineno)
        from_end = '%d.end -%dc' % (lineno, cols_from_end)
        first_non_space = 0
        while self.text.get('%d.%d' % (lineno, first_non_space)) == ' ':
            first_non_space += 1
        new_insert = '%d.%d' % (lineno, first_non_space)
        if self.text.compare(new_insert, '<', from_end):
            new_insert = from_end
        self.text.mark_set(INSERT, new_insert)
        self.text.see(INSERT)

    def get_text(self):
        return self.text.get('1.0', 'end-1c')

    def set_text(self, text, reset_editor=True):
        initial_position = self.text.index(INSERT)
        # IDEA: When to use `_change_text2` that uses difflib;
        # Maybe when the number of changes is few
        self._change_text1(text)
        self.text.mark_set(INSERT, initial_position)
        self.text.see(INSERT)
        if reset_editor:
            self.text.edit_reset()
            self.text.edit_modified(False)

    def _change_text1(self, text):
        self.text.delete('1.0', END)
        self.text.insert('1.0', text)

    def _change_text2(self, text):
        import difflib
        old_text = self.get_text()
        differ = difflib.Differ()
        current_line = 1
        for line in differ.compare(old_text.splitlines(True),
                                   text.splitlines(True)):
            if line.startswith(' '):
                current_line += 1
                continue
            if line.startswith('+'):
                self.text.insert('%s.0' % current_line, line[2:])
                current_line += 1
                continue
            if line.startswith('-'):
                self.text.delete('%s.0' % current_line, '%s.0' % (current_line + 1))
                continue

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
        return int(str(self.text.index(index)).split('.')[0])

    def _get_column_from_index(self, index):
        return int(str(self.text.index(index)).split('.')[1])

    def set_insert(self, textIndex):
        if isinstance(textIndex, basestring):
            self.text.mark_set(INSERT, textIndex)
        else:
            self.text.mark_set(INSERT, textIndex._getIndex())
        self.text.see(INSERT)

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

    def insert(self, text_index, text):
        self.text.insert(text_index._getIndex(), text)

    def delete(self, start=None, end=None):
        startIndex = INSERT
        if start is not None:
            startIndex = start._getIndex()
            if start == self.get_end():
                return
        endIndex = None
        if end is not None:
            endIndex = end._getIndex()
        self.text.delete(startIndex, endIndex)

    def _get_next_word_index_old(self):
        result = INSERT
        while self.text.compare(result, '!=', 'end-1c') and \
              not self.text.get(result)[0].isalnum():
            result = str(self.text.index(result + '+1c'))
        return result + ' wordend'

    def _get_next_word_index(self):
        line = self.text.get('insert', 'insert lineend')
        if line == '':
            return 'insert +1l linestart'
        offset = 0
        while offset < len(line) and not line[offset].isalnum():
            offset += 1
        if offset == 0:
            offset = 1
        while offset < len(line) and line[offset].isalnum():
            if offset > 0 and line[offset - 1].isalnum() and \
               line[offset].isupper() and offset + 1 < len(line) and \
               line[offset + 1].islower():
                break
            if offset > 0 and line[offset - 1].islower() and \
               line[offset].isupper():
                break
            offset += 1
        return 'insert +%dc' % offset

    def next_word(self):
        self.text.mark_set(INSERT, self._get_next_word_index())
        self.text.see(INSERT)

    def _change_next_word(self, function):
        next_word = self.text.index(self._get_next_word_index())
        while self.text.compare('insert', '<', 'end -1c') and \
              not self.text.get(INSERT).isalnum() and \
              self.text.compare('insert', '<', next_word):
            self.text.mark_set(INSERT, 'insert +1c')

        if self.text.compare('insert', '!=', next_word):
            word = self.text.get(INSERT, next_word)
            self.text.delete(INSERT, next_word)
            self.text.insert(INSERT, function(word))
            self.text.mark_set(INSERT, next_word)
        self.text.see(INSERT)

    def upper_next_word(self):
        self._change_next_word(str.upper)

    def lower_next_word(self):
        self._change_next_word(str.lower)

    def capitalize_next_word(self):
        self._change_next_word(str.capitalize)

    def _get_prev_word_index_old(self):
        result = INSERT
        while not self.text.compare(result, '==', '1.0') and \
              not self.text.get(result + '-1c')[0].isalnum():
            result = str(self.text.index(result + '-1c'))
        return result + '-1c wordstart'

    def _get_prev_word_index(self):
        column = self._get_column_from_index('insert')
        if column == 0:
            if self._get_line_from_index('insert') != 1:
                return 'insert -1l lineend'
            else:
                return 'insert'
        offset = column
        line = self.text.get('insert linestart', 'insert +1c')
        while offset > 0 and not line[offset - 1].isalnum():
            offset -= 1
        if offset == column:
            offset -= 1
        while offset > 0 and line[offset - 1].isalnum():
            if offset < len(line) - 1 and line[offset].isupper() and \
               line[offset + 1].islower():
                break
            if offset > 0 and line[offset - 1].islower() and \
               line[offset].isupper():
                break
            offset -= 1
        return 'insert linestart +%dc' % offset

    def prev_word(self):
        self.text.mark_set(INSERT, self._get_prev_word_index())
        self.text.see(INSERT)

    def delete_next_word(self):
        self.text.delete(INSERT, self._get_next_word_index())

    def delete_prev_word(self):
        self.text.delete(self._get_prev_word_index(), INSERT)

    def getWidget(self):
        return self.text

    def saving_editor(self):
        self.text.edit_separator()
        if self.is_modified():
            self.text.edit_modified(False)

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

    def goto_start(self):
        self.set_insert(self.get_start())

    def goto_end(self):
        self.set_insert(self.get_end())

    def generate_event(self, event):
        self.text.event_generate(event)

    def set_mark(self):
        self.text.mark_set('mark', INSERT)

    def clear_mark(self):
        self.text.mark_unset('mark')

    def _select_region(self):
        start, end = self._get_region_index()
        self.text.tag_add(SEL, start, end)

    def copy_region(self):
        try:
            self._add_yank()
            self._select_region()
            self.text.event_generate('<<Copy>>')
            self.text.tag_remove(SEL, '1.0', END)
        except TclError:
            pass

    def cut_region(self):
        try:
            self._add_yank()
            self._select_region()
            self.text.event_generate('<<Cut>>')
            self.text.see(INSERT)
        except TclError, e:
            pass

    def _add_yank(self):
        start, end = self._get_region_index()
        selected = self.text.get(start, end)
        self.kill_ring.killed(selected)

    def yank(self, count):
        result = self.kill_ring.yank(count)
        if result is not None:
            old = self.kill_ring.yank(count - 1)
            self.text.delete('insert -%dc' % len(old), INSERT)
            self.text.insert(INSERT, result)

    def paste(self):
        self.text.event_generate('<<Paste>>')
        self.text.see(INSERT)

    def swap_mark_and_insert(self):
        try:
            mark = self.text.index('mark')
            self.set_mark()
            self.text.mark_set(INSERT, mark)
            self.text.see(INSERT)
        except TclError:
            pass

    def kill_line(self, append=False):
        if self.text.compare('insert', '>=', 'end -1c'):
            return
        text = self.text.get('insert', 'insert lineend')
        if not append:
            self.text.clipboard_clear()
        if text == '':
            self.text.clipboard_append('\n')
            self.text.delete('insert')
        else:
            self.text.clipboard_append(text)
            self.text.delete('insert', 'insert lineend')
        if append:
            self.kill_ring.update_last(self.text.clipboard_get())
        else:
            self.kill_ring.killed(self.text.clipboard_get())

    def next_page(self):
        self.text.event_generate('<Next>')

    def prev_page(self):
        self.text.event_generate('<Prior>')

    def insert_tab(self, text_index = None):
        if text_index is None:
            text_index = self.get_insert()
        self.indenter.insert_tab(text_index)

    def set_highlighting(self, highlighting):
        self.highlighting = highlighting
        for name, style in self.highlighting.get_styles().items():
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
            font = tkFont.Font(font=self.text['font']).copy()
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


    def start_searching(self, forward):
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
                                 nocase=int(not case),
                                 backwards=int(not forwards))
        if not found:
            return None
        return GraphicalTextIndex(self, found)

    def set_indenter(self, text_indenter):
        self.indenter = text_indenter

    def get_indenter(self):
        return self.indenter

    def get_current_line_number(self):
        return self._get_line_from_index(INSERT)

    def get_current_column_number(self):
        return self._get_column_from_index(INSERT)

    def get_current_offset(self):
        return self.get_offset(INSERT)

    def _get_offset1(self, index):
        # adding up line lengths
        result = self._get_column_from_index(index)
        current_line = self._get_line_from_index(index)
        current_pos = '1.0 lineend'
        for x in range(current_line - 1):
            result += self._get_column_from_index(current_pos) + 1
            current_pos = str(self.text.index(current_pos + ' +1l lineend'))
        return result

    def _get_offset2(self, index):
        # walking the whole text
        text = self.get_text()
        column = self._get_column_from_index(index)
        line = self._get_line_from_index(index)
        current_pos = 0
        current_line = 1
        while current_line < line and current_pos < len(text):
            if text[current_pos] == '\n':
                current_line += 1
            current_pos += 1
        for i in range(column):
            if not current_pos < len(text) and text[current_pos] != '\n':
                break
            current_pos += 1
        return current_pos

    def _get_offset3(self, index):
        # using binary search
        text = self.get_text()
        start = 0
        end = len(text)
        indexer = _OffsetToIndexCacher(self.text)
        while start < end:
            mid = (start + end) // 2
            if self.text.compare(indexer.get_index(mid), '>', index):
                end = mid - 1
            elif self.text.compare(indexer.get_index(mid), '==', index):
                return mid
            else:
                start = mid + 1
        return start

    def get_offset(self, get_offset):
        return self._get_offset3(get_offset)

    def set_status_bar_manager(self, manager):
        self.status_bar_manager = manager

    def _set_editingcontexts(self, editingcontext):
        self.editingcontext = editingcontext
        editingtools = editingcontext.editingtools
        self.set_indenter(editingtools.create_indenter(self))
        self.set_highlighting(editingtools.create_highlighting())

    def get_editing_context(self):
        return self.editingcontext

    def line_editor(self):
        return GraphicalLineEditor(self)


class GraphicalTextIndex(object):
    """An immutable class for pointing to a position in a text"""

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
        return str(self.index)

    def __str__(self):
        return '<%s, %s>' % (self.__class__.__name__, self.index)


class _TextChangeInspector(object):

    def __init__(self, editor, change_observer=None):
        self.editor = editor
        self.text = editor.text
        self.redirector = ropeide.tkhelpers.WidgetRedirector(self.text)
        self.old_insert = self.redirector.register('insert', self._insert)
        self.old_delete = self.redirector.register('delete', self._delete)
        self.old_edit = self.redirector.register('edit', self._edit)
        self.change_observer = change_observer
        self.changed_region = None

    def _insert(self, *args):
        start = self.text.index(args[0])
        result = self.old_insert(*args)
        end = self.text.index(start + ' +%dc' % len(args[1]))
        if not start or not end:
            return
        if self.changed_region is not None:
            if self.text.compare(start, '<', self.changed_region[1]):
                end = self.text.index(self.changed_region[1] + ' +%dc' % len(args[1]))
            if self.text.compare(self.changed_region[0], '<', start):
                start = self.changed_region[0]
        self.changed_region = (start, end)
        self._notify_observer()
        return result

    def _notify_observer(self):
        if self.is_changed() and self.change_observer:
            self.text.after_idle(self.change_observer)

    def _delete(self, *args):
        start = self.text.index(args[0])
        result = self.old_delete(*args)
        end = start
        if not start:
            return
        if self.changed_region is not None:
            if self.text.compare(end, '<', self.changed_region[1]):
                delete_len = 1
                if len(args) > 1 and args[1] is not None:
                    delete_len = self.editor.get_offset(str(self.text.index(args[1]))) - \
                                 self.editor.get_offset(start)
                end = self.text.index(self.changed_region[1] + ' -%dc' % delete_len)
            if self.text.compare(self.changed_region[0], '<', start):
                start = self.changed_region[0]
        self.changed_region = (start, end)
        self._notify_observer()
        return result

    def _edit(self, *args):
        if len(args) < 1 or args[0] not in ['undo', 'redo']:
            return self.old_edit(*args)
        start = self.text.index(INSERT)
        result = self.old_edit(*args)
        end = self.text.index(INSERT)
        if self.text.compare(end, '<', start):
            start, end = end, start
        if self.changed_region is not None:
            if self.text.compare(self.changed_region[0], '<', start):
                start = self.changed_region[0]
            if self.text.compare(self.changed_region[1], '>', end):
                end = self.changed_region[1]
        self.changed_region = (start, end)
        self._notify_observer()
        return result

    def get_changed_region(self):
        return self.changed_region

    def is_changed(self):
        return self.changed_region is not None

    def clear_changed(self):
        self.changed_region = None


class EditorFactory(object):

    def create(self):
        pass


class GraphicalEditorFactory(EditorFactory):

    def __init__(self, frame, **kwds):
        self.frame = frame
        self.kwds = kwds

    def create(self, *args, **kwds):
        kwds.update(self.kwds)
        return GraphicalEditor(self.frame, *args, **kwds)


class GraphicalLineEditor(object):
    """An interface for line oriented editors"""

    def __init__(self, editor):
        self.editor = editor

    def get_line(self, line_number):
        return self.editor.text.get('%d.0' % line_number, '%d.0 lineend' % line_number)

    def length(self):
        result = self.editor._get_line_from_index(END) - 1
        return result

    def indent_line(self, line_number, count):
        if count == 0:
            return
        if count > 0:
            self.editor.text.insert('%d.0' % line_number, count * ' ')
        else:
            self.editor.text.delete('%d.0' % line_number,
                                    '%d.%d' % (line_number, -count))

    def insert_to_line(self, line_number, text):
        self.editor.text.insert('%d.0' % line_number, text)


class _OffsetToIndexCacher(object):
    """A faster way to convert offset to `Tkinter` index

    This should not be used if the text changes during calls to
    `get_index()` method.

    """
    def __init__(self, editor):
        self.editor = editor
        self.index = '1.0'
        self.offset = 0

    def get_index(self, offset):
        diff = offset - self.offset
        if diff == 0:
            return self.index
        if diff > 0:
            new_index = self.index + ' +%dc' % diff
        else:
            new_index = self.index + ' %dc' % diff
        if abs(diff) > 1:
            new_index = self.editor.index(new_index)
            self.index = new_index
            self.offset = offset
        return new_index


class OffsetToIndexCacher(object):
    """A faster way to convert offset to `GraphicalTextIndex`"""
    def __init__(self, editor):
        self.editor = editor
        self.cacher = _OffsetToIndexCacher(editor)

    def get_index(self, offset):
        return GraphicalTextIndex(editor, self.cacher.get_index(offset))


class KillRingManager(object):

    def __init__(self, limit=20):
        self.ring = []
        self.limit = limit

    def yank(self, count):
        if self.ring:
            return self.ring[count % len(self.ring)]

    def killed(self, killed):
        self.ring.insert(0, killed)
        if len(self.ring) > self.limit:
            del self.ring[-1]

    def update_last(self, new_text):
        if self.ring:
            self.ring[0] = new_text
