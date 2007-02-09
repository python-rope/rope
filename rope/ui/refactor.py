import Tkinter

import rope.refactor.change_signature
import rope.refactor.encapsulate_field
import rope.refactor.extract
import rope.refactor.importutils
import rope.refactor.inline
import rope.refactor.introduce_factory
import rope.refactor.introduce_parameter
import rope.refactor.localtofield
import rope.refactor.move
import rope.refactor.rename
import rope.ui.core
from rope.refactor import ImportOrganizer
from rope.ui.actionhelpers import ConfirmEditorsAreSaved
from rope.ui.extension import SimpleAction
from rope.ui.menubar import MenuAddress
from rope.ui.uihelpers import (TreeViewHandle, TreeView,
                               DescriptionList, EnhancedListHandle,
                               VolatileList)


class PreviewAndCommitChanges(object):

    def __init__(self, project, changes):
        self.project = project
        self.changes = changes

    def preview(self):
        toplevel = Tkinter.Toplevel()
        toplevel.title('Preview Changes')

        def description(change):
            return change.get_description()
        description_list = DescriptionList(toplevel, 'Changes', description)
        for change in self.changes.changes:
            description_list.add_entry(change)

        frame = Tkinter.Frame(toplevel)
        def ok(event=None):
            toplevel.destroy()
            self.commit()
        def cancel(event=None):
            toplevel.destroy()
        ok_button = Tkinter.Button(frame, text='OK', command=ok)
        cancel_button = Tkinter.Button(frame, text='Cancel', command=cancel)
        ok_button.grid(row=1, column=0)
        #toplevel.bind('<Return>', lambda event: ok())
        toplevel.bind('<Escape>', lambda event: cancel())
        toplevel.bind('<Control-g>', lambda event: cancel())
        cancel_button.grid(row=1, column=1)
        frame.grid()

    def commit(self):
        self.project.do(self.changes)


class RefactoringDialog(object):

    def __init__(self, project, title):
        self.project = project
        self.title = title

    def show(self):
        self.toplevel = Tkinter.Toplevel()
        self.toplevel.title(self.title)
        self.toplevel.bind('<Escape>', lambda event: self._cancel())
        self.toplevel.bind('<Control-g>', lambda event: self._cancel())
        frame = self._get_dialog_frame()

        ok_button = Tkinter.Button(self.toplevel, text='Done', command=self._ok)
        preview_button = Tkinter.Button(self.toplevel, text='Preview', command=self._preview)
        cancel_button = Tkinter.Button(self.toplevel, text='Cancel', command=self._cancel)
        ok_button.grid(row=1, column=0)
        preview_button.grid(row=1, column=1)
        cancel_button.grid(row=1, column=2)
        frame.grid(row=0, columnspan=3)

    def _ok(self, event=None):
        PreviewAndCommitChanges(self.project, self._get_changes()).commit()
        self.toplevel.destroy()

    def _preview(self, event=None):
        PreviewAndCommitChanges(self.project, self._get_changes()).preview()
        self.toplevel.destroy()

    def _cancel(self, event=None):
        self.toplevel.destroy()


class RenameDialog(RefactoringDialog):

    def __init__(self, context, title, is_local=False, current_module=False):
        resource = context.resource
        editor = context.get_active_editor().get_editor()
        super(RenameDialog, self).__init__(context.project, title)
        self.is_local = is_local
        offset = editor.get_current_offset()
        if current_module:
            offset = None
        self.renamer = rope.refactor.rename.RenameRefactoring(
            context.project, resource, offset)

    def _get_changes(self):
        new_name = self.new_name_entry.get()
        return self.renamer.get_changes(new_name, in_file=self.is_local)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='New Name :')
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.insert(0, self.renamer.get_old_name())
        self.new_name_entry.select_range(0, Tkinter.END)
        self.new_name_entry.grid(row=0, column=1, columnspan=2)
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.focus_set()
        return frame


