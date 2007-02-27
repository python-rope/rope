import ScrolledText
import Tkinter
from Tkinter import *

import rope.base.exceptions


class RopeUIError(rope.base.exceptions.RopeError):
    """Base exception for user interface parts of rope"""


def do_nothing(*args, **kws):
    pass


class EnhancedListHandle(object):

    def entry_to_string(self, obj):
        return str(obj)

    def selected(self, obj):
        pass

    def canceled(self):
        pass

    def focus_went_out(self):
        pass


class EnhancedList(object):

    def __init__(self, parent, handle, title="List", get_focus=True,
                 height=14, width=50):
        self.handle = handle
        self.entries = []
        self.frame = Frame(parent)
        label = Label(self.frame, text=title)
        self.list = Listbox(self.frame, selectmode=SINGLE,
                            height=height, width=width)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<space>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Up>', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        self.list.bind('<Down>', self._select_next)
        if get_focus:
            self.list.focus_set()
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
                self.activate(active - 1)
        return 'break'

    def _select_next(self, event):
        selection = self.list.curselection()
        if selection:
            active = int(selection[0])
            if active + 1 < self.list.size():
                self.activate(active + 1)
        return 'break'

    def activate(self, index):
        self.list.select_clear(0, END)
        self.list.selection_set(index)
        self.list.activate(index)
        self.list.see(index)

    def add_entry(self, entry):
        self.entries.append(entry)
        self.list.insert(END, self.handle.entry_to_string(entry))
        if len(self.entries) == 1:
            self.list.selection_set(0)

    def clear(self):
        self.entries = []
        self.list.delete(0, END)

    def get_active_index(self):
        selection = self.list.curselection()
        if selection:
            return int(selection[0])
        return 0

    def get_active_entry(self):
        if self.entries:
            return self.entries[self.get_active_index()]


class VolatileList(EnhancedList):

    def __init__(self, *args, **kwds):
        super(VolatileList, self).__init__(*args, **kwds)
        self.list.bind('<Alt-p>', lambda event: self.move_up())
        self.list.bind('<Alt-n>', lambda event: self.move_down())
        self.list.bind('<Control-v>', self._next_page)
        self.list.bind('<Next>', self._next_page)
        self.list.bind('<Alt-v>', self._prev_page)
        self.list.bind('<Prior>', self._prev_page)

    def _next_page(self, event):
        height = self.list['height']
        next = min(len(self.entries) - 1, self.get_active_index() + height)
        self.activate(next)
        return 'break'

    def _prev_page(self, event):
        height = self.list['height']
        next = max(0, self.get_active_index() - height)
        self.activate(next)
        return 'break'

    def insert_entry(self, entry, index=None):
        if index is None:
            index = len(self.entries)
        self.entries.insert(index, entry)
        self.list.insert(index, self.handle.entry_to_string(entry))
        if len(self.entries) == 1:
            self.list.selection_set(0)

    def remove_entry(self, index=None):
        if index is None:
            index = self.get_active_index()
        result = self.entries[index]
        self.list.delete(index)
        return self.entries.pop(index)

    def get_entries(self):
        return list(self.entries)

    def move_up(self):
        index = self.get_active_index()
        if index > 0:
            entry = self.remove_entry(index)
            self.insert_entry(entry, index - 1)
            self.activate(index - 1)

    def move_down(self):
        index = self.get_active_index()
        if index < len(self.entries) - 1:
            entry = self.remove_entry(index)
            self.insert_entry(entry, index + 1)
            self.activate(index + 1)

    def update(self):
        index = self.get_active_index()
        if index > 0:
            entry = self.remove_entry(index)
            self.insert_entry(entry, index)
            self.activate(index)


class _DescriptionListHandle(EnhancedListHandle):

    def __init__(self, text, description):
        self.text = text
        self.description = description

    def entry_to_string(self, obj):
        return str(obj)

    def selected(self, obj):
        self.text['state'] = Tkinter.NORMAL
        self.text.delete('0.0', Tkinter.END)
        self.text.insert('0.0', self._get_description(obj))
        self.text['state'] = Tkinter.DISABLED

    def _get_description(self, obj):
        return self.description(obj)

    def canceled(self):
        pass


class DescriptionList(object):

    def __init__(self, parent, title, description):
        frame = Tkinter.Frame(parent)

        description_text = ScrolledText.ScrolledText(frame, height=12, width=80)
        self.handle = _DescriptionListHandle(description_text, description)
        self.list = VolatileList(frame, self.handle, title)
        description_text.grid(row=0, column=1, sticky=N+E+W+S)
        frame.grid()

    def add_entry(self, obj):
        self.list.add_entry(obj)
        if self.list.list.size() == 1:
            self.handle.selected(obj)

    def get_selected(self):
        return self.list.get_active_entry()


class TreeViewHandle(object):

    def entry_to_string(self, obj):
        return str(obj)

    def get_children(self, obj):
        return []

    def selected(self, obj):
        """Return True if you want the node to be expanded/collapsed"""
        return True

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


