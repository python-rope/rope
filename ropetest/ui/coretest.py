import os
import unittest

from rope.ui.core import Core, RopeException
from ropetest import testutils


class CoreTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        Core.get_core().close_project()
        self._make_sample_project()
        self.sample_file2 = 'samplefile2.txt'
        file_ = open(self.sample_file, 'w')
        file_.write('sample text')
        file_.close()
        Core.get_core().open_project(self.project_root)
        self.textEditor = Core.get_core().open_file(self.sample_file)
        self.project = Core.get_core().get_open_project()

    def _make_sample_project(self):
        self.sample_file = 'sample_file.txt'
        self.sample_path = os.path.join(self.project_root, 'sample_file.txt')
        os.mkdir(self.project_root)
        self.sample_folder = 'sample_folder'
        os.mkdir(os.path.join(self.project_root, self.sample_folder))
        sample = open(self.sample_path, 'w')
        sample.write('sample text\n')
        sample.close()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        unittest.TestCase.tearDown(self)

    def test_opening_files(self):
        self.assertEquals('sample text\n',
                          self.textEditor.get_editor().get_text())

    def test_active_editor(self):
        self.assertEquals(self.textEditor, Core.get_core().get_active_editor())
        newEditor = Core.get_core().open_file(self.sample_file)
        self.assertEquals(newEditor, Core.get_core().get_active_editor())

    def test_saving(self):
        self.textEditor.get_editor().set_text('another text')
        Core.get_core().save_active_editor()

    def test_error_when_opening_a_non_existent_file(self):
        try:
            Core.get_core().open_file(self.sample_file2)
            self.fail('Should have thrown exception; file doesn\'t exist')
        except RopeException:
            pass

    def test_making_new_files(self):
        editor = Core.get_core().create_file(self.sample_file2)
        editor.get_editor().set_text('file2')
        editor.save()

    def test_error_when_making_already_existant_file(self):
        try:
            editor = Core.get_core().create_file(self.sample_file)
            self.fail('Show have throws exception; file already exists')
        except RopeException:
            pass

    def test_creating_folders(self):
        Core.get_core().create_folder('SampleFolder')

    def test_not_reopening_editors(self):
        editor1 = Core.get_core().open_file(self.sample_file)
        editor2 = Core.get_core().open_file(self.sample_file)
        self.assertTrue(editor1 is editor2)

    def test_closing_editor(self):
        editor = Core.get_core().open_file(self.sample_file)
        self.assertEquals(Core.get_core().get_active_editor(), editor)
        Core.get_core().close_active_editor()
        self.assertNotEquals(Core.get_core().get_active_editor(), editor)

    def test_closing_the_last_editor(self):
        Core.get_core().close_active_editor()
        self.assertTrue(Core.get_core().get_active_editor() is None)

    def test_switching_active_editor(self):
        parent = self.project.root;
        parent.create_file('file1.txt')
        parent.create_file('file2.txt')
        editor1 = Core.get_core().open_file('file1.txt')
        editor2 = Core.get_core().open_file('file2.txt')
        self.assertEquals(editor2, Core.get_core().get_active_editor())
        Core.get_core().switch_active_editor()
        self.assertEquals(editor1, Core.get_core().get_active_editor())

    def test_saving_all(self):
        self.textEditor.get_editor().set_text('another text')
        text_editor2 = Core.get_core().create_file(self.sample_file2)
        text_editor2.get_editor().set_text('another text')
        file1 = self.project.get_resource(self.sample_file)
        file2 = self.project.get_resource(self.sample_file)
        Core.get_core().save_all_editors()
        self.assertEquals('another text', file1.read())
        self.assertEquals('another text', file2.read())


if __name__ == '__main__':
    unittest.main()