def rename(context):
    RenameDialog(context, 'Rename Refactoring').show()

def rename_module(context):
    RenameDialog(context, 'Rename Current Module Refactoring', current_module=True).show()

def local_rename(context):
    RenameDialog(context, 'Rename Refactoring', True).show()

def transform_module_to_package(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        changes = rope.refactor.TransformModuleToPackage(
            context.project, resource).get_changes()
        self.project.do(changes)


class ExtractDialog(RefactoringDialog):

    def __init__(self, context, do_extract, kind):
        editor = context.get_active_editor().get_editor()
        super(ExtractDialog, self).__init__(context.project,
                                            'Extract ' + kind)
        self.do_extract = do_extract
        self.kind = kind

    def _get_changes(self):
        return self.do_extract(self.new_name_entry.get())

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='New %s Name :' % self.kind)
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.grid(row=0, column=1)

        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.focus_set()
        return frame


def extract_method(context):
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.resource
        start_offset, end_offset = editor.get_region_offset()
        return rope.refactor.extract.ExtractMethodRefactoring(
            context.project, resource, start_offset,
            end_offset).get_changes(new_name)
    ExtractDialog(context, do_extract, 'Method').show()

def extract_variable(context):
    def do_extract(new_name):
        editor = context.get_active_editor().get_editor()
        resource = context.get_active_editor().get_file()
        start_offset, end_offset = editor.get_region_offset()
        return rope.refactor.extract.ExtractVariableRefactoring(
            context.project, resource, start_offset,
            end_offset).get_changes(new_name)
    ExtractDialog(context, do_extract, 'Variable').show()


class IntroduceFactoryDialog(RefactoringDialog):

    def __init__(self, context):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        super(IntroduceFactoryDialog, self).__init__(
            context.project, 'Introduce Factory Method Refactoring')
        self.introducer = rope.refactor.introduce_factory.IntroduceFactoryRefactoring(
            context.project, resource, editor.get_current_offset())

    def _get_changes(self):
        return self.introducer.get_changes(
            self.new_name_entry.get(), global_factory=self.global_factory_val.get())

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Factory Method Name :')
        self.new_name_entry = Tkinter.Entry(frame)

        self.global_factory_val = Tkinter.BooleanVar(False)
        static_factory_button = Tkinter.Radiobutton(frame, variable=self.global_factory_val,
                                                    value=False, text='Use static method')
        global_factory_button = Tkinter.Radiobutton(frame, variable=self.global_factory_val,
                                                    value=True, text='Use global function')
        self.new_name_entry.bind('<Return>', lambda event: self._ok())

        label.grid(row=0, column=0)
        self.new_name_entry.grid(row=0, column=1)
        static_factory_button.grid(row=1, column=0)
        global_factory_button.grid(row=1, column=1)
        self.new_name_entry.focus_set()
        return frame


def introduce_factory(context):
    IntroduceFactoryDialog(context).show()

class _ModuleViewHandle(TreeViewHandle):

    def __init__(self, project, toplevel, do_select):
        self.project = project
        self.toplevel = toplevel
        self.do_select = do_select

    def entry_to_string(self, resource):
        if resource.is_folder():
            result = resource.name
            if result == '':
                result = 'project root'
            return result
        else:
            return resource.name[:-3]

    def get_children(self, resource):
        if resource.is_folder():
            return [child for child in resource.get_children()
                    if not child.name.startswith('.') and
                    (child.is_folder() or child.name.endswith('.py'))]
        else:
            return []

    def selected(self, resource):
        self.toplevel.destroy()
        self.do_select(resource)

    def canceled(self):
        self.toplevel.destroy()

    def focus_went_out(self):
        pass


