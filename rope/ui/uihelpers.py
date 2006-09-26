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

    def __init__(self, parent, handle, title="List"):
        self.handle = handle
        self.entries = []
        self.frame = Frame(parent)
        label = Label(self.frame, text=title)
        self.list = Listbox(self.frame, selectmode=SINGLE)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Up>', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        self.list.bind('<Down>', self._select_next)
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
        return 'break'

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
        return 'break'

    def add_entry(self, entry):
        self.entries.append(entry)
        self.list.insert(END, self.handle.entry_to_string(entry))
        if len(self.entries) == 1:
            self.list.selection_set(0)
 
    def clear(self):
        self.entries = []
        self.list.delete(0, END)


class TreeViewHandle(object):

    def entry_to_string(self, obj):
        return str(obj)
    
    def get_children(self, obj):
        return []

    def selected(self, obj):
        pass
    
    def canceled(self):
        pass

    def focus_went_out(self):
        pass


class _TreeNodeInformation(object):

    def __init__(self, entry, level=0):
        self.entry = entry
        self.expanded = False
        self.children_count = 0
        self.level = level


class TreeView(object):

    def __init__(self, parent, handle, title='Tree'):
        self.handle = handle
        self.nodes = []
        self.frame = Frame(parent)
        label = Label(self.frame, text=title)
        self.list = Listbox(self.frame, selectmode=SINGLE, height=12, width=32)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<Control-g>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Up>', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        self.list.bind('<Down>', self._select_next)
        self.list.bind('<e>', self._expand_item)
        self.list.bind('<plus>', self._expand_item)
        self.list.bind('<c>', self._collapse_item)
        self.list.bind('<minus>', self._collapse_item)
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
            self.handle.selected(self.nodes[selected].entry)

    def _cancel(self, event):
        self.handle.canceled()

    def _select_entry(self, index):
        self.list.select_clear(0, END)
        self.list.selection_set(index)
        self.list.see(index)
        self.list.activate(index)
        self.list.see(index)
        
    def _select_prev(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active - 1 >= 0:
                self._select_entry(active - 1)
        return 'break'

    def _select_next(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active + 1 < self.list.size():
                self._select_entry(active + 1)
        return 'break'

    def _expand_item(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            self.expand(active)

    def _collapse_item(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            self.collapse(active)

    def _update_entry_text(self, index):
        node = self.nodes[index]
        entry = node.entry
        if len(self.handle.get_children(entry)) > 0:
            if node.expanded:
                expansion_sign = '-'
            else:
                expansion_sign = '+'
        else:
            expansion_sign = ' '
        level = node.level
        new_text = 4 * level * ' ' + expansion_sign + \
                   ' ' + self.handle.entry_to_string(entry)
        old_text = self.list.get(index)
        if old_text != new_text:
            old_selection = 0
            selection = self.list.curselection()
            if selection:
                old_selection = int(selection[0])
            self.list.delete(index)
            self.list.insert(index, new_text)
            self._select_entry(old_selection)
            
    def add_entry(self, entry, index=None, level=0):
        if index == None:
            index = self.list.size()
        self.nodes.insert(index, _TreeNodeInformation(entry, level=level))
        self.list.insert(index, 4 * level * '  ' +
                         self.handle.entry_to_string(entry))
        if len(self.nodes) == 1:
            self._select_entry(1)
        self._update_entry_text(index)
 
    def remove(self, entry_number):
        self.collapse(entry_number)
        self.nodes.pop(entry_number)
        self.list.delete(entry_number)
 
    def clear(self):
        self.nodes = []
        self.list.delete(0, END)

    def expand(self, entry_number):
        node = self.nodes[entry_number]
        if node.expanded:
            return
        new_children = self.handle.get_children(node.entry)
        node.children_count = len(new_children)
        node.expanded = True
        for index, child in enumerate(new_children):
            self.add_entry(child, entry_number + index + 1, node.level + 1)
        self._update_entry_text(entry_number)

    def collapse(self, entry_number):
        node = self.nodes[entry_number]
        if not node.expanded:
            return
        node.expanded = False
        for i in range(node.children_count):
            self.remove(entry_number + 1)
        self._update_entry_text(entry_number)


