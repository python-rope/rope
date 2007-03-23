import Tkinter

import rope.ide.codeassist
import rope.ui.core
from rope.base import codeanalyze
from rope.ide import formatter, notes, generate
from rope.ui import registers
from rope.ui.actionhelpers import ConfirmEditorsAreSaved
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui.uihelpers import EnhancedList, EnhancedListHandle


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
    start, end = editor.get_region_offset()
    lines = codeanalyze.SourceLinesAdapter(editor.get_text())
    start_line = lines.get_line_number(start)
    end_line = lines.get_line_number(end)
    first_line = lines.get_line(start_line)
    action = 'comment'
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


core = rope.ui.core.Core.get_core()
core._add_menu_cascade(MenuAddress(['Source'], 's'), ['all', 'none'])
actions = []

actions.append(SimpleAction('correct_line_indentation',
                            do_correct_line_indentation, 'C-i',
                            MenuAddress(['Source', 'Correct Line Indentation'], 'i', 0),
                            ['python', 'rest']))
actions.append(SimpleAction('format_code',
                            do_format_code, 'C-c C-f',
                            MenuAddress(['Source', 'Remove Extra Spaces And Lines'], None, 0),
                            ['python']))

actions.append(SimpleAction('comment_line', comment_line, 'C-c c',
                            MenuAddress(['Source', 'Comment Line'], 'e', 0),
                            ['python']))
actions.append(SimpleAction('comment_region', comment_region, 'C-c C-c',
                            MenuAddress(['Source', 'Comment Region'], 'n', 0),
                            ['python']))

actions.append(SimpleAction('show_codetags', show_codetags, 'C-c a t',
                            MenuAddress(['Source', 'Show Codetags'], None, 1), ['python']))
actions.append(SimpleAction('show_errors', show_errors, 'C-c a e',
                            MenuAddress(['Source', 'Show Errors'], None, 1), ['python']))
actions.append(SimpleAction('show_warnings', show_warnings, 'C-c a w',
                            MenuAddress(['Source', 'Show Warnings'], None, 1), ['python']))
actions.append(SimpleAction('show_annotations', show_all, 'C-c a a',
                            MenuAddress(['Source', 'Show All Annotations'], None, 1), ['python']))


actions.append(
    SimpleAction('generate_variable', generate_variable, 'C-c n v',
                 MenuAddress(['Source', 'Generate Variable'], None, 2), ['python']))
actions.append(
    SimpleAction('generate_function', generate_function, 'C-c n f',
                 MenuAddress(['Source', 'Generate Function'], None, 2), ['python']))
actions.append(
    SimpleAction('generate_class', generate_class, 'C-c n c',
                 MenuAddress(['Source', 'Generate Class'], None, 2), ['python']))
actions.append(
    SimpleAction('generate_module', generate_module, 'C-c n m',
                 MenuAddress(['Source', 'Generate Module'], None, 2), ['python']))
actions.append(
    SimpleAction('generate_package', generate_package, 'C-c n p',
                 MenuAddress(['Source', 'Generate Package'], None, 2), ['python']))

actions.append(SimpleAction('memorize_location', registers.add_location, 'C-x m m',
                            MenuAddress(['Source', 'Memorize Location'], None, 3), ['all']))
actions.append(SimpleAction('remember_location', registers.goto_location, 'C-x m b',
                            MenuAddress(['Source', 'Remember Location'], None, 3)))
actions.append(SimpleAction('memorize_string', registers.add_string, 'C-x m s',
                            MenuAddress(['Source', 'Memorize String'], None, 3), ['all']))
actions.append(SimpleAction('remember_string', registers.insert_string, 'C-x m i',
                            MenuAddress(['Source', 'Remember String'], None, 3)))

for action in actions:
    core.register_action(action)
