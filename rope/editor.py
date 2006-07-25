import os

from Tkinter import *
from tkFont import *
from ScrolledText import ScrolledText

import rope.highlight
import rope.searching
import rope.indenter
import rope.codeassist
import rope.editingtools
from rope.uihelpers import EnhancedList, EnhancedListHandle
from rope.uihelpers import TreeViewer, TreeViewerHandle


class TextEditor(object):
    """The base class for all text editor"""
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

    def highlight_match(self, match):
        pass

    def search(self, keyword, start, case=True, forwards=True):
        pass

    def line_editor(self):
        pass


class TextIndex(object):
    """A class for pointing to a position in a text"""


class LineEditor(object):
    """An interface for line oriented editors"""
    
    def get_line(self, line_number):
        pass
    
    def length(self):
        pass
    
    def indent_line(self, line_number, count):
        pass


class EditorFactory(object):

    def create(self):
        pass

class GraphicalEditorFactory(EditorFactory):

    def __init__(self, frame):
        self.frame = frame

    def create(self, *args, **kws):
        return GraphicalEditor(self.frame, *args, **kws)


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


class _CompletionListHandle(EnhancedListHandle):

    def __init__(self, editor, toplevel, code_assist_result):
        self.editor = editor
        self.toplevel = toplevel
        self.result = code_assist_result

    def entry_to_string(self, proposal):
        return proposal.kind[0].upper() + '  ' + proposal.name

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        if selected.kind != 'template':
            self.editor.text.delete('0.0 +%dc' % self.result.start_offset, INSERT)
            self.editor.text.insert('0.0 +%dc' % self.result.start_offset,
                                    selected.name)
        else:
            self.editor._get_template_information(self.result, selected)
        self.toplevel.destroy()

    def focus_went_out(self):
        self.canceled()


class _OutlineViewHandle(TreeViewerHandle):
    
    def __init__(self, editor, toplevel):
        self.editor = editor
        self.toplevel = toplevel

    def entry_to_string(self, outline_node):
        return outline_node.get_name()

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        self.editor.goto_line(selected.get_line_number())
        self.toplevel.destroy()

    def focus_went_out(self):
        self.canceled()

    def get_children(self, outline_node):
        return outline_node.get_children()
        
        
