import ScrolledText
import Tkinter

import rope.ide.codeassist
import rope.ui.core
import rope.ui.testview
from rope.base import codeanalyze
from rope.ide import formatter, notes, generate, sort, outline
from rope.ui import spelldialog, registers
from rope.ui.actionhelpers import ConfirmEditorsAreSaved, StoppableTaskRunner
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui.uihelpers import (TreeView, TreeViewHandle, EnhancedList,
                               EnhancedListHandle)


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
    for node in (outline.PythonOutline(context.project).\
                 get_root_nodes(editor.get_text())):
        tree_view.add_entry(node)
    toplevel.grab_set()


class _CompletionListHandle(EnhancedListHandle):

    def __init__(self, editor, toplevel, start_offset):
        self.editor = editor
        self.toplevel = toplevel
        self.start_offset = start_offset

    def entry_to_string(self, proposal):
        mode = '  '
        if isinstance(proposal, rope.ide.codeassist.TemplateProposal):
            mode = 'T_'
        if isinstance(proposal, rope.ide.codeassist.CompletionProposal):
            if proposal.type is None:
                mode = proposal.kind[0].upper() + '_'
            else:
                mode = proposal.kind[0].upper() + proposal.type[0].upper()
        return mode + '  ' + proposal.name

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        if isinstance(selected, rope.ide.codeassist.TemplateProposal):
            _get_template_information(self.editor, selected, self.start_offset)
        else:
            self.editor.text.delete('0.0 +%dc' % self.start_offset,
                                    Tkinter.INSERT)
            self.editor.text.insert('0.0 +%dc' % self.start_offset,
                                    selected.name)
        self.toplevel.destroy()

    def focus_went_out(self):
        self.canceled()


class DoCodeAssist(object):

    def __call__(self, context):
        editor = context.get_active_editor().get_editor()
        source = editor.get_text()
        offset = editor.get_current_offset()
        result = rope.ide.codeassist.code_assist(
            context.project, source, offset, context.resource,
            templates=self._get_templates(context))
        proposals = rope.ide.codeassist.sorted_proposals(result)
        start_offset = rope.ide.codeassist.starting_offset(source, offset)
        toplevel = Tkinter.Toplevel()
        toplevel.title('Code Assist Proposals')
        handle = _CompletionListHandle(editor, toplevel, start_offset)
        enhanced_list = EnhancedList(
            toplevel, handle, title='Code Assist Proposals', height=9, width=30)
        for proposal in proposals:
            enhanced_list.add_entry(proposal)
        start_index = editor.text.index('0.0 +%dc' % start_offset)
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
        enhanced_list.list.bind('<Control-g>', lambda event: handle.canceled())
        toplevel.grab_set()

    _templates = None

    def _get_templates(self, context):
        if self._templates is None:
            templates = rope.ide.codeassist.default_templates()
            for name, definition in (context.core.get_prefs().
                                     get('templates', [])):
                templates[name] = rope.ide.codeassist.Template(definition)
            self._templates = templates
        return self._templates


def _get_template_information(editor, proposal, start_offset):
    template = proposal.template
    def apply_template(mapping):
        string = template.substitute(mapping)
        editor.text.delete('0.0 +%dc' % start_offset, Tkinter.INSERT)
        editor.text.insert('0.0 +%dc' % start_offset,
                         string)
        offset = template.get_cursor_location(mapping)
        editor.text.mark_set(Tkinter.INSERT, '0.0 +%dc' % (start_offset + offset))
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
        for var, entry in entries.items():
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
    toplevel.bind('<Escape>', lambda event: cancel())
    toplevel.bind('<Control-g>', lambda event: cancel())
    toplevel.bind('<Return>', lambda event: ok())
    frame.grid()


def do_goto_definition(context):
    editor = context.get_active_editor().get_editor()
    resource, lineno = rope.ide.codeassist.get_definition_location(
        context.project, editor.get_text(),
        editor.get_current_offset(), context.resource)
    if resource is not None:
        new_editor = context.core.get_editor_manager().\
                     get_resource_editor(resource).get_editor()
    else:
        new_editor = editor
    if lineno is not None:
        new_editor.goto_line(lineno)

