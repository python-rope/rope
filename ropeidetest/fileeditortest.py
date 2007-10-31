import unittest

import Tkinter

from ropeide.editor import *
from ropeide.fileeditor import *
from ropetest import testutils
from ropeidetest.mockeditortest import get_sample_editingcontext


class FileEditorTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.project_root = 'sample_project'
        self.project = testutils.sample_project(self.project_root)
        self._make_sample_project()
        self.fileName = self.sample_file
        get_sample_editingcontext()
        self.editor = FileEditor(self.project, self.project.get_resource(self.fileName),
                                 GraphicalEditorFactory(Tkinter.Frame()))

    def _make_sample_project(self):
        self.sample_file = 'sample_file.txt'
        self.sample_path = os.path.join(self.project_root, 'sample_file.txt')
        sample = open(self.sample_path, 'w')
        sample.write('sample text\n')
        sample.close()

    def tearDown(self):
        testutils.remove_project(self.project)
        unittest.TestCase.tearDown(self)

    def test_creation(self):
        self.assertEquals('sample text\n',
                          self.editor.get_editor().get_text())

    def test_saving(self):
        self.editor.get_editor().set_text('another text')
        self.editor.save()
        self.assertEquals('another text', self.project.get_resource(self.fileName).read())


if __name__ == '__main__':
    unittest.main()
