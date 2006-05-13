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
        self.fileName = self.projectMaker.getSampleFileName()
        self.project = Project(self.projectMaker.getRoot())
        self.editor = FileEditor(self.project, self.project.get_resource(self.fileName), self.text)
    
    def tearDown(self):
        self.projectMaker.removeAll()
        unittest.TestCase.tearDown(self)
        
    def testCreation(self):
        self.assertEquals(self.projectMaker.getSampleFileContents(),
                          self.editor.get_editor().get_text())

    def testSaving(self):
        self.text.set_text('another text')
        self.editor.save()
        self.assertEquals('another text', self.project.get_resource(self.fileName).read())


if __name__ == '__main__':
    unittest.main()
