import fnmatch
import re
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


class _BaseList(object):

    def __init__(self, parent, handle, title=None, get_focus=True,
                 height=14, width=50):
        self.handle = handle
        self.entries = []
        self.frame = Frame(parent)
        self.list = Listbox(self.frame, selectmode=SINGLE,
                            height=height, width=width)
        scrollbar = Scrollbar(self.frame, orient=VERTICAL)
        scrollbar['command'] = self.list.yview
        self.list.config(yscrollcommand=scrollbar.set)
        self.list.bind('<Return>', self._open_selected)
        self.list.bind('<space>', self._open_selected)
        self.list.bind('<Escape>', self._cancel)
        self.list.bind('<Control-g>', self._cancel)
        self.list.bind('<FocusOut>', self._focus_out)
        self.list.bind('<FocusIn>', self._focus_in)
        self.list.bind('<Control-p>', self._select_prev)
        self.list.bind('<Up>', self._select_prev)
        self.list.bind('k', self._select_prev)
        self.list.bind('<Control-n>', self._select_next)
        self.list.bind('<Down>', self._select_next)
        self.list.bind('j', self._select_next)
        self.list['selectmode'] = Tkinter.SINGLE
        if get_focus:
            self.list.focus_set()
        if title is not None:
            label = Label(self.frame, text=title)
            label.grid(row=0, column=0, columnspan=2)
        self.list.grid(row=1, column=0, sticky=N+E+W+S)
        scrollbar.grid(row=1, column=1, sticky=N+E+W+S)
        self.frame.grid(sticky=N+E+W+S)

    def _focus_out(self, event):
        self.handle.focus_went_out()

    def _focus_in(self, event):
        self.activate(self.get_active_index())

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
        self.list.select_set(Tkinter.ACTIVE)
        selection = self.list.curselection()
        if selection:
            return int(selection[0])
        return 0

    def get_active_entry(self):
        if self.entries:
            return self.entries[self.get_active_index()]


class EnhancedList(_BaseList):

    def __init__(self, *args, **kwds):
        super(EnhancedList, self).__init__(*args, **kwds)
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

    def update(self):
        index = self.get_active_index()
        if index > 0:
            entry = self.remove_entry(index)
            self.insert_entry(entry, index)
            self.activate(index)


class VolatileList(EnhancedList):
    """This is like an `EnhancedList` except you can move entries in it.

    You can use ``M-p`` and ``M-n`` or `move_up` and `move_down` methods
    to move entries in the list

    """

    def __init__(self, *args, **kwds):
        super(VolatileList, self).__init__(*args, **kwds)
        self.list.bind('<Alt-p>', lambda event: self.move_up())
        self.list.bind('<Alt-n>', lambda event: self.move_down())

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


class _DescriptionListHandle(EnhancedListHandle):

    def __init__(self, text, description, callback):
        self.text = text
        self.description = description
        self.callback = callback

    def entry_to_string(self, obj):
        return str(obj)

    def selected(self, obj):
        self.text['state'] = Tkinter.NORMAL
        self.text.delete('0.0', Tkinter.END)
        self.text.insert('0.0', self._get_description(obj))
        self.callback(self.text)
        self.text['state'] = Tkinter.DISABLED

    def _get_description(self, obj):
        return self.description(obj)

    def canceled(self):
        pass


