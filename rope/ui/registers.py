import Tkinter
from rope.ui.uihelpers import (TreeViewHandle, TreeView, find_item_dialog,
                               SearchableList, SearchableListHandle)


class Registers(object):

    def __init__(self):
        self.locations = {}
        self.strings = {}

    def add_location(self, name, resource, line):
        self.locations[name] = (resource, line)

    def add_string(self, name, string):
        self.strings[name] = string

    def get_location(self, name):
        return self.locations[name]

    def get_string(self, name):
        return self.strings[name]

    def project_closed(self):
        self.locations.clear()


def _ask_name(name, callback):
    toplevel = Tkinter.Toplevel()
    toplevel.title('Add Register')
    label = Tkinter.Label(toplevel, text=(name.title() + ' Name:'))
    text = Tkinter.Entry(toplevel)
    def done(event):
        callback(text.get())
        toplevel.destroy()
    def cancel(event):
        toplevel.destroy()
    label.grid(row=0, column=0)
    text.grid(row=0, column=1)
    text.bind('<Control-g>', cancel)
    text.bind('<Control-g>', cancel)
    text.bind('<Escape>', cancel)
    text.bind('<Return>', done)
    text.focus_set()
    toplevel.grab_set()

def add_location(context):
    registers = context.core.registers
    def add(name):
        registers.add_location(name, context.resource, context.offset)
    _ask_name('location', add)

def add_string(context):
    registers = context.core.registers
    region = context.editor.get_region_offset()
    string = context.editor.get_text()[region[0]:region[1]]
    def add(name):
        registers.add_string(name, string)
    _ask_name('string', add)


class _LocationHandle(SearchableListHandle):

    def __init__(self, toplevel, context):
        self.toplevel = toplevel
        self.context = context

    def selected(self, entry):
        self.toplevel.destroy()
        resource, offset = entry[1]
        editor_manager = self.context.core.get_editor_manager()
        editor = editor_manager.get_resource_editor(resource).get_editor()
        editor.set_insert(editor.get_index(offset))

    def entry_to_string(self, entry):
        return '%s : <%s:%s>' % (entry[0], entry[1][0].path, entry[1][1])

    def matches(self, entry, text):
        return self.entry_to_string(entry).startswith(text)

    def canceled(self):
        self.toplevel.destroy()


def goto_location(context):
    toplevel = Tkinter.Toplevel()
    toplevel.title('Goto Location')
    location_list = SearchableList(toplevel, _LocationHandle(toplevel, context),
                                   title='Goto Location', width=35, height=12)
    for name, location in context.core.registers.locations.items():
        location_list.add_entry((name, location))

class _StringHandle(SearchableListHandle):

    def __init__(self, toplevel, context):
        self.toplevel = toplevel
        self.context = context

    def selected(self, entry):
        self.toplevel.destroy()
        string = self.context.core.registers.get_string(entry)
        editor = self.context.editor
        editor.insert(editor.get_insert(), string)

    def entry_to_string(self, entry):
        return entry

    def matches(self, entry, text):
        return entry.startswith(text)

    def canceled(self):
        self.toplevel.destroy()


def insert_string(context):
    toplevel = Tkinter.Toplevel()
    toplevel.title('Insert String')
    location_list = SearchableList(toplevel, _StringHandle(toplevel, context),
                                   title='Insert String', width=32, height=12)
    for name in context.core.registers.strings:
        location_list.add_entry(name)