def do_show_doc(context):
    if not context.get_active_editor():
        return
    editor = context.get_active_editor().get_editor()
    doc = rope.ide.codeassist.get_doc(
        context.project, editor.get_text(),
        editor.get_current_offset(), context.resource)
    if doc is not None:
        toplevel = Tkinter.Toplevel()
        toplevel.title('Show Doc')
        doc_text = ScrolledText.ScrolledText(toplevel, height=15, width=80)
        doc_text.grid(row=0, column=1,
                      sticky=Tkinter.N + Tkinter.E + Tkinter.W + Tkinter.S)
        doc_text.insert('0.0', doc)
        doc_text.mark_set('insert', '0.0')
        doc_text['state'] = Tkinter.DISABLED

        def close(event=None):
            toplevel.destroy()
        def next_page(event=None):
            doc_text.event_generate('<Next>')
        def prev_page(event=None):
            doc_text.event_generate('<Prior>')
        toplevel.bind('<Escape>', close)
        toplevel.bind('<Control-g>', close)
        toplevel.bind('<FocusOut>', close)
        toplevel.bind('<Control-v>', next_page)
        toplevel.bind('<Alt-v>', prev_page)
        toplevel.grab_set()
        doc_text.focus_set()

def do_run_module(context):
    if context.get_active_editor():
        context.get_core().get_open_project().get_pycore().\
                run_module(context.get_active_editor().get_file())

def run_tests(context):
    rope.ui.testview.run_unit_test(context.project, context.resource)

def run_soi(context):
    pycore = context.project.pycore
    pycore.analyze_module(context.resource)

class _OccurrenceListHandle(EnhancedListHandle):

    def __init__(self, toplevel, core, focus_set):
        self.toplevel = toplevel
        self.editor_manager = core.get_editor_manager()
        self.focus_set = focus_set

    def entry_to_string(self, entry):
        result = entry.resource.path + ' : ' + str(entry.offset)
        if entry.unsure:
            result += ' ?'
        return result

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        editor = self.editor_manager.get_resource_editor(
            selected.resource).get_editor()
        editor.set_insert(editor.get_index(selected.offset))
        self.focus_set()

    def focus_went_out(self):
        pass


def find_occurrences(context):
    resource = context.resource
    offset = context.editor.get_current_offset()
    def calculate(handle):
        return rope.ide.codeassist.find_occurrences(
            context.project, resource, offset,
            unsure=True, task_handle=handle)
    result = StoppableTaskRunner(calculate, title='Finding Occurrences')()
    enhanced_list = None
    def focus_set():
        enhanced_list.list.focus_set()
    toplevel = Tkinter.Toplevel()
    toplevel.title('Code Assist Proposals')
    enhanced_list = EnhancedList(
        toplevel, _OccurrenceListHandle(toplevel, context.get_core(),
                                        focus_set),
        title='Occurrences')
    for occurrence in result:
        enhanced_list.add_entry(occurrence)
    def close(event):
        toplevel.destroy()
    toplevel.bind('<Escape>', close)
    toplevel.bind('<Control-g>', close)
    enhanced_list.list.focus_set()


def _generate_element(context, kind):
    generator = generate.create_generate(
        kind, context.project, context.resource,
        context.editor.get_current_offset())
    changes = generator.get_changes()
    context.project.do(changes)
    resource, lineno = generator.get_location()
    editor = context.core.get_editor_manager().\
             get_resource_editor(resource).get_editor()
    editor.goto_line(lineno)

@ConfirmEditorsAreSaved
def generate_variable(context):
    _generate_element(context, 'variable')

@ConfirmEditorsAreSaved
def generate_function(context):
    _generate_element(context, 'function')

@ConfirmEditorsAreSaved
def generate_class(context):
    _generate_element(context, 'class')

@ConfirmEditorsAreSaved
def generate_module(context):
    _generate_element(context, 'module')

@ConfirmEditorsAreSaved
def generate_package(context):
    _generate_element(context, 'package')

def do_correct_line_indentation(context):
    if context.get_active_editor():
        context.get_active_editor().get_editor().correct_line_indentation()

def do_format_code(context):
    editor = context.editor
    result = formatter.Formatter().format(editor.get_text())
    if result != editor.get_text():
        editor.set_text(result, reset_editor=False)


def comment_line(context):
    editor = context.get_active_editor().get_editor()
    line_number = editor.get_current_line_number()
    _comment_line(editor, line_number)

