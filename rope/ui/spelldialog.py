import threading
import Tkinter

from rope.ide.spellchecker import SpellChecker


class _SpellCheckingDialog(object):

    def __init__(self, context, start, end):
        self.editor = context.editor
        self.offset = start
        self.text = self.editor.get_text()[start:end]
        self.checker = SpellChecker(self.text)
        self.typos = self.checker.check()
        self.changed_offset = start
        self.semaphore = threading.Semaphore(0)

    def do(self):
        try:
            while True:
                typo = self.typos.next()
                typo_dialog = _TypoDialog(typo, self)
                typo_dialog()
        except StopIteration:
            pass

    def quit(self):
        self.checker.quit()


class _TypoDialog(object):

    def __init__(self, typo, checking):
        self.typo = typo
        self.checking = checking
        self.editor = checking.editor
        self.toplevel = None

    def __call__(self):
        toplevel = Tkinter.Toplevel()
        self.toplevel = toplevel
        toplevel.title('Spell Checker <%s>' % self.typo.original)
        suggestions = ''
        for index, name in enumerate(self.typo.suggestions[:10]):
            suggestions += '%i : %s\n' % (index, name)
            toplevel.bind('<KeyPress-%i>' % index,
                          lambda event, name=name: self._use(name))
        actions = 'SPC : Leave unchanged\n'
        actions += 'r : Replace word\n'
        actions += 'a : Accept for this session\n'
        actions += 'i : Insert into private dictionary\n'
        actions += 'l : Insert lower cased version into private dictionary\n'
        actions += 'q : quit session\n'
        toplevel.bind('<space>', self._skip)
        toplevel.bind('r', self._replace)
        toplevel.bind('a', self._add_session)
        toplevel.bind('i', self._add_dictionary)
        toplevel.bind('l', self._add_lower_to_dictionary)
        toplevel.bind('q', self._quit_session)
        toplevel.bind('<Control-g>', self._quit_session)
        toplevel.bind('<Escape>', self._quit_session)
        label1 = Tkinter.Label(toplevel, text=suggestions, justify=Tkinter.LEFT)
        label2 = Tkinter.Label(toplevel, text=actions, justify=Tkinter.LEFT)
        label1.grid(row=0, column=0)
        label2.grid(row=0, column=1)
        # For blocking the main thread
        toplevel.focus_set()
        toplevel.grab_set()
        toplevel.mainloop()

    def _add_session(self, event=None):
        self.checking.checker.accept_word(self.typo.original)

    def _add_dictionary(self, event=None):
        self.checking.checker.insert_dictionary(self.typo.original)

    def _add_lower_to_dictionary(self, event=None):
        self.checking.checker.insert_dictionary(self.typo.original.lower())

    def _replace(self, event=None):
        toplevel = Tkinter.Toplevel()
        toplevel.title('Replace <%s>' % self.typo.original)
        label = Tkinter.Label(toplevel, text='Replace <%s> With :' %
                              self.typo.original)
        entry = Tkinter.Entry(toplevel)
        entry.insert(0, self.typo.original)
        entry.select_range(0, Tkinter.END)
        def cancel(event=None):
            toplevel.destroy()
        def done(event=None):
            replacement = entry.get()
            toplevel.destroy()
            self._use(replacement)
        entry.bind('<Control-g>', cancel)
        entry.bind('<Escape>', cancel)
        entry.bind('<Return>', done)
        label.grid(row=0, column=0)
        entry.grid(row=0, column=1)
        entry.focus_set()
        entry.grab_set()

    def _use(self, name):
        length = len(self.typo.original)
        start = self.editor.get_index(self.typo.offset + self.checking.changed_offset)
        end = self.editor.get_relative(start, length)
        new_length = len(name)
        self.editor.delete(start, end)
        self.editor.insert(start, name)
        self.checking.changed_offset += new_length - length
        self._skip()

    def _skip(self, event=None):
        self.toplevel.destroy()
        self.toplevel.quit()

    def _quit_session(self, event=None):
        self.checking.quit()
        self._skip()


def check_word(context):
    text = context.editor.get_text()
    offset = context.editor.get_current_offset()
    end = min(len(text) - 1, offset)
    start = max(0, offset - 1)
    for index in range(start, -1, -1):
        c = text[index]
        if c.isalnum():
            start = index
        else:
            break
    for index in range(start, len(text)):
        c = text[index]
        if c.isalnum():
            end = index + 1
        else:
            break
    _SpellCheckingDialog(context, start, end).do()    

def check_region(context):
    start, end = context.editor.get_region_offset()
    _SpellCheckingDialog(context, start, end).do()

def check_buffer(context):
    end = len(context.editor.get_text())
    _SpellCheckingDialog(context, 0, end).do()
