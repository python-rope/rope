import os
import unittest

from rope.ui.core import Core, RopeException
from ropetest.projecttest import SampleProjectMaker

class CoreTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        Core.get_core().close_project()
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.fileName = self.projectMaker.get_sample_file_name()
        self.fileName2 = 'samplefile2.txt'
        file_ = open(self.fileName, 'w')
        file_.write('sample text')
        file_.close()
        Core.get_core().open_project(self.projectMaker.get_root())
        self.textEditor = Core.get_core().open_file(self.fileName)
        self.project = Core.get_core().get_open_project()

    def tearDown(self):
        self.projectMaker.remove_all()
        os.remove(self.fileName)
        if os.path.exists(self.fileName2):
            os.remove(self.fileName2)
        unittest.TestCase.tearDown(self)

    def test_opening_files(self):
        self.assertEquals(self.projectMaker.get_sample_file_contents(),
                          self.textEditor.get_editor().get_text())

    def test_active_editor(self):
        self.assertEquals(self.textEditor, Core.get_core().get_active_editor())
        newEditor = Core.get_core().open_file(self.fileName)
        self.assertEquals(newEditor, Core.get_core().get_active_editor())

    def test_saving(self):
        self.textEditor.get_editor().set_text('another text')
        Core.get_core().save_active_editor()

    def test_error_when_opening_a_non_existent_file(self):
        try:
            Core.get_core().open_file(self.fileName2)
            self.fail('Should have thrown exception; file doesn\'t exist')
        except RopeException:
            pass

    def test_making_new_files(self):
        editor = Core.get_core().create_file(self.fileName2)
        editor.get_editor().set_text('file2')
        editor.save()

    def test_error_when_making_already_existant_file(self):
        try:
            editor = Core.get_core().create_file(self.fileName)
            self.fail('Show have throws exception; file already exists')
        except RopeException:
            pass

    def test_creating_folders(self):
        Core.get_core().create_folder('SampleFolder')

    def test_not_reopening_editors(self):
        editor1 = Core.get_core().open_file(self.projectMaker.get_sample_file_name())
        editor2 = Core.get_core().open_file(self.projectMaker.get_sample_file_name())
        self.assertTrue(editor1 is editor2)
    
    def test_closing_editor(self):
        editor = Core.get_core().open_file(self.projectMaker.get_sample_file_name())
        self.assertEquals(Core.get_core().get_active_editor(), editor)
        Core.get_core().close_active_editor()
        self.assertNotEquals(Core.get_core().get_active_editor(), editor)

    def test_closing_the_last_editor(self):
        Core.get_core().close_active_editor()
        self.assertTrue(Core.get_core().get_active_editor() is None)

    def test_switching_active_editor(self):
        parent = self.project.get_root_folder();
        parent.create_file('file1.txt')
        parent.create_file('file2.txt')
        editor1 = Core.get_core().open_file('file1.txt')
        editor2 = Core.get_core().open_file('file2.txt')
        self.assertEquals(editor2, Core.get_core().get_active_editor())
        Core.get_core().switch_active_editor()
        self.assertEquals(editor1, Core.get_core().get_active_editor())

    def test_saving_all(self):
        self.textEditor.get_editor().set_text('another text')
        text_editor2 = Core.get_core().create_file(self.fileName2)
        text_editor2.get_editor().set_text('another text')
        file1 = self.project.get_resource(self.fileName)
        file2 = self.project.get_resource(self.fileName)
        Core.get_core().save_all_editors()
        self.assertEquals('another text', file1.read())
        self.assertEquals('another text', file2.read())


if __name__ == '__main__':
    unittest.main()