class DescriptionList(object):

    def __init__(self, parent, title, description,
                 height=12, indexwidth=50, callback=lambda text: None):
        frame = Tkinter.Frame(parent)
        description_text = ScrolledText.ScrolledText(frame, height=height,
                                                     width=80)
        self.handle = _DescriptionListHandle(
            description_text, description, callback)
        self.list = EnhancedList(frame, self.handle, title,
                                 height=height, width=indexwidth)
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
        self.list = EnhancedList(parent, self.adapter,
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


def find_item_dialog(handle, title='Find', matches='Matches',
                     height=14, width=50):
    toplevel = Tkinter.Toplevel()
    toplevel.title(title)
    find_dialog = Tkinter.Frame(toplevel)
    name_label = Tkinter.Label(toplevel, text='Name')
    name = Tkinter.Entry(toplevel, width=width // 2)
    list_handle = _FindListViewAdapter(toplevel, handle)
    found = EnhancedList(find_dialog, list_handle, matches, get_focus=False,
                         height=height, width=width)
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


class SearchableListHandle(EnhancedListHandle):

    def matches(self, entry, text):
        pass


class SearchableList(object):

    def __init__(self, parent, handle, verb='Find', name='Item',
                 get_focus=True, height=14, width=50):
        self.handle = handle
        self.frame = Frame(parent)
        label1 = Label(self.frame, text=(verb + ' '+ name))
        self.text = Tkinter.Entry(self.frame)
        list_frame = Frame(self.frame)
        self.list = EnhancedList(list_frame, handle, name + 's', False,
                                 height=height, width=width)

        self.text.bind('<Return>', self._open_selected)
        self.text.bind('<Escape>', self._cancel)
        self.text.bind('<Control-g>', self._cancel)
        self.text.bind('<Any-KeyRelease>', self._text_changed)
        if get_focus:
            self.text.focus_set()
        label1.grid(row=0)
        self.text.grid(row=1)
        list_frame.grid(row=2)
        self.frame.grid(sticky=N+E+W+S)

    def _open_selected(self, event=None):
        self.handle.selected(self.list.get_active_entry())

    def _cancel(self, event=None):
        self.handle.canceled()

    def _text_changed(self, event=None):
        for index, entry in enumerate(self.list.get_entries()):
            if self.handle.matches(entry, self.text.get()):
                self.list.activate(index)
                break

    def add_entry(self, entry):
        self.list.add_entry(entry)


class ProgressBar(object):

    def __init__(self, parent):
        self.text = Tkinter.Label(parent, width=79, justify=Tkinter.LEFT)
        self.canvas = canvas = Tkinter.Canvas(parent, height=20)
        self.color = 'blue'
        self.back_color = canvas['bg']
        self.percent = 0
        canvas.create_rectangle(0, 0, canvas['width'],
                                canvas['height'], fill='')
        canvas.create_rectangle(0, 0, 0, canvas['height'],
                                fill=self.color, outline=self.color)
        self.text.grid(row=0)
        self.canvas.grid(row=1)

    def set_done_percent(self, percent):
        self.percent = percent
        self._draw_shape()

    def set_color(self, color):
        self.color = color
        self._draw_shape()

    def set_text(self, text):
        self.text['text'] = text

    def _draw_shape(self):
        width = int(self.canvas['width']) * self.percent // 100
        self.canvas.create_rectangle(0, 0, width, self.canvas['height'],
                                     fill=self.color)
        total_width = self.canvas['width']
        self.canvas.create_rectangle(width, 0, total_width,
                                     self.canvas['height'],
                                     fill=self.back_color)


class HelperMatcher(object):

    def __init__(self, all_entries, does_match):
        self.all_entries = all_entries
        self.last_keyword = None
        self.last_result = None
        self.does_match = does_match

    def find_matches(self, starting):
        if starting == self.last_keyword:
            return self.last_result
        entries = []
        if self.last_keyword is not None and \
           starting.startswith(self.last_keyword):
            entries = self.last_result
        else:
            entries = self.all_entries
        result = []
        for entry in entries:
            if self.does_match(starting, entry):
                result.append(entry)
        self.last_keyword = starting
        self.last_result = result
        return result

    def invalidate(self):
        self.last_keyword = None
        self.last_result = None


class DoesMatch(object):

    def __init__(self, to_search_text=str):
        self.cache = None
        self.to_search_text = to_search_text

    def __call__(self, pattern, entry):
        selector = self._get_selector(pattern)
        text = self.to_search_text(entry)
        if isinstance(text, basestring):
            return selector(text)
        if isinstance(text, list):
            for subtext in text:
                if selector(subtext):
                    return True
        return False

    def _get_selector(self, pattern):
        if self.cache is None or self.cache[0] != pattern:
            self.cache = (pattern, _create_selector(pattern))
        return self.cache[1]


def _create_selector(pattern):
    if '?' in pattern or '*' in pattern:
        return _RESelector(pattern)
    else:
        return _NormalSelector(pattern)


class _NormalSelector(object):

    def __init__(self, pattern):
        self.pattern = pattern

    def __call__(self, input_str):
        return input_str.startswith(self.pattern)


class _RESelector(object):

    def __init__(self, pattern):
        self.pattern = re.compile(fnmatch.translate(pattern + '*'))

    def __call__(self, input_str):
        return self.pattern.match(input_str)


def init_completing_entry(entry, completer):
    def complete(event):
        text = entry.get()
        completions = completer(text)
        if completions:
            prefix = completions[0]
            for word in completions:
                prefix = _common_prefix(prefix, word)
            entry.delete(0, 'end')
            entry.insert(0, prefix)
            entry.index('end')
    entry.bind('<Alt-slash>', complete)
    entry.bind('<Control-space>', complete)

def _common_prefix(prefix, word):
    for index, (c1, c2) in enumerate(zip(prefix, word)):
        if c1 != c2:
            return prefix[:index]
    return prefix[:min(len(prefix), len(word))]


def highlight_diffs(text):
    last = '0.0'
    current = '1.0'
    text.tag_config('red', foreground='#AA1111')
    text.tag_config('green', foreground='#11AA11')
    text.tag_config('blue', foreground='#1111AA')
    text.tag_config('grey', foreground='#9999BB')
    text.tag_config('sep', background='#9999A0')
    tag_map = {'+': 'green', '-': 'red', '?': 'grey', '@': 'blue', '=': 'sep'}
    while current != last:
        c = text.get(current)
        if c in tag_map:
            text.tag_add(tag_map[c], current, current + ' lineend +1c')
        last = current
        current = text.index(current + ' +1l')
