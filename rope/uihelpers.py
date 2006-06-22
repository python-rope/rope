from Tkinter import *


def do_nothing(*args, **kws):
    pass

class EnhancedListHandle(object):

    def entry_to_string(self, obj):
        return str(object)
    
    def selected(self, obj):
        pass
    
    def canceled(self):
        pass

    def focus_went_out(self):
        pass


class EnhancedList(object):

    def __init__(self, parent, handle):
        self.handle = handle
        self.entries = []
        self.frame = Frame(parent)
        label = Label(self.frame, text='Code Assist Proposals')
        self.list = Listbox(self.frame, selectmode=SINGLE)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        label.grid(row=0, column=0, columnspan=2)
        self.list.grid(row=1, column=0, sticky=N+E+W+S)
        scrollbar.grid(row=1, column=1, sticky=N+E+W+S)
        self.frame.grid(sticky=N+E+W+S)
        

    def _focus_out(self, event):
        self.handle.focus_went_out()

    def _open_selected(self, event):
        selection = self.list.curselection()
        if selection:
            selected = int(selection[0])
            self.handle.selected(self.entries[selected])

    def _cancel(self, event):
        self.handle.canceled()

    def _select_prev(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active - 1 >= 0:
                self.list.select_clear(0, END)
                self.list.selection_set(active - 1)
                self.list.see(active - 1)
                self.list.activate(active - 1)
                self.list.see(active - 1)

    def _select_next(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active + 1 < self.list.size():
                self.list.select_clear(0, END)
                self.list.selection_set(active + 1)
                self.list.see(active + 1)
                self.list.activate(active + 1)
                self.list.see(active + 1)

    def add_entry(self, entry):
        self.entries.append(entry)
        self.list.insert(END, self.handle.entry_to_string(entry))
        if len(self.entries) == 1:
            self.list.selection_set(0)
 
    def clear(self):
        self.entries = []
        self.list.delete(0, END)


class TreeViewerHandle(object):

    def entry_to_string(self, obj):
        return str(object)
    
    def get_children(self, obj):
        return []

    def selected(self, obj):
        pass
    
    def canceled(self):
        pass

    def focus_went_out(self):
        pass


class TreeViewer(object):

    def __init__(self, parent, handle):
        self.handle = handle
        self.entries = []
        self.frame = Frame(parent)
        label = Label(self.frame, text='Code Assist Proposals')
        self.list = Listbox(self.frame, selectmode=SINGLE)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        label.grid(row=0, column=0, columnspan=2)
        self.list.grid(row=1, column=0, sticky=N+E+W+S)
        scrollbar.grid(row=1, column=1, sticky=N+E+W+S)
        self.frame.grid(sticky=N+E+W+S)
        

    def _focus_out(self, event):
        self.handle.focus_went_out()

    def _open_selected(self, event):
        selection = self.list.curselection()
        if selection:
            selected = int(selection[0])
            self.handle.selected(self.entries[selected])

    def _cancel(self, event):
        self.handle.canceled()

    def _select_prev(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active - 1 >= 0:
                self.list.select_clear(0, END)
                self.list.selection_set(active - 1)
                self.list.see(active - 1)
                self.list.activate(active - 1)
                self.list.see(active - 1)

    def _select_next(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active + 1 < self.list.size():
                self.list.select_clear(0, END)
                self.list.selection_set(active + 1)
                self.list.see(active + 1)
                self.list.activate(active + 1)
                self.list.see(active + 1)

    def add_entry(self, entry):
        self.entries.append(entry)
        self.list.insert(END, self.handle.entry_to_string(entry))
        if len(self.entries) == 1:
            self.list.selection_set(0)
 
    def clear(self):
        self.entries = []
        self.list.delete(0, END)