class MoveDialog(RefactoringDialog):

    def __init__(self, context, current_module=False):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        self.project = context.get_core().get_open_project()
        super(MoveDialog, self).__init__(context.project,
                                         'Move Refactoring')
        offset = editor.get_current_offset()
        if current_module:
            offset = None
        self.mover = rope.refactor.move.MoveRefactoring(
            context.project, resource, offset)

    def _get_changes(self):
        destination = self.project.get_pycore().find_module(self.new_name_entry.get())
        return self.mover.get_changes(destination)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Destination Module :')
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        self.new_name_entry.grid(row=0, column=1)
        def do_select(resource):
            name = rope.refactor.importutils.get_module_name(
                self.project.get_pycore(), resource)
            self.new_name_entry.delete(0, Tkinter.END)
            self.new_name_entry.insert(0, name)
        def browse():
            toplevel = Tkinter.Toplevel()
            toplevel.title('Choose Destination Module')
            tree_handle = _ModuleViewHandle(self.project, toplevel, do_select)
            tree_view = TreeView(toplevel, tree_handle, title='Destination Module')
            for folder in self.project.get_pycore().get_source_folders():
                tree_view.add_entry(folder)
            tree_view.list.focus_set()
            toplevel.grab_set()

        browse_button = Tkinter.Button(frame, text='...', command=browse)
        browse_button.grid(row=0, column=2)
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.bind('<Escape>', lambda event: self._cancel())
        self.new_name_entry.bind('<Control-g>', lambda event: self._cancel())
        frame.grid()
        self.new_name_entry.focus_set()
        return frame

def move(context):
    MoveDialog(context).show()

def move_module(context):
    MoveDialog(context, current_module=True).show()

class _Parameter(object):

    def __init__(self, name):
        self.name = name
        self.is_added = False
        self.default_and_value = None


def _get_parameter_index(definition_info, name):
    for index, pair in enumerate(definition_info.args_with_defaults):
        if pair[0] == name:
            return index
    index = len(definition_info.args_with_defaults)
    name = name[name.rindex('*') + 1:]
    if definition_info.args_arg is not None:
        if definition_info.args_arg == name:
            return index
        index += 1
    if definition_info.keywords_arg is not None and \
       definition_info.keywords_arg == name:
        return index

class _ParameterListHandle(EnhancedListHandle):

    def __init__(self, definition_info):
        self.definition_info = definition_info

    def entry_to_string(self, parameter):
        return parameter.name

    def selected(self, parameter):
        pass


