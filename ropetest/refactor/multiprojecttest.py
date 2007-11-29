import unittest

import rope.base.codeanalyze
import rope.refactor.occurrences
from rope.refactor import multiproject, rename
from ropetest import testutils


class MultiProjectRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(MultiProjectRefactoringTest, self).setUp()
        self.project1 = testutils.sample_project(foldername='testproject1')
        self.project2 = testutils.sample_project(
            foldername='testproject2', python_path=[self.project1.address])
        self.mod1 = self.project1.root.create_file('mod1.py')
        self.mod2 = self.project2.root.create_file('mod2.py')

    def tearDown(self):
        testutils.remove_project(self.project1)
        testutils.remove_project(self.project2)
        super(MultiProjectRefactoringTest, self).tearDown()

    def test_trivial_rename(self):
        self.mod1.write('var = 1\n')
        refactoring = multiproject.MultiProjectRefactoring(
            rename.Rename, [])
        renamer = refactoring(self.project1, self.mod1, 1)
        multiproject.perform(renamer.get_all_changes('newvar'))
        self.assertEquals('newvar = 1\n', self.mod1.read())

    def test_rename(self):
        self.mod1.write('var = 1\n')
        self.mod2.write('import mod1\nmyvar = mod1.var\n')
        refactoring = multiproject.MultiProjectRefactoring(
            rename.Rename, [self.project2])
        renamer = refactoring(self.project1, self.mod1, 1)
        multiproject.perform(renamer.get_all_changes('newvar'))
        self.assertEquals('newvar = 1\n', self.mod1.read())
        self.assertEquals('import mod1\nmyvar = mod1.newvar\n',
                          self.mod2.read())


if __name__ == '__main__':
    unittest.main()
