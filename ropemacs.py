from Pymacs import lisp

import rope.refactor.extract
import rope.refactor.inline
import rope.refactor.move
import rope.refactor.rename
from rope.base import project, libutils
from rope.contrib import codeassist


class interactive(object):

    def __init__(self, mode=''):
        self.mode = mode

    def __call__(self, func):
        func.interaction = self.mode
        return func


class RopeInterface(object):

    def __init__(self):
        self.project = None
        self.old_content = None

    def init(self):
        """Initialize rope mode"""
        lisp.add_hook(lisp.before_save_hook,
                      lisp.rope_before_save_actions)
        lisp.add_hook(lisp.after_save_hook,
                      lisp.rope_after_save_actions)
        lisp.add_hook(lisp.kill_emacs_hook,
                      lisp.rope_exiting_actions)

        actions = [
            ('C-x p o', lisp.rope_open_project),
            ('C-x p k', lisp.rope_close_project),
            ('C-x p u', lisp.rope_undo_refactoring),
            ('C-x p r', lisp.rope_redo_refactoring),
            ('C-c g', lisp.rope_goto_definition),
            ('C-c C-d', lisp.rope_show_doc),

            ('C-c r r', lisp.rope_rename),
            ('C-c r l', lisp.rope_extract_variable),
            ('C-c r m', lisp.rope_extract_method),
            ('C-c r i', lisp.rope_inline),
            ('C-c r v', lisp.rope_move),
            ('C-c r 1 r', lisp.rope_rename_current_module),
            ('C-c r 1 v', lisp.rope_move_current_module),
            ('C-c r 1 p', lisp.rope_module_to_package),

            ('C-c i o', lisp.rope_organize_imports)]
        for key, callback in actions:
            lisp.global_set_key(self._key_sequence(key), callback)

    def _key_sequence(self, sequence):
        result = []
        for key in sequence.split():
            if key.lower().startswith('c-'):
                number = ord(key[-1].upper()) - ord('A') + 1
                result.append(chr(number))
            else:
                result.append(key)
        return ''.join(result)

    def before_save_actions(self):
        if self.project is not None:
            resource = self._get_resource()
            if resource is not None and resource.exists():
                self.old_content = resource.read()
            else:
                self.old_content = ''

    def after_save_actions(self):
        if self.project is not None:
            libutils.report_change(self.project, lisp.buffer_file_name(),
                                   self.old_content)
            self.old_content = None

    def exiting_actions(self):
        if self.project is not None:
            self.close_project()

    @interactive('DRope Project Root Folder: ')
    def open_project(self, root):
        if self.project is not None:
            self.close_project()
        self.project = project.Project(root)

    @interactive()
    def close_project(self):
        if project is not None:
            self.project.close()
            self.project = None
            lisp.message('Project closed')

    @interactive('cUndo refactoring might change many files; proceed? (y)')
    def undo_refactoring(self, confirm):
        if chr(confirm) in ('\r', '\n', 'y'):
            self._check_project()
            for changes in self.project.history.undo():
                self._reload_buffers(changes.get_changed_resources())

    @interactive('cRedo refactoring might change many files; proceed? (y)')
    def redo_refactoring(self, confirm):
        if chr(confirm) in ('\r', '\n', 'y'):
            self._check_project()
            for changes in self.project.history.redo():
                self._reload_buffers(changes.get_changed_resources())

    def do_rename(self, newname, module=False):
        self._check_project()
        lisp.save_some_buffers()
        resource, offset = self._get_location()
        if module:
            offset = None
        renamer = rope.refactor.rename.Rename(self.project, resource, offset)
        changes = renamer.get_changes(newname, docs=True)
        self._perform(changes)

    @interactive('sNew Name: ')
    def rename(self, newname):
        self.do_rename(newname)

    @interactive('sNew Module Name: ')
    def rename_current_module(self, newname):
        self.do_rename(newname, module=True)

    @interactive()
    def move(self):
        mover = self._create_mover()
        if isinstance(mover, rope.refactor.move.MoveGlobal):
            lisp.call_interactively(lisp.rope_move_global)
        if isinstance(mover, rope.refactor.move.MoveModule):
            lisp.call_interactively(lisp.rope_move_module)
        if isinstance(mover, rope.refactor.move.MoveMethod):
            lisp.call_interactively(lisp.rope_move_method)

    def _create_mover(self, module=False):
        self._check_project()
        lisp.save_some_buffers()
        resource, offset = self._get_location()
        if module:
            offset = None
        return rope.refactor.move.create_move(self.project, resource, offset)

    @interactive('sDestination Module Name: ')
    def move_global(self, dest_module):
        mover = self._create_mover()
        destination = self.project.pycore.find_module(dest_module)
        self._perform(mover.get_changes(destination))

    @interactive('sDestination Attribute: ')
    def move_method(self, dest_attr):
        mover = self._create_mover()
        self._perform(mover.get_changes(dest_attr,
                                        mover.get_method_name()))

    @interactive('sDestination Package: ')
    def move_module(self, dest_package):
        mover = self._create_mover()
        destination = self.project.pycore.find_module(dest_package)
        self._perform(mover.get_changes(destination))

    @interactive('sDestination Package: ')
    def move_current_module(self, dest_package):
        mover = self._create_mover(module=True)
        destination = self.project.pycore.find_module(dest_package)
        self._perform(mover.get_changes(destination))

    @interactive()
    def module_to_package(self):
        self._check_project()
        lisp.save_buffer()
        packager = rope.refactor.ModuleToPackage(self.project,
                                                 self._get_resource())
        self._perform(packager.get_changes())

    def _do_extract(self, extractor, newname):
        self._check_project()
        lisp.save_buffer()
        resource = self._get_resource()
        start, end = self._get_region()
        extractor = extractor(self.project, resource, start, end)
        changes = extractor.get_changes(newname)
        self._perform(changes)

    @interactive('sNew Variable Name: ')
    def extract_variable(self, newname):
        self._do_extract(rope.refactor.extract.ExtractVariable, newname)

    @interactive('sNew Method Name: ')
    def extract_method(self, newname):
        self._do_extract(rope.refactor.extract.ExtractMethod, newname)

    @interactive()
    def inline(self):
        self._check_project()
        lisp.save_some_buffers()
        resource, offset = self._get_location()
        inliner = rope.refactor.inline.create_inline(
            self.project, resource, offset)
        self._perform(inliner.get_changes())

    @interactive()
    def organize_imports(self):
        self._check_project()
        lisp.save_buffer()
        organizer = rope.refactor.ImportOrganizer(self.project)
        self._perform(organizer.organize_imports(self._get_resource()))

    def _perform(self, changes):
        if changes is None:
            return
        self.project.do(changes)
        self._reload_buffers(changes.get_changed_resources())
        lisp.message(str(changes.description) + ' finished')

    def _get_region(self):
        offset1 = self._get_offset()
        lisp.exchange_point_and_mark()
        offset2 = self._get_offset()
        lisp.exchange_point_and_mark()
        return min(offset1, offset2), max(offset1, offset2)

    def _get_offset(self):
        return lisp.point() - 1

    @interactive()
    def goto_definition(self):
        self._check_project()
        resource, offset = self._get_location()
        definition = codeassist.get_definition_location(
            self.project, lisp.buffer_string(), offset, resource)
        if definition[0]:
            lisp.find_file(definition[0].real_path)
        if definition[1]:
            lisp.goto_line(definition[1])

    @interactive()
    def show_doc(self):
        self._check_project()
        resource, offset = self._get_location()
        docs = codeassist.get_doc(
            self.project, lisp.buffer_string(), offset, resource)
        if docs:
            pydoc_buffer = lisp.get_buffer_create('*rope-pydoc*')
            lisp.set_buffer(pydoc_buffer)
            lisp.erase_buffer()
            lisp.insert(docs)
            lisp.display_buffer(pydoc_buffer)

    def _get_location(self):
        resource = self._get_resource()
        offset = self._get_offset()
        return resource, offset

    def _get_resource(self):
        filename = lisp.buffer_file_name()
        resource = libutils.path_to_resource(self.project, filename, 'file')
        return resource

    def _check_project(self):
        if self.project is None:
            lisp.call_interactively(lisp.rope_open_project)
        else:
            self.project.validate(self.project.root)

    def _reload_buffers(self, changed_resources):
        for resource in changed_resources:
            buffer = lisp.find_buffer_visiting(resource.real_path)
            if buffer and resource.exists():
                lisp.set_buffer(buffer)
                lisp.revert_buffer(None, 1)


interface = RopeInterface()

init = interface.init
open_project = interface.open_project
close_project = interface.close_project
undo_refactoring = interface.undo_refactoring
redo_refactoring = interface.redo_refactoring

rename = interface.rename
extract_variable = interface.extract_variable
extract_method = interface.extract_method
inline = interface.inline
rename_current_module = interface.rename_current_module
module_to_package = interface.module_to_package
move = interface.move
move_global = interface.move_global
move_module = interface.move_module
move_method = interface.move_method
move_current_module = interface.move_current_module

organize_imports = interface.organize_imports

before_save_actions = interface.before_save_actions
after_save_actions = interface.after_save_actions
exiting_actions = interface.exiting_actions

goto_definition = interface.goto_definition
show_doc = interface.show_doc
