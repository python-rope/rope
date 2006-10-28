import unittest

from rope.base.pycore import PyObject
from rope.base.project import Project
from ropetest import testutils
from rope.ui.fileactions import FileFinder

class FileFinderTest(unittest.TestCase):
    
    def setUp(self):
        super(FileFinderTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.finder = FileFinder(self.project)
        
        self.file1 = 'aa'
        self.file2 = 'abb'
        self.file3 = 'abc'
        self.file4 = 'b'
        self.parent = self.project.get_root_folder().create_folder('parent')
        self.parent.create_file(self.file1)
        self.parent.create_file(self.file2)
        self.parent.create_file(self.file3)
        self.parent.create_file(self.file4)
        
    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(FileFinderTest, self).tearDown()

    def testEmptyFinding(self):
        files = self.finder.find_files_starting_with('')
        self.assertEquals(4, len(files))

    def testFinding(self):
        self.assertEquals(3, len(self.finder.find_files_starting_with('a')))
        
    def testAbsoluteFinding(self):
        result = self.finder.find_files_starting_with('aa')
        self.assertEquals(1, len(result))
        self.assertEquals(self.file1, result[0].get_name())
        self.assertEquals(self.file2, self.finder.find_files_starting_with('abb')[0].get_name())

    def testSpecializedFinding(self):
        result = self.finder.find_files_starting_with('ab')
        self.assertEquals(2, len(result))

    def testEnsuringCorrectCaching(self):
        result0 = self.finder.find_files_starting_with('')
        self.assertEquals(4, len(result0))
        result1 = self.finder.find_files_starting_with('a')
        self.assertEquals(3, len(result1))
        result2 = self.finder.find_files_starting_with('ab')
        self.assertEquals(2, len(result2))
        result3 = self.finder.find_files_starting_with('aa')
        self.assertEquals(1, len(result3))
        result4 = self.finder.find_files_starting_with('a')
        self.assertEquals(3, len(result4))


if __name__ == '__main__':
    unittest.main()
