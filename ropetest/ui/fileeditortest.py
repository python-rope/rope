import unittest
import Tkinter

from rope.base.project import Project
from rope.ui.editor import *
from rope.ui.fileeditor import *
from ropetest.projecttest import SampleProjectMaker
from ropetest.ui.mockeditortest import get_sample_editingcontext

class FileEditorTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.fileName = self.projectMaker.get_sample_file_name()
        self.project = Project(self.projectMaker.get_root())
        get_sample_editingcontext()
        self.editor = FileEditor(self.project, self.project.get_resource(self.fileName),
                                 GraphicalEditorFactory(Tkinter.Frame()))

    def tearDown(self):
        self.projectMaker.remove_all()
        unittest.TestCase.tearDown(self)

    def test_creation(self):
        self.assertEquals(self.projectMaker.get_sample_file_contents(),
                          self.editor.get_editor().get_text())

    def test_saving(self):
        self.editor.get_editor().set_text('another text')
        self.editor.save()
        self.assertEquals('another text', self.project.get_resource(self.fileName).read())


if __name__ == '__main__':
    unittest.main()
