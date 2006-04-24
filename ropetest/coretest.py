import os
import unittest

from rope.core import Core, RopeException
from ropetest.projecttest import SampleProjectMaker

class CoreTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        Core.get_core().close_project()
        self.projectMaker = SampleProjectMaker()
        self.fileName = self.projectMaker.getSampleFileName()
        self.fileName2 = 'samplefile2.txt'
        file = open(self.fileName, 'w')
        file.write('sample text')
        file.close()
        Core.get_core().open_project(self.projectMaker.getRoot())
        self.textEditor = Core.get_core().open_file(self.fileName)
        self.project = Core.get_core().get_open_project()

    def tearDown(self):
        self.projectMaker.removeAll()
        os.remove(self.fileName)
        if os.path.exists(self.fileName2):
            os.remove(self.fileName2)
        unittest.TestCase.tearDown(self)

    def testOpeningFiles(self):
        self.assertEquals(self.projectMaker.getSampleFileContents(), self.textEditor.get_editor().get_text())

    def testActiveEditor(self):
        self.assertEquals(self.textEditor, Core.get_core().get_active_editor())
        newEditor = Core.get_core().open_file(self.fileName)
        self.assertEquals(newEditor, Core.get_core().get_active_editor())

    def testSaving(self):
        self.textEditor.get_editor().set_text('another text')
        Core.get_core().save_file()

    def testErrorWhenOpeningANonExistentFile(self):
        try:
            Core.get_core().open_file(self.fileName2)
            self.fail('Should have thrown exception; file doesn\'t exist')
        except RopeException:
            pass
    
    def testMakingNewFiles(self):
        editor = Core.get_core().create_file(self.fileName2)
        editor.get_editor().set_text('file2')
        editor.save()

    def testErrorWhenMakingAlreadyExistantFile(self):
        try:
            editor = Core.get_core().create_file(self.fileName)
            self.fail('Show have throws exception; file already exists')
        except RopeException:
            pass

    def testCreatingFolder(self):
        Core.get_core().create_folder('SampleFolder')

    def test_running_current_editor(self):
        self.project.create_file('sample.py')
        self.project.create_file('output.txt')
        sample_file = self.project.get_resource('sample.py')
        sample_file.write("file = open('output.txt', 'w')\nfile.write('run')\nfile.close()\n")
        Core.get_core().open_file('sample.py')
        runner = Core.get_core().run_active_editor()
        runner.wait_process()
        self.assertEquals('run', self.project.get_resource('output.txt').read())

    def test_not_reopening_editors(self):
        editor1 = Core.get_core().open_file(self.projectMaker.getSampleFileName())
        editor2 = Core.get_core().open_file(self.projectMaker.getSampleFileName())
        self.assertTrue(editor1 is editor2)
    
    def test_closing_editor(self):
        editor = Core.get_core().open_file(self.projectMaker.getSampleFileName())
        self.assertEquals(Core.get_core().get_active_editor(), editor)
        Core.get_core().close_active_editor()
        self.assertNotEquals(Core.get_core().get_active_editor(), editor)

    def test_closing_the_last_editor(self):
        Core.get_core().close_active_editor()
        self.assertTrue(Core.get_core().get_active_editor() is None)

if __name__ == '__main__':
    unittest.main()