class ChangeMethodSignatureDialog(RefactoringDialog):

    def __init__(self, context):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        self.project = context.get_core().get_open_project()
        super(ChangeMethodSignatureDialog, self).__init__(
            context.project, 'Change Method Signature Refactoring')
        self.signature = rope.refactor.change_signature.ChangeSignature(
            context.project, resource, editor.get_current_offset())
        self.definition_info = self.signature.get_definition_info()
        self.to_be_removed = []

    def _get_changes(self):
        changers = []
        parameters = self.param_list.get_entries()
        definition_info = self.definition_info
        for parameter in self.to_be_removed:
            if parameter.is_added:
                continue
            remover = rope.refactor.change_signature.ArgumentRemover(
                _get_parameter_index(definition_info, parameter.name))
            changers.append(remover)
            remover.change_definition_info(definition_info)
        for index, parameter in enumerate(parameters):
            if parameter.is_added:
                adder = rope.refactor.change_signature.ArgumentAdder(
                    index, parameter.name, *(parameter.default_and_value))
                changers.append(adder)
                adder.change_definition_info(definition_info)
        new_ordering = [_get_parameter_index(definition_info, param.name)
                        for param in parameters if not param.name.startswith('*')]
        changers.append(rope.refactor.change_signature.ArgumentReorderer(new_ordering))
        return self.signature.apply_changers(changers)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Change Method Signature :')
        label.grid(row=0, column=0)
        param_frame = Tkinter.Frame(frame)
        self.param_list = VolatileList(
            param_frame, _ParameterListHandle(self.definition_info),
            "Parameters")
        for pair in self.definition_info.args_with_defaults:
            self.param_list.add_entry(_Parameter(pair[0]))
        if self.definition_info.args_arg is not None:
            self.param_list.add_entry(
                _Parameter('*' + self.definition_info.args_arg))
        if self.definition_info.keywords_arg is not None:
            self.param_list.add_entry(
                _Parameter('**' + self.definition_info.keywords_arg))

        move_up = Tkinter.Button(frame, text='Move Up', width=20,
                                 command=lambda: self.param_list.move_up())
        move_down = Tkinter.Button(frame, text='Move Down', width=20,
                                   command=lambda: self.param_list.move_down())
        remove = Tkinter.Button(frame, text='Remove', width=20,
                                command=lambda: self._remove())
        add = Tkinter.Button(frame, text='Add New Parameter', width=20,
                             command=lambda: self._add())
        self.toplevel.bind('<Alt-r>', lambda event: self._remove())
        self.toplevel.bind('<Alt-a>', lambda event: self._add())
        param_frame.grid(row=0, column=0, rowspan=5)
        move_up.grid(row=0, column=1, sticky=Tkinter.S)
        move_down.grid(row=1, column=1, sticky=Tkinter.N)
        remove.grid(row=2, column=1, sticky=Tkinter.N)
        add.grid(row=3, column=1, sticky=Tkinter.N)
        frame.grid()
        frame.focus_set()
        return frame

    def _remove(self):
        self.to_be_removed.append(self.param_list.remove_entry())

    def _add(self):
        toplevel = Tkinter.Toplevel()
        toplevel.title('Add New Parameter')
        name_label = Tkinter.Label(toplevel, text='Name')
        name_entry = Tkinter.Entry(toplevel)
        default_label = Tkinter.Label(toplevel, text='Default')
        default_entry = Tkinter.Entry(toplevel)
        value_label = Tkinter.Label(toplevel, text='Value')
        value_entry = Tkinter.Entry(toplevel)
        name_label.grid(row=0, column=0)
        name_entry.grid(row=0, column=1)
        default_label.grid(row=1, column=0)
        default_entry.grid(row=1, column=1)
        value_label.grid(row=2, column=0)
        value_entry.grid(row=2, column=1)
        def ok(event=None):
            new_param = _Parameter(name_entry.get())
            value = None
            default = None
            if default_entry.get().strip() != '':
                default = default_entry.get()
            if value_entry.get().strip() != '':
                value = value_entry.get().strip()
            new_param.default_and_value = (default, value)
            new_param.is_added = True
            insertion_index = self.param_list.get_active_index()
            if self.param_list.get_entries():
                insertion_index += 1
            self.param_list.insert_entry(new_param, insertion_index)
            toplevel.destroy()
        def cancel(event=None):
            toplevel.destroy()
        toplevel.bind('<Return>', ok)
        toplevel.bind('<Escape>', cancel)
        toplevel.bind('<Control-g>', cancel)
        name_entry.focus_set()
        toplevel.grab_set()

def change_signature(context):
    ChangeMethodSignatureDialog(context).show()

class InlineArgumentDefaultDialog(RefactoringDialog):

    def __init__(self, context):
        resource = context.get_active_editor().get_file()
        editor = context.get_active_editor().get_editor()
        self.project = context.get_core().get_open_project()
        super(InlineArgumentDefaultDialog, self).__init__(
            context.project, 'Inline Argument Default')
        self.signature = rope.refactor.change_signature.ChangeSignature(
            context.project, resource, editor.get_current_offset())
        self.definition_info = self.signature.get_definition_info()

    def _get_changes(self):
        selected = self.param_list.get_active_entry()
        index = _get_parameter_index(self.definition_info, selected.name)
        return self.signature.inline_default(index)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='Change Method Signature :')
        label.grid(row=0, column=0)
        self.param_list = VolatileList(
            frame, _ParameterListHandle(self.definition_info),
            "Choose which to inline:")
        for pair in self.definition_info.args_with_defaults:
            if pair[1] is not None:
                self.param_list.add_entry(_Parameter(pair[0]))
        frame.grid()
        frame.focus_set()
        return frame

