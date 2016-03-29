try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.refactor import multiproject, rename, move
from ropetest import testutils


class MultiProjectRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(MultiProjectRefactoringTest, self).setUp()
        self.project1 = testutils.sample_project(foldername='testproject1')
        self.project2 = testutils.sample_project(foldername='testproject2')
        self.mod1 = self.project1.root.create_file('mod1.py')
        self.other = self.project1.root.create_file('other.py')
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

    def test_move(self):
        self.mod1.write('def a_func():\n    pass\n')
        self.mod2.write('import mod1\nmyvar = mod1.a_func()\n')
        refactoring = multiproject.MultiProjectRefactoring(
            move.create_move, [self.project2])
        renamer = refactoring(self.project1, self.mod1,
                              self.mod1.read().index('_func'))
        multiproject.perform(renamer.get_all_changes(self.other))
        self.assertEquals('', self.mod1.read())
        self.assertEquals('def a_func():\n    pass\n', self.other.read())
        self.assertEquals('import other\nmyvar = other.a_func()\n',
                          self.mod2.read())

    def test_rename_from_the_project_not_containing_the_change(self):
        self.project2.get_prefs().add('python_path', self.project1.address)
        self.mod1.write('var = 1\n')
        self.mod2.write('import mod1\nmyvar = mod1.var\n')
        refactoring = multiproject.MultiProjectRefactoring(
            rename.Rename, [self.project1])
        renamer = refactoring(self.project2, self.mod2,
                              self.mod2.read().rindex('var'))
        multiproject.perform(renamer.get_all_changes('newvar'))
        self.assertEquals('newvar = 1\n', self.mod1.read())
        self.assertEquals('import mod1\nmyvar = mod1.newvar\n',
                          self.mod2.read())


if __name__ == '__main__':
    unittest.main()
