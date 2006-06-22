import os

from Tkinter import *
from tkFont import *
from ScrolledText import ScrolledText

import rope.highlight
import rope.searching
import rope.indenter
import rope.codeassist
from rope.uihelpers import EnhancedList


class TextEditor(object):
    '''The base class for all text editor'''
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

    def next_word(self):
        pass

    def prev_word(self):
        pass

    def delete_next_word(self):
        pass

    def delete_prev_word(self):
        pass

    def goto_start(self):
        pass

    def goto_end(self):
        pass

    def set_highlighting(self, highlighting):
        pass

    def highlight_match(self, match):
        pass

    def search(self, keyword, start, case=True, forwards=True):
        pass

    def undo_separator(self):
        pass

    def line_editor(self):
        pass


class TextIndex(object):
    '''A class for pointing to a position in a text'''


class LineEditor(object):
    """An interface for line oriented editors"""
    
    def get_line(self, line_number):
        pass
    
    def length(self):
        pass
    
    def indent_line(self, line_number, count):
        pass


class GraphicalLineEditor(LineEditor):
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


class GraphicalEditor(TextEditor):
    def __init__(self, parent):
        font = None
        if os.name == 'posix':
            font = Font(family='Typewriter', size=14)
        else:
            font = Font(family='Courier', size=13)
        self.text = ScrolledText(parent, bg='white',
                         font=font,
                         undo=True, maxundo=20, highlightcolor='#99A')
        self.searcher = rope.searching.Searcher(self)
        self._bind_keys()
        self._initialize_highlighting()
        self.highlighting = rope.highlight.NoHighlighting()
        self.indenter = rope.indenter.NormalIndenter(self)
        self.code_assist = rope.codeassist.NoAssist()
        self.status_bar_manager = None

    def _initialize_highlighting(self):
        def colorize(event=None):
            start = 'insert linestart-2c'
            end = 'insert lineend'
            start_tags = self.text.tag_names(start)
            if start_tags:
                tag = start_tags[0]
                range_ = self.text.tag_prevrange(tag, start + '+1c')
                if self.text.compare(range_[0], '<', start):
                    start = range_[0]
                if self.text.compare(range_[1], '>', end):
                    end = range_[1]
            end_tags = self.text.tag_names(end)
            if end_tags:
                tag = end_tags[0]
                range_ = self.text.tag_prevrange(tag, end + '+1c')
                if self.text.compare(range_[1], '>', end):
                    end = range_[1]
            self._highlight_range(start, end)
        def modified(event):
            if not self.modified_flag:
                print 'start modified', event
                self.modified_flag = True
                colorize()
                self.text.edit_modified(False)
                self.modified_flag = False
                print 'end modified', event
        self.modified_flag = False
        self.text.bind('<Any-KeyRelease>', colorize, '+')
        #        self.text.bind('<<Modified>>', modified)
        self.text.edit_modified(False)

    def _highlight_range(self, startIndex, endIndex):
        for style in self.highlighting.getStyles().keys():
            self.text.tag_remove(style, startIndex, endIndex)
        for start, end, kind in self.highlighting.highlights(GraphicalTextIndex(self, startIndex),
                                                             GraphicalTextIndex(self, endIndex)):
            self.text.tag_add(kind, start._getIndex(), end._getIndex())

    def _bind_keys(self):
        self.text.bind('<Alt-f>', lambda event: self.next_word())
        self.text.bind('<Alt-b>', lambda event: self.prev_word())
        self.text.bind('<Alt-d>', lambda event: self.delete_next_word())
        def delete_prev_wordListener(event):
            self.delete_prev_word()
            return 'break'
        self.text.bind('<Alt-BackSpace>', delete_prev_wordListener)
        def do_undo(event):
            self.undo()
            return 'break'
        def do_redo(event):
            self.redo()
            return 'break'
        self.text.bind('<Control-x><u>', do_undo)
        self.text.bind('<Control-x><r>', do_redo)
        def do_goto_start(event):
            self.goto_start()
            self.text.see(INSERT)
        def do_goto_end(event):
            self.goto_end()
            self.text.see(INSERT)
        self.text.bind('<Alt-less>', do_goto_start)
        self.text.bind('<Alt-KeyPress->>', do_goto_end)
        def do_set_mark(event):
            self.set_mark()
            return 'break'
        self.text.bind('<Control-space>', do_set_mark)
        def do_copy(event):
            self.copy_region()
            return 'break'
        self.text.bind('<Alt-w>', do_copy)
        def do_cut(event):
            self.cut_region()
            return 'break'
        self.text.bind('<Control-w>', do_cut)
        def do_paste(event):
            self.paste()
            return 'break'
        self.text.bind('<Control-y>', do_paste)
        def escape(event):
            self.clear_mark()
            if self.get_searcher().is_searching():
                self.get_searcher().cancel_searching()
        self.text.bind('<Control-g>', escape)
        self.text.bind('<Escape>', escape)
        def do_swap_mark_and_insert(event):
            self.swap_mark_and_insert()
            return 'break'
        self.text.bind('<Control-x><Control-x>', do_swap_mark_and_insert)
        def go_next_page(event):
            self.next_page()
            return 'break'
        self.text.bind('<Control-v>', go_next_page)
        def go_prev_page(event):
            self.prev_page()
            return 'break'
        self.text.bind('<Alt-v>', go_prev_page)
        def indent_line(event):
            self.correct_line_indentation()
            return 'break'
        def do_insert_tab(event):
            self.insert_tab()
            return 'break'
        self.text.bind('<Control-i>', indent_line)
        self.text.bind('<Tab>', do_insert_tab)
        def return_handler(event):
            if self.searcher.is_searching():
                self.searcher.end_searching()
                return 'break'
            self.text.insert(INSERT, '\n')
            self.correct_line_indentation()
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
                self.indenter.deindent(self.get_current_line_number())
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
        self.text.bind('<Alt-slash>', lambda event: self._show_completion_window());
        self.text.bind('<FocusOut>', lambda event: self._focus_went_out())
        self.text.bind('<F3>', lambda event: self.goto_definition())

    def goto_definition(self):
        result = self.code_assist.get_definition_location(self.get_text(),
                                                          self.get_current_offset())
        editor = self
        if result[0] is not None:
            import rope.core
            editor = rope.core.Core.get_core().get_editor_manager().\
                     get_resource_editor(result[0].get_resource()).get_editor()
        if result[1] is not None:
            editor.goto_line(result[1])

    def _focus_went_out(self):
        if self.searcher.is_searching():
            self.searcher.end_searching()

    def goto_line(self, lineno, colno=0):
        self.text.mark_set(INSERT, '%d.%d' % (lineno, colno))
        self.text.see(INSERT)

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

    def _show_completion_window(self):
        result = self.code_assist.assist(self.get_text(), self.get_current_offset())
        toplevel = Toplevel()
        toplevel.title('Code Assist Proposals')
        def open_selected(selected):
            if selected.kind != 'template':
                self.text.delete('0.0 +%dc' % result.start_offset,
                                 '0.0 +%dc' % result.end_offset)
                self.text.insert('0.0 +%dc' % result.start_offset,
                                 selected.name)
            else:
                self._get_template_information(result, selected)
            toplevel.destroy()
        def cancel():
            toplevel.destroy()
        def entry_to_string(proposal):
            return proposal.kind[0].upper() + '  ' + proposal.name
        enhanced_list = EnhancedList(toplevel, entry_to_string, open_selected, cancel, cancel)
        for proposal in result.completions:
            enhanced_list.add_entry(proposal)
        for proposal in result.templates:
            enhanced_list.add_entry(proposal)
        #        self.text.see('insert')
        #        local_x, local_y, cx, cy = self.text.bbox("insert")
        #        x = local_x + self.text.winfo_rootx() + 2
        #        y = local_y + cy + self.text.winfo_rooty()
        #        toplevel.wm_geometry('+%d+%d' % (x, y))
        #        toplevel.wm_overrideredirect(1)
        enhanced_list.list.focus_set()
        toplevel.grab_set()

    def _get_template_information(self, result, proposal):
        template = proposal.template
        def apply_template(mapping):
            string = template.substitute(mapping)
            self.text.delete('0.0 +%dc' % result.start_offset,
                             '0.0 +%dc' % result.end_offset)
            self.text.insert('0.0 +%dc' % result.start_offset,
                             string)
            offset = template.get_cursor_location(mapping)
            self.text.mark_set(INSERT, '0.0 +%dc' % (result.start_offset + offset))
            self.text.see(INSERT)

        if not template.variables():
            apply_template({})
            return
        toplevel = Toplevel()
        toplevel.title(proposal.name)
        frame = Frame(toplevel)
        label = Label(frame, text=('Variables in template %s' % proposal.name))
        label.grid(row=0, column=0, columnspan=2)
        entries = {}
        def ok(event=None):
            mapping = {}
            for var, entry in entries.iteritems():
                mapping[var] = entry.get()
            apply_template(mapping)
            toplevel.destroy()
        def cancel(event=None):
            toplevel.destroy()

        for (index, var) in enumerate(template.variables()):
            label = Label(frame, text=var, width=20)
            label.grid(row=index+1, column=0)
            entry = Entry(frame, width=25)
            entry.insert(INSERT, var)
            entry.grid(row=index+1, column=1)
            entries[var] = entry
        ok_button = Button(frame, text='Done', command=ok)
        cancel_button = Button(frame, text='Cancel', command=cancel)
        ok_button.grid(row=len(template.variables()) + 1, column=0)
        cancel_button.grid(row=len(template.variables()) + 1, column=1)
        frame.grid()

    def get_text(self):
        return self.text.get('1.0', 'end-1c')

    def set_text(self, text):
        self.text.delete('1.0', END)
        self.text.insert('1.0', text)
        self.text.mark_set(INSERT, '1.0')
        self._highlight_range('0.0', 'end')
        self.text.edit_reset()
        self.text.edit_modified(False)

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
        
    def _get_next_word_index_old(self):
        result = INSERT
        while self.text.compare(result, '!=', 'end-1c') and \
              not self.text.get(result)[0].isalnum():
            result = str(self.text.index(result + '+1c'))
        return result + ' wordend'

    def _get_next_word_index(self):
        current = str(self.text.index(INSERT))
        if self.text.get(current) == '\n':
            return current + '+1c'
        while self.text.compare(current, '!=', 'end-1c') and not self.text.get(current).isalnum():
            current = str(self.text.index(current + ' +1c'))
            if self.text.get(current) == '\n':
                return current
        is_upper = self.text.get(current).isupper()
        while self.text.compare(current, '!=', 'end-1c'):
            current = str(self.text.index(current + ' +1c'))
            if not self.text.get(current).isalnum() or self.text.get(current).isupper():
                break
        return current

    def next_word(self):
        self.text.mark_set(INSERT, self._get_next_word_index())
        self.text.see(INSERT)

    def _get_prev_word_index_old(self):
        result = INSERT
        while not self.text.compare(result, '==', '1.0') and \
              not self.text.get(result + '-1c')[0].isalnum():
            result = str(self.text.index(result + '-1c'))
        return result + '-1c wordstart'

    def _get_prev_word_index(self):
        current = str(self.text.index(INSERT))
        if self.text.get(current + '-1c') == '\n':
            return current + '-1c'
        while self.text.compare(current, '!=', '1.0') and not self.text.get(current + ' -1c').isalnum():
            current = str(self.text.index(current + ' -1c'))
            if self.text.get(current + '-1c') == '\n':
                return current
        is_upper = self.text.get(current + ' -1c').isupper()
        while self.text.compare(current, '!=', '1.0') and self.text.get(current + ' -1c').isalnum():
            current = str(self.text.index(current + ' -1c'))
            if  self.text.get(current).isupper():
                break
        return current

    def prev_word(self):
        self.text.mark_set(INSERT, self._get_prev_word_index())
        self.text.see(INSERT)

    def delete_next_word(self):
        self.text.delete(INSERT, self._get_next_word_index())

    def delete_prev_word(self):
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
        start = 'mark'
        end = INSERT
        if self.text.compare(start, '>', end):
            start, end = end, start
        self.text.tag_add(SEL, start, end)

    def copy_region(self):
        try:
            self._select_region()
            self.text.event_generate('<<Copy>>')
            self.text.tag_remove(SEL, '1.0', END)
        except TclError:
            pass

    def cut_region(self):
        try:
            self._select_region()
            self.text.event_generate('<<Cut>>')
            self.text.see(INSERT)
        except TclError:
            pass

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

    def set_code_assist(self, code_assist):
        self.code_assist = code_assist

    def get_indenter(self):
        return self.indenter

    def get_current_line_number(self):
        return self._get_line_from_index(INSERT)

    def get_current_offset(self):
        result = self._get_column_from_index(INSERT)
        current_line = self._get_line_from_index(INSERT)
        current_pos = '1.0 lineend'
        for x in range(current_line - 1):
            result += self._get_column_from_index(current_pos) + 1
            current_pos = str(self.text.index(current_pos + ' +1l lineend'))
        return result

    def set_status_bar_manager(self, manager):
        self.status_bar_manager = manager

    def line_editor(self):
        return GraphicalLineEditor(self)


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
        return str(self.index)

    def __str__(self):
        return '<%s, %s>' % (self.__class__.__name__, self.index)