class GraphicalEditor(TextEditor):

    def __init__(self, parent, editor_tools):
        font = None
        if os.name == 'posix':
            font = Font(family='Typewriter', size=14)
        else:
            font = Font(family='Courier', size=13)
        self.text = ScrolledText(parent, bg='white', font=font,
                                 undo=True, maxundo=20, highlightcolor='#99A')
        self.searcher = rope.searching.Searcher(self)
        self._set_editing_tools(editor_tools)
        self._bind_keys()
        self._initialize_highlighting()
        self.status_bar_manager = None
        self.modification_observers = []

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
        self.modified_flag = False
        self.text.bind('<Any-KeyRelease>', colorize, '+')
        self.text.bind('<<Modified>>', self._editor_modified)
        self.text.edit_modified(False)
    
    def _editor_modified(self, event):
        if self.modified_flag:
            self.modified_flag = False
        else:
            self.modified_flag = True
        for observer in self.modification_observers:
            observer()

    def add_modification_observer(self, observer):
        self.modification_observers.append(observer)

    def _highlight_range(self, start_index, end_index):
        for style in self.highlighting.get_styles().keys():
            self.text.tag_remove(style, start_index, end_index)
        start_offset = self._get_offset(start_index)
        end_offset = self._get_offset(end_index)
        for start, end, kind in self.highlighting.highlights(self.get_text(),
                                                             start_offset,
                                                             end_offset):
            tag_start = '1.0 +%dc' % start
            tag_end = '1.0 +%dc' % end
            self.text.tag_add(kind, tag_start, tag_end)

    def _bind_keys(self):
        self.text.bind('<Alt-f>', lambda event: self.next_word())
        self.text.bind('<Alt-b>', lambda event: self.prev_word())
        self.text.bind('<Alt-d>', lambda event: self.delete_next_word())
        def delete_prev_word_listener(event):
            self.delete_prev_word()
            return 'break'
        self.text.bind('<Alt-BackSpace>', delete_prev_word_listener)
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
        self.text.event_add('<<ForwardSearch>>', '<Control-s>')
        self.text.event_add('<<BackwardSearch>>', '<Control-r>')
        self.text.bind('<<ForwardSearch>>',
                       lambda event: self.start_searching(True), '+')
        self.text.bind('<<BackwardSearch>>',
                       lambda event: self.start_searching(False))
        self.text.bind('<Any-KeyPress>', self._search_handler)
        self.text.bind('<BackSpace>', backspace, '+')
        self.text.bind('<Alt-slash>', lambda event: self._show_completion_window());
        self.text.bind('<FocusOut>', lambda event: self._focus_went_out())
        self.text.bind('<F3>', lambda event: self.goto_definition())
        def show_quick_outline(event):
            self._show_outline_window()
            return 'break'
        self.text.bind('<Control-o>', show_quick_outline)
        self.text.bind('<Alt-R>', self._rename_refactoring_dialog)

    def goto_definition(self):
        result = self.code_assist.get_definition_location(self.get_text(),
                                                          self.get_current_offset())
        self._goto_editor_location(result[0], result[1])
            
    def _goto_editor_location(self, resource, lineno):
        editor = self
        if resource is not None:
            import rope.core
            editor = rope.core.Core.get_core().get_editor_manager().\
                     get_resource_editor(resource).get_editor()
        if lineno is not None:
            editor.goto_line(lineno)
            
    def _rename_refactoring_dialog(self, event=None):
        toplevel = Toplevel()
        toplevel.title('Rename Refactoring')
        frame = Frame(toplevel)
        label = Label(frame, text='New Name :')
        label.grid(row=0, column=0)
        new_name_entry = Entry(frame)
        new_name_entry.grid(row=0, column=1)
        def ok(event=None):
            self.rename_refactoring(new_name_entry.get())
            toplevel.destroy()
        def cancel(event=None):
            toplevel.destroy()

        ok_button = Button(frame, text='Done', command=ok)
        cancel_button = Button(frame, text='Cancel', command=cancel)
        ok_button.grid(row=1, column=0)
        new_name_entry.bind('<Return>', lambda event: ok())
        new_name_entry.bind('<Escape>', lambda event: cancel())
        cancel_button.grid(row=1, column=1)
        frame.grid()
        new_name_entry.focus_set()

    def rename_refactoring(self, new_name):
        initial_position = self.text.index(INSERT)
        refactored = self.refactoring.rename(self.get_text(),
                                             self.get_current_offset(), new_name)
        self.set_text(refactored, False)
        self.text.mark_set(INSERT, initial_position)
        self.text.see(INSERT)

    def _focus_went_out(self):
        if self.searcher.is_searching():
            self.searcher.end_searching()

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

    def _show_completion_window(self):
        result = self.code_assist.assist(self.get_text(), self.get_current_offset())
        toplevel = Toplevel()
        toplevel.title('Code Assist Proposals')
        enhanced_list = EnhancedList(toplevel, _CompletionListHandle(self, toplevel, result),
                                     title='Code Assist Proposals')
        proposals = rope.codeassist.ProposalSorter(result).get_sorted_proposal_list()
        for proposal in proposals:
            enhanced_list.add_entry(proposal)
        start_index = self.text.index('0.0 +%dc' % result.start_offset)
        initial_cursor_position = str(self.text.index(INSERT))
        def key_pressed(event):
            import string
            if len(event.char) == 1 and (event.char.isalnum() or
                                         event.char in string.punctuation):
                self.text.insert(INSERT, event.char)
            elif event.keysym == 'space':
                self.text.insert(INSERT, ' ')
            elif event.keysym == 'BackSpace':
                self.text.delete(INSERT + '-1c')
            elif self.text.compare(initial_cursor_position, '>', INSERT):
                toplevel.destroy()
                return
            else:
                return
            new_name = self.text.get(start_index, INSERT)
            enhanced_list.clear()
            for proposal in proposals:
                if proposal.name.startswith(new_name):
                    enhanced_list.add_entry(proposal)
        enhanced_list.list.focus_set()
        enhanced_list.list.bind('<Any-KeyPress>', key_pressed)
        toplevel.grab_set()

    def _show_outline_window(self):
        toplevel = Toplevel()
        toplevel.title('Quick Outline')
        tree_view = TreeViewer(toplevel, _OutlineViewHandle(self, toplevel),
                               title='Quick Outline')
        for node in self.outline.get_root_nodes(self.get_text()):
            tree_view.add_entry(node)
        tree_view.list.focus_set()
        toplevel.grab_set()

    def _get_template_information(self, result, proposal):
        template = proposal.template
        def apply_template(mapping):
            string = template.substitute(mapping)
            self.text.delete('0.0 +%dc' % result.start_offset, INSERT)
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

    def set_text(self, text, reset_editor=True):
        self.text.delete('1.0', END)
        self.text.insert('1.0', text)
        self.text.mark_set(INSERT, '1.0')
        self._highlight_range('0.0', 'end')
        if reset_editor:
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
        while self.text.compare(current, '!=', '1.0') and \
              not self.text.get(current + ' -1c').isalnum():
            current = str(self.text.index(current + ' -1c'))
            if self.text.get(current + '-1c') == '\n':
                return current
        is_upper = self.text.get(current + ' -1c').isupper()
        while self.text.compare(current, '!=', '1.0') and \
              self.text.get(current + ' -1c').isalnum():
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
        for name, style in self.highlighting.get_styles().iteritems():
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
        return self._get_offset(INSERT)
    
    def _get_offset(self, index):
        result = self._get_column_from_index(index)
        current_line = self._get_line_from_index(index)
        current_pos = '1.0 lineend'
        for x in range(current_line - 1):
            result += self._get_column_from_index(current_pos) + 1
            current_pos = str(self.text.index(current_pos + ' +1l lineend'))
        return result
    
    def set_status_bar_manager(self, manager):
        self.status_bar_manager = manager

    def _set_editing_tools(self, editing_tools):
        self.editing_tools = editing_tools
        self.set_indenter(editing_tools.create_indenter(self))
        self.set_code_assist(editing_tools.create_code_assist())
        self.set_highlighting(editing_tools.create_highlighting())
        self.outline = editing_tools.create_outline()
        self.refactoring = editing_tools.create_refactoring()

    def line_editor(self):
        return GraphicalLineEditor(self)


class GraphicalTextIndex(TextIndex):
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