def inline_argument_default(context):
    InlineArgumentDefaultDialog(context).show()

class IntroduceParameterDialog(RefactoringDialog):

    def __init__(self, context, title):
        editor = context.get_active_editor().get_editor()
        super(IntroduceParameterDialog, self).__init__(context.project, title)
        self.renamer = rope.refactor.introduce_parameter.IntroduceParameter(
            context.project, context.resource, editor.get_current_offset())

    def _get_changes(self):
        new_name = self.new_name_entry.get()
        return self.renamer.get_changes(new_name)

    def _get_dialog_frame(self):
        frame = Tkinter.Frame(self.toplevel)
        label = Tkinter.Label(frame, text='New Parameter Name :')
        label.grid(row=0, column=0)
        self.new_name_entry = Tkinter.Entry(frame)
        #self.new_name_entry.insert(0, '')
        self.new_name_entry.select_range(0, Tkinter.END)
        self.new_name_entry.grid(row=0, column=1, columnspan=2)
        self.new_name_entry.bind('<Return>', lambda event: self._ok())
        self.new_name_entry.focus_set()
        return frame


def introduce_parameter(context):
    IntroduceParameterDialog(context, 'Introduce Parameter').show()


def _import_action(context, method):
    if not context.get_active_editor():
        return
    file_editor = context.get_active_editor()
    import_organizer = ImportOrganizer(context.project)
    if import_organizer:
        changes = method(import_organizer, file_editor.get_file())
        if changes is not None:
            context.project.do(changes)


def organize_imports(context):
    _import_action(context, ImportOrganizer.organize_imports)


def expand_star_imports(context):
    _import_action(context, ImportOrganizer.expand_star_imports)


def transform_froms_to_imports(context):
    _import_action(context, ImportOrganizer.transform_froms_to_imports)


def transform_relatives_to_absolute(context):
    _import_action(context, ImportOrganizer.transform_relatives_to_absolute)


def handle_long_imports(context):
    _import_action(context, ImportOrganizer.handle_long_imports)