def _comment_line(editor, line_number, action='shift'):
    line_editor = editor.line_editor()
    line = line_editor.get_line(line_number)
    if line.strip() == '':
        return
    if line.lstrip().startswith('#') and action != 'comment':
        line_editor.indent_line(line_number, -(line.index('#') + 1))
    elif action != 'uncomment':
        line_editor.insert_to_line(line_number, '#')


def comment_region(context):
    editor = context.get_active_editor().get_editor()
    start, end = context.region
    lines = codeanalyze.SourceLinesAdapter(editor.get_text())
    start_line = lines.get_line_number(start)
    end_line = lines.get_line_number(end)
    first_line = lines.get_line(start_line)
    action = 'comment'
    # IDEA: comments should be indented
    if first_line.lstrip().startswith('#'):
        action = 'uncomment'
    for i in range(start_line, end_line + 1):
        _comment_line(editor, i, action)

class _AnnotationListHandle(EnhancedListHandle):

    def __init__(self, toplevel, core):
        self.toplevel = toplevel
        self.editor_manager = core.get_editor_manager()
        self.resource = self.editor_manager.active_editor.get_file()

    def entry_to_string(self, entry):
        return str(entry[0]) + ': ' + entry[1]

    def canceled(self):
        self.toplevel.destroy()

    def selected(self, selected):
        editor = self.editor_manager.get_resource_editor(self.resource).get_editor()
        editor.goto_line(selected[0])

    def focus_went_out(self):
        pass


def _show_annotations(context, name, items):
    toplevel = Tkinter.Toplevel()
    toplevel.title('%s List' % name)
    enhanced_list = EnhancedList(
        toplevel, _AnnotationListHandle(toplevel, context.get_core()),
        title='%ss' % name)
    for item in items:
        enhanced_list.add_entry(item)
    def close(event):
        toplevel.destroy()
    enhanced_list.list.focus_set()

def show_codetags(context):
    tags = notes.Codetags().tags(context.resource.read())
    _show_annotations(context, 'Codetag', tags)

def show_errors(context):
    tags = notes.Errors().errors(context.resource.read())
    _show_annotations(context, 'Error', tags)

def show_warnings(context):
    tags = notes.Warnings().warnings(context.resource.read())
    _show_annotations(context, 'Warning', tags)

def show_all(context):
    result = notes.Codetags().tags(context.resource.read())
    result.extend(notes.Warnings().warnings(context.resource.read()))
    result.extend(notes.Errors().errors(context.resource.read()))
    result.sort()
    _show_annotations(context, 'Annotation', result)


_sort_mapping = {'a': 'alpha', 'k': 'kind',
                 'p': 'pydoc', 's': 'special', 'u': 'underlined'}

def sort_scopes(context, kind):
    sorter = sort.get_sorter(_sort_mapping[kind.lower()],
                             reverse=context.prefix)
    sort_scopes = sort.SortScopes(context.project,
                                  context.resource, context.offset)
    context.project.do(sort_scopes.get_changes(sorter=sorter))
    

def _generate_sort_actions(menu):
    for name in _sort_mapping.values():
        c = name[0].lower()
        sorter = sort.get_sorter(name)
        action_name = 'sort_by_' + name
        menu_name = str(sorter)
        yield SimpleAction(
            action_name, lambda context, c=c: sort_scopes(context, c),
            'C-c s ' + c,
            menu.child(menu_name.title(), c), ['python'])


core = rope.ui.core.Core.get_core()
core.add_menu_cascade(MenuAddress(['Source'], 's'), ['all', 'none'])
actions = []

actions.append(SimpleAction('code_assist', DoCodeAssist(), 'M-/',
                            MenuAddress(['Source', 'Code Assist (Auto-Complete)'], 'c'), ['python']))
actions.append(SimpleAction('goto_definition', do_goto_definition, 'C-c g',
                            MenuAddress(['Source', 'Goto Definition'], 'd'), ['python']))
actions.append(SimpleAction('show_doc', do_show_doc, 'C-c C-d',
                            MenuAddress(['Source', 'Show Doc'], 's'), ['python']))
actions.append(SimpleAction('quick_outline', do_quick_outline, 'C-c C-o',
                            MenuAddress(['Source', 'Quick Outline'], 'q'), ['python']))
actions.append(SimpleAction('find_occurrences', find_occurrences, 'C-c C-s',
                            MenuAddress(['Source', 'Find Occurrences'], 'f'), ['python']))