class _TreeViewListAdapter(object):

    def __init__(self, tree_view, handle):
        self.tree_view = tree_view
        self.handle = handle

    def entry_to_string(self, node):
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
        return new_text

    def selected(self, node):
        if self.handle.selected(node.entry):
            index = self.tree_view.list.get_entries().index(node)
            self.tree_view.toggle(entry_number=index)

    def canceled(self):
        self.handle.canceled()

    def focus_went_out(self):
        self.handle.focus_went_out()


class TreeView(object):

    def __init__(self, parent, handle, title='Tree', height=12, width=32):
        self.handle = handle
        self.frame = Frame(parent)
        label = Label(self.frame, text=title)
        self.adapter = _TreeViewListAdapter(self, handle)
        self.list = VolatileList(parent, self.adapter,
                                 title, height=height, width=width)
        self.list.list.bind('<Control-g>', lambda event: self.adapter.canceled())
        self.list.list.bind('<e>', self._expand_item)
        self.list.list.bind('<plus>', self._expand_item)
        self.list.list.bind('<c>', self._collapse_item)
        self.list.list.bind('<minus>', self._collapse_item)

    def _expand_item(self, event):
        self.expand(self.list.get_active_index())

    def _collapse_item(self, event):
        self.collapse(self.list.get_active_index())

    def _update_entry_text(self, index):
        node = self.list.entries[index]
        self.list.remove_entry(index)
        self.list.insert_entry(node, index)
        self.list.activate(index)

    def add_entry(self, entry, index=None, level=0):
        self.list.insert_entry(_TreeNodeInformation(entry, level=level), index)

    def remove(self, entry_number):
        self.collapse(entry_number)
        self.list.remove_entry(entry_number)

    def clear(self):
        self.list.clear()

    def expand(self, entry_number):
        node = self.list.get_entries()[entry_number]
        if node.expanded:
            return
        new_children = self.handle.get_children(node.entry)
        node.children_count = len(new_children)
        node.expanded = True
        for index, child in enumerate(new_children):
            self.add_entry(child, entry_number + index + 1, node.level + 1)
        self._update_entry_text(entry_number)

    def collapse(self, entry_number):
        node = self.list.get_entries()[entry_number]
        if not node.expanded:
            return
        node.expanded = False
        for i in range(node.children_count):
            self.remove(entry_number + 1)
        self._update_entry_text(entry_number)

    def toggle(self, entry_number):
        node = self.list.get_entries()[entry_number]
        if not node.expanded:
            self.expand(entry_number)
        else:
            self.collapse(entry_number)

    def size(self):
        return len(self.list.get_entries())

    def get(self, index):
        return self.adapter.entry_to_string(self.list.get_entries()[index])


class FindItemHandle(object):

    def find_matches(self, starting):
        pass

    def selected(self, item):
        pass

    def to_string(self, item):
        pass

    def to_name(self, item):
        return self.to_string(item)


class _FindListViewAdapter(object):

    def __init__(self, toplevel, handle):
        self.toplevel = toplevel
        self.handle = handle

    def entry_to_string(self, obj):
        return self.handle.to_string(obj)

    def selected(self, obj):
        self.toplevel.destroy()
        if obj is not None:
            self.handle.selected(obj)

    def canceled(self):
        self.toplevel.destroy()

    def focus_went_out(self):
        pass


def find_item_dialog(handle, title='Find', matches='Matches'):
    toplevel = Tkinter.Toplevel()
    toplevel.title(title)
    find_dialog = Tkinter.Frame(toplevel)
    name_label = Tkinter.Label(toplevel, text='Name')
    name = Tkinter.Entry(toplevel)
    list_handle = _FindListViewAdapter(toplevel, handle)
    found = VolatileList(find_dialog, list_handle, matches, get_focus=False)
    def name_changed(event):
        if name.get() == '':
            result = []
        else:
            result = handle.find_matches(name.get())
        found.clear()
        for item in result:
            found.insert_entry(item, len(found.get_entries()))
    def complete_name(event):
        if not found.get_entries():
            return
        result = handle.to_name(found.get_entries()[0])
        for item in found.get_entries():
            common_index = 0
            for a, b in zip(result, handle.to_name(item)):
                if a == b:
                    common_index += 1
                else:
                    break
        if len(name.get()) < common_index:
            result = result[:common_index]
            name.delete('0', Tkinter.END)
            name.insert('0', result)
    name.bind('<Any-KeyRelease>', name_changed)
    name.bind('<Return>',
              lambda event: list_handle.selected(found.get_active_entry()))
    name.bind('<Escape>', lambda event: list_handle.canceled())
    name.bind('<Control-g>', lambda event: list_handle.canceled())
    name.bind('<Alt-slash>', complete_name)
    name.bind('<Control-space>', complete_name)
    name_label.grid(row=0, column=0, columnspan=2)
    name.grid(row=1, column=0, columnspan=2)
    find_dialog.grid(row=2, column=0, columnspan=2)
    name.focus_set()
    toplevel.grab_set()