def inline(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        changes = rope.refactor.inline.InlineRefactoring(
            context.project, resource,
            editor.get_current_offset()).get_changes()
        context.project.do(changes)


def encapsulate_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        changes = rope.refactor.encapsulate_field.EncapsulateFieldRefactoring(
            context.project, resource, editor.get_current_offset()).get_changes()
        context.project.do(changes)


def convert_local_to_field(context):
    if context.get_active_editor():
        fileeditor = context.get_active_editor()
        resource = fileeditor.get_file()
        editor = fileeditor.get_editor()
        changes = rope.refactor.localtofield.ConvertLocalToFieldRefactoring(
            context.project, resource,
            editor.get_current_offset()).get_changes()
        context.project.do(changes)


actions = []
actions.append(SimpleAction('rename', ConfirmEditorsAreSaved(rename), 'C-c r r',
                            MenuAddress(['Refactor', 'Rename'], 'n'), ['python']))
actions.append(SimpleAction('extract_method',
                            ConfirmEditorsAreSaved(extract_method, all=False), 'C-c r m',
                            MenuAddress(['Refactor', 'Extract Method'], 'x'), ['python']))
actions.append(SimpleAction('move', ConfirmEditorsAreSaved(move), 'C-c r v',
                            MenuAddress(['Refactor', 'Move'], 'm'), ['python']))
actions.append(SimpleAction('inline', ConfirmEditorsAreSaved(inline), 'C-c r i',
                            MenuAddress(['Refactor', 'Inline'], 'i'), ['python']))
actions.append(SimpleAction('extract_local_variable',
                            ConfirmEditorsAreSaved(extract_variable, all=False), 'C-c r l',
                            MenuAddress(['Refactor', 'Extract Local Variable'], 'l'), ['python']))
actions.append(SimpleAction('rename_in_file',
                            ConfirmEditorsAreSaved(local_rename, all=False), 'C-c r e',
                            MenuAddress(['Refactor', 'Rename in File'], 'e'), ['python']))
actions.append(SimpleAction('change_signature',
                            ConfirmEditorsAreSaved(change_signature), 'C-c r c',
                            MenuAddress(['Refactor', 'Change Method Signature'], 'c'),
                            ['python']))
actions.append(SimpleAction('introduce_factory',
                            ConfirmEditorsAreSaved(introduce_factory), 'C-c r f',
                            MenuAddress(['Refactor', 'Introduce Factory Method'], 'f', 1),
                            ['python']))
actions.append(SimpleAction('encapsulate_field',
                            ConfirmEditorsAreSaved(encapsulate_field), 'C-c r s',
                            MenuAddress(['Refactor', 'Encapsulate Field'], 's', 1),
                            ['python']))
actions.append(SimpleAction('introduce_parameter',
                            ConfirmEditorsAreSaved(introduce_parameter), 'C-c r p',
                            MenuAddress(['Refactor', 'Introduce Parameter'], None, 1),
                            ['python']))
actions.append(SimpleAction('local_to_field',
                            ConfirmEditorsAreSaved(convert_local_to_field), None,
                            MenuAddress(['Refactor', 'Convert Local Variable to Field'], 'b', 1),
                            ['python']))
actions.append(SimpleAction('inline_argument_default',
                            ConfirmEditorsAreSaved(inline_argument_default), None,
                            MenuAddress(['Refactor', 'Inline Argument Default'], 'g', 1),
                            ['python']))
actions.append(SimpleAction('module_to_package',
                            ConfirmEditorsAreSaved(transform_module_to_package), None,
                            MenuAddress(['Refactor', 'Transform Module to Package'], 't', 1),
                            ['python']))
actions.append(SimpleAction('rename_current_module',
                            ConfirmEditorsAreSaved(rename_module), 'C-c r 1 r',
                            MenuAddress(['Refactor', 'Rename Current Module'], None, 1),
                            ['python']))
actions.append(SimpleAction('move_current_module',
                            ConfirmEditorsAreSaved(move_module), 'C-c r 1 v',
                            MenuAddress(['Refactor', 'Move Current Module'], None, 1),
                            ['python']))
actions.append(SimpleAction('organize_imports',
                            ConfirmEditorsAreSaved(organize_imports, all=False), 'C-c i o',
                            MenuAddress(['Refactor', 'Organize Imports'], 'o', 2), ['python']))
actions.append(SimpleAction('expand_star_imports',
                            ConfirmEditorsAreSaved(expand_star_imports, all=False), 'C-c i x',
                            MenuAddress(['Refactor', 'Expand Star Imports'], 'p', 2),
                            ['python']))
actions.append(SimpleAction('relative_to_absolute',
                            ConfirmEditorsAreSaved(transform_relatives_to_absolute, all=False), 'C-c i a',
                            MenuAddress(['Refactor', 'Transform Relatives to Absolute'], 'a', 2),
                            ['python']))
actions.append(SimpleAction('from_to_import',
                            ConfirmEditorsAreSaved(transform_froms_to_imports, all=False), 'C-c i n',
                            MenuAddress(['Refactor', 'Transform Froms to Imports'], 'r', 2),
                            ['python']))
actions.append(SimpleAction('handle_long_imports',
                            ConfirmEditorsAreSaved(handle_long_imports, all=False), 'C-c i l',
                            MenuAddress(['Refactor', 'Handle Long Imports'], None, 2),
                            ['python']))

core = rope.ui.core.get_core()
core._add_menu_cascade(MenuAddress(['Refactor'], 't'), ['python'])
for action in actions:
    core.register_action(action)
