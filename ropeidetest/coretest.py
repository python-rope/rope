import os
import unittest

from ropeide.core import Core, RopeError
from ropetest import testutils


class CoreTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self._make_sample_project()
        self.sample_file2 = 'samplefile2.txt'
        self.core = Core.get_core()
        self.core._init_x()
        self.core._init_menus()
        self.core.prefs.set('project_rope_folder', None)
        self.core.open_project(self.project_root)
        self.textEditor = self.core.open_file(self.sample_file)
        self.project = self.core.get_open_project()

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
        self.core.close_project()
        testutils.remove_recursively(self.project_root)
        unittest.TestCase.tearDown(self)

    def test_opening_files(self):
        self.assertEquals('sample text\n',
                          self.textEditor.get_editor().get_text())

    def test_active_editor(self):
        self.assertEquals(self.textEditor, self.core.get_active_editor())
        newEditor = self.core.open_file(self.sample_file)
        self.assertEquals(newEditor, self.core.get_active_editor())

    def test_saving(self):
        self.textEditor.get_editor().set_text('another text')
        self.core.save_active_editor()

    def test_error_when_opening_a_non_existent_file(self):
        try:
            self.core.open_file(self.sample_file2)
            self.fail('Should have thrown exception; file doesn\'t exist')
        except RopeError:
            pass

    def test_making_new_files(self):
        editor = self.core.create_file(self.sample_file2)
        editor.get_editor().set_text('file2')
        editor.save()

    def test_error_when_making_already_existent_file(self):
        try:
            editor = self.core.create_file(self.sample_file)
            self.fail('Show have throws exception; file already exists')
        except RopeError:
            pass

    def test_creating_folders(self):
        self.core.create_folder('SampleFolder')

    def test_not_reopening_editors(self):
        editor1 = self.core.open_file(self.sample_file)
        editor2 = self.core.open_file(self.sample_file)
        self.assertTrue(editor1 is editor2)

    def test_closing_editor(self):
        editor = self.core.open_file(self.sample_file)
        self.assertEquals(self.core.get_active_editor(), editor)
        self.core.close_active_editor()
        self.assertNotEquals(self.core.get_active_editor(), editor)

    def test_closing_the_last_editor(self):
        self.core.close_active_editor()
        self.assertTrue(self.core.get_active_editor() is None)

    def test_switching_active_editor(self):
        parent = self.project.root;
        parent.create_file('file1.txt')
        parent.create_file('file2.txt')
        editor1 = self.core.open_file('file1.txt')
        editor2 = self.core.open_file('file2.txt')
        self.assertEquals(editor2, self.core.get_active_editor())
        self.core.switch_active_editor()
        self.assertEquals(editor1, self.core.get_active_editor())

    def test_saving_all(self):
        self.textEditor.get_editor().set_text('another text')
        text_editor2 = self.core.create_file(self.sample_file2)
        text_editor2.get_editor().set_text('another text')
        file1 = self.project.get_resource(self.sample_file)
        file2 = self.project.get_resource(self.sample_file)
        self.core.save_all_editors()
        self.assertEquals('another text', file1.read())
        self.assertEquals('another text', file2.read())


if __name__ == '__main__':
    unittest.main()