actions.append(SimpleAction('correct_line_indentation', do_correct_line_indentation, 'C-i',
                            MenuAddress(['Source', 'Correct Line Indentation'], 'i', 1),
                            ['python', 'rst']))
actions.append(SimpleAction('format_code', do_format_code, 'C-c C-f',
                            MenuAddress(['Source', 'Remove Extra Spaces And Lines'], None, 1),
                            ['python']))
actions.append(SimpleAction('comment_line', comment_line, 'C-c c',
                            MenuAddress(['Source', 'Comment Line'], 'e', 1),
                            ['python']))
actions.append(SimpleAction('comment_region', comment_region, 'C-c C-c',
                            MenuAddress(['Source', 'Comment Region'], 'n', 1),
                            ['python']))

run = MenuAddress(['Source', 'Run'], 'r', 2)
core.add_menu_cascade(run, ['python'])
actions.append(SimpleAction('run_module', do_run_module, 'C-c x p',
                            run.child('Run Module', 'm'), ['python']))
actions.append(SimpleAction('run_unit_tests', run_tests, 'C-c x t',
                            run.child('Run Unit Tests', 't'), ['python']))
actions.append(SimpleAction('run_soi', run_soi, 'C-c x s',
                            run.child('Run SOI On Module', 's'), ['python']))

annotes = MenuAddress(['Source', 'Annotations'], 'a', 2)
core.add_menu_cascade(annotes, ['python'])
actions.append(SimpleAction('show_codetags', show_codetags, 'C-c a t',
                            annotes.child('Show Codetags', 'c'), ['python']))
actions.append(SimpleAction('show_errors', show_errors, 'C-c a e',
                            annotes.child('Show Errors', 'e'), ['python']))
actions.append(SimpleAction('show_warnings', show_warnings, 'C-c a w',
                            annotes.child('Show Warnings', 'w'), ['python']))
actions.append(SimpleAction('show_annotations', show_all, 'C-c a a',
                            annotes.child('Show All Annotations', 'a'), ['python']))


generate_ = MenuAddress(['Source', 'Generate'], 'g', 2)
core.add_menu_cascade(generate_, ['python'])
actions.append(SimpleAction('generate_variable', generate_variable, 'C-c n v',
                            generate_.child('Generate Variable', 'v'), ['python']))
actions.append(SimpleAction('generate_function', generate_function, 'C-c n f',
                            generate_.child('Generate Function', 'f'), ['python']))
actions.append(SimpleAction('generate_class', generate_class, 'C-c n c',
                            generate_.child('Generate Class', 'c'), ['python']))
actions.append(SimpleAction('generate_module', generate_module, 'C-c n m',
                            generate_.child('Generate Module', 'm'), ['python']))
actions.append(SimpleAction('generate_package', generate_package, 'C-c n p',
                            generate_.child('Generate Package', 'p'), ['python']))

sort_ = MenuAddress(['Source', 'Sort Scopes'], 'o', 2)
core.add_menu_cascade(sort_, ['python'])
actions.extend(_generate_sort_actions(sort_))

memory = MenuAddress(['Source', 'Memory'], 'm', 2)
core.add_menu_cascade(memory, ['all', 'none'])
actions.append(SimpleAction('memorize_location', registers.add_location, 'C-x m m',
                            memory.child('Memorize Location', 'm'), ['all']))
actions.append(SimpleAction('remember_location', registers.goto_location, 'C-x m b',
                            memory.child('Remember Location', 'b')))
actions.append(SimpleAction('memorize_string', registers.add_string, 'C-x m s',
                            memory.child('Memorize String', 's'), ['all']))
actions.append(SimpleAction('remember_string', registers.insert_string, 'C-x m i',
                            memory.child('Remember String', 'i')))

spell = MenuAddress(['Source', 'Spell Checking'], 'p', 2)
core.add_menu_cascade(spell, ['all'])
actions.append(SimpleAction('spellcheck_word', spelldialog.check_word, 'M-$',
                            spell.child('Spell-Check Word', 'w'), ['all']))
actions.append(SimpleAction('spellcheck_region', spelldialog.check_region, 'C-x $ r',
                            spell.child('Spell-Check Region', 'r'), ['all']))
actions.append(SimpleAction('spellcheck_buffer', spelldialog.check_buffer, 'C-x $ b',
                            spell.child('Spell-Check Buffer', 'b'), ['all']))


for action in actions:
    core.register_action(action)
