import unittest

from rope.editor import *
from rope.fileeditor import *
from rope.project import Project
from ropetest.mockeditor import MockEditor
from ropetest.projecttest import SampleProjectMaker

class FileEditorTest(unittest.TestCase):
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.text = MockEditor()
        self.projectMaker = SampleProjectMaker()
        self.projectMaker.make_project()
        self.fileName = self.projectMaker.get_sample_file_name()
        self.project = Project(self.projectMaker.get_root())
        self.editor = FileEditor(self.project, self.project.get_resource(self.fileName), self.text)
    
    def tearDown(self):
        self.projectMaker.remove_all()
        unittest.TestCase.tearDown(self)
        
    def test_creation(self):
        self.assertEquals(self.projectMaker.get_sample_file_contents(),
                          self.editor.get_editor().get_text())

    def test_saving(self):
        self.text.set_text('another text')
        self.editor.save()
        self.assertEquals('another text', self.project.get_resource(self.fileName).read())


if __name__ == '__main__':
    unittest.main()
