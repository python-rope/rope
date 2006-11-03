import Tkinter

import rope.ui.core
import rope.ui.testview
from rope.ui.menubar import MenuAddress
from rope.ui.extension import SimpleAction
from rope.ui.uihelpers import (TreeView, TreeViewHandle, EnhancedList,
                               EnhancedListHandle)


def do_correct_line_indentation(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().correct_line_indentation()

class _OutlineViewHandle(TreeViewHandle):
    
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


def do_quick_outline(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    toplevel = Tkinter.Toplevel()
    toplevel.title('Quick Outline')
    tree_view = TreeView(toplevel, _OutlineViewHandle(editor, toplevel),
                         title='Quick Outline')
    for node in context.editingtools.outline.get_root_nodes(editor.get_text()):
        tree_view.add_entry(node)
    tree_view.list.focus_set()
    toplevel.grab_set()

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
            self.editor.text.delete('0.0 +%dc' % self.result.start_offset,
                                    Tkinter.INSERT)
            self.editor.text.insert('0.0 +%dc' % self.result.start_offset,
                                    selected.name)
        else:
            _get_template_information(self.editor, self.result, selected)
        self.toplevel.destroy()

    def focus_went_out(self):
        self.canceled()

def do_code_assist(context):
    editor = context.get_active_editor().get_editor()
    result = context.editingtools.codeassist.assist(
        editor.get_text(), editor.get_current_offset(), context.resource)
    toplevel = Tkinter.Toplevel()
    toplevel.title('Code Assist Proposals')
    enhanced_list = EnhancedList(toplevel, _CompletionListHandle(editor, toplevel, result),
                                 title='Code Assist Proposals')
    proposals = rope.ide.codeassist.ProposalSorter(result).get_sorted_proposal_list()
    for proposal in proposals:
        enhanced_list.add_entry(proposal)
    start_index = editor.text.index('0.0 +%dc' % result.start_offset)
    initial_cursor_position = str(editor.text.index(Tkinter.INSERT))
    def key_pressed(event):
        import string
        if len(event.char) == 1 and (event.char.isalnum() or
                                     event.char in string.punctuation):
            editor.text.insert(Tkinter.INSERT, event.char)
        elif event.keysym == 'space':
            editor.text.insert(Tkinter.INSERT, ' ')
        elif event.keysym == 'BackSpace':
            editor.text.delete(Tkinter.INSERT + '-1c')
        elif editor.text.compare(initial_cursor_position, '>', Tkinter.INSERT):
            toplevel.destroy()
            return
        else:
            return
        new_name = editor.text.get(start_index, Tkinter.INSERT)
        enhanced_list.clear()
        for proposal in proposals:
            if proposal.name.startswith(new_name):
                enhanced_list.add_entry(proposal)
    enhanced_list.list.focus_set()
    enhanced_list.list.bind('<Any-KeyPress>', key_pressed)
    toplevel.grab_set()

def _get_template_information(editor, result, proposal):
    template = proposal.template
    def apply_template(mapping):
        string = template.substitute(mapping)
        editor.text.delete('0.0 +%dc' % result.start_offset, Tkinter.INSERT)
        editor.text.insert('0.0 +%dc' % result.start_offset,
                         string)
        offset = template.get_cursor_location(mapping)
        editor.text.mark_set(Tkinter.INSERT, '0.0 +%dc' % (result.start_offset + offset))
        editor.text.see(Tkinter.INSERT)

    if not template.variables():
        apply_template({})
        return
    toplevel = Tkinter.Toplevel()
    toplevel.title(proposal.name)
    frame = Tkinter.Frame(toplevel)
    label = Tkinter.Label(frame, text=('Variables in template %s' % proposal.name))
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
        label = Tkinter.Label(frame, text=var, width=20)
        label.grid(row=index+1, column=0)
        entry = Tkinter.Entry(frame, width=25)
        entry.insert(Tkinter.INSERT, var)
        entry.grid(row=index+1, column=1)
        entries[var] = entry
    ok_button = Tkinter.Button(frame, text='Done', command=ok)
    cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
    ok_button.grid(row=len(template.variables()) + 1, column=0)
    cancel_button.grid(row=len(template.variables()) + 1, column=1)
    frame.grid()

    
def do_goto_definition(context):
    editor = context.get_active_editor().get_editor()
    resource, lineno = context.editingtools.codeassist.get_definition_location(
        editor.get_text(), editor.get_current_offset(), context.resource)
    if resource is not None:
        new_editor = context.get_core().get_editor_manager().\
                     get_resource_editor(resource).get_editor()
    else:
        new_editor = editor
    if lineno is not None:
        new_editor.goto_line(lineno)

def do_show_doc(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    doc = context.editingtools.codeassist.get_doc(editor.get_text(),
                                                  editor.get_current_offset(),
                                                  context.resource)
    if doc is not None:
        toplevel = Tkinter.Toplevel()
        toplevel.title('Show Doc')
        doc_text = Tkinter.Label(toplevel, text='\n%s\n' % doc, justify=Tkinter.LEFT, 
                                 relief=Tkinter.GROOVE, width=80)
        doc_text.grid(sticky=Tkinter.W+Tkinter.N)
        def close(event=None):
            toplevel.destroy()
        toplevel.bind('<Escape>', close)
        toplevel.bind('<Control-g>', close)
        toplevel.bind('<FocusOut>', close)
        toplevel.grab_set()
        toplevel.focus_set()

def do_run_module(context):
    if context.get_active_editor():
        context.get_core().get_open_project().get_pycore().\
                run_module(context.get_active_editor().get_file())

def run_tests(context):
    rope.ui.testview.run_unit_test(context.project, context.resource)


# Registering code assist actions
core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['Code'], 'o'), ['python', 'rest'])
actions = []

actions.append(SimpleAction('Code Assist', do_code_assist, 'M-slash',
                            MenuAddress(['Code', 'Code Assist'], 'c'), ['python']))
actions.append(SimpleAction('Goto Definition', do_goto_definition, 'F3',
                            MenuAddress(['Code', 'Goto Definition'], 'g'), ['python']))
actions.append(SimpleAction('Show Doc', do_show_doc, 'F2',
                            MenuAddress(['Code', 'Show Doc'], 's'), ['python']))
actions.append(SimpleAction('Quick Outline', do_quick_outline, 'C-o',
                            MenuAddress(['Code', 'Quick Outline'], 'q'), ['python']))

actions.append(SimpleAction('Correct Line Indentation',
                            do_correct_line_indentation, 'C-i',
                            MenuAddress(['Code', 'Correct Line Indentation'], 'i', 1),
                            ['python', 'rest']))
actions.append(SimpleAction('Run Module', do_run_module, 'M-X p',
                            MenuAddress(['Code', 'Run Module'], 'm', 2), ['python']))
actions.append(SimpleAction('Run Test', run_tests, 'M-X t',
                            MenuAddress(['Code', 'Run Test'], 't', 2), ['python']))

for action in actions:
    core.register_action(action)
