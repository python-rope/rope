import unittest

from rope.refactoring import PythonRefactoring
from rope.project import Project
from ropetest import testutils

class RefactoringTest(unittest.TestCase):

    def setUp(self):
        super(RefactoringTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.refactoring = PythonRefactoring(self.project.get_pycore())

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RefactoringTest, self).tearDown()

    def test_simple_global_variable_renaming(self):
        refactored = self.refactoring.rename('a_var = 20\n', 2, 'new_var')
        self.assertEquals('new_var = 20\n', refactored)

    def test_variable_renaming_only_in_its_scope(self):
        refactored = self.refactoring.rename('a_var = 20\ndef a_func():\n    a_var = 10\n', 32, 'new_var')
        self.assertEquals('a_var = 20\ndef a_func():\n    new_var = 10\n', refactored)

    def test_not_renaming_dot_name(self):
        refactored = self.refactoring.rename("replace = True\n'aaa'.replace('a', 'b')\n", 1, 'new_var')
        self.assertEquals("new_var = True\n'aaa'.replace('a', 'b')\n", refactored)
    
    def test_renaming_multiple_names_in_the_same_line(self):
        refactored = self.refactoring.rename('a_var = 10\na_var = 10 + a_var / 2\n', 2, 'new_var')
        self.assertEquals('new_var = 10\nnew_var = 10 + new_var / 2\n', refactored)


if __name__ == '__main__':
    unittest.main()

