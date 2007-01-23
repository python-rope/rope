import unittest

import rope.base.history
from rope.base import exceptions, project
from rope.base.change import *
from ropetest import testutils


class HistoryTest(unittest.TestCase):

    def setUp(self):
        super(HistoryTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = project.Project(self.project_root)
        self.history = self.project.history

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(HistoryTest, self).tearDown()

    def test_undoing_writes(self):
        my_file = self.project.root.create_file('my_file.txt')
        my_file.write('text1')
        self.history.undo()
        self.assertEquals('', my_file.read())

    def test_moving_files(self):
        my_file = self.project.root.create_file('my_file.txt')
        my_file.move('new_file.txt')
        self.history.undo()
        self.assertEquals('', my_file.read())

    def test_moving_files_to_folders(self):
        my_file = self.project.root.create_file('my_file.txt')
        my_folder = self.project.root.create_folder('my_folder')
        my_file.move(my_folder.path)
        self.history.undo()
        self.assertEquals('', my_file.read())

    def test_simple_undo(self):
        my_file = self.project.root.create_file('my_file.txt')
        change = ChangeContents(my_file, '1')
        self.history.do(change)
        self.assertEquals('1', my_file.read())
        self.history.undo()
        self.assertEquals('', my_file.read())

    def test_simple_redo(self):
        my_file = self.project.root.create_file('my_file.txt')
        change = ChangeContents(my_file, '1')
        self.history.do(change)
        self.history.undo()
        self.history.redo()
        self.assertEquals('1', my_file.read())

    def test_simple_re_undo(self):
        my_file = self.project.root.create_file('my_file.txt')
        change = ChangeContents(my_file, '1')
        self.history.do(change)
        self.history.undo()
        self.history.redo()
        self.history.undo()
        self.assertEquals('', my_file.read())

    def test_multiple_undos(self):
        my_file = self.project.root.create_file('my_file.txt')
        change = ChangeContents(my_file, '1')
        self.history.do(change)
        change = ChangeContents(my_file, '2')
        self.history.do(change)
        self.history.undo()
        self.assertEquals('1', my_file.read())
        change = ChangeContents(my_file, '3')
        self.history.do(change)
        self.history.undo()
        self.assertEquals('1', my_file.read())
        self.history.redo()
        self.assertEquals('3', my_file.read())

    @testutils.assert_raises(exceptions.HistoryError)
    def test_undo_list_underflow(self):
        self.history.undo()

    @testutils.assert_raises(exceptions.HistoryError)
    def test_redo_list_underflow(self):
        self.history.redo()

    @testutils.assert_raises(exceptions.HistoryError)
    def test_undo_limit(self):
        my_file = self.project.root.create_file('my_file.txt')
        history = rope.base.history.History(maxundos=1)
        history.do(ChangeContents(my_file, '1'))
        history.do(ChangeContents(my_file, '2'))
        try:
            history.undo()
            history.undo()
        finally:
            self.assertEquals('1', my_file.read())


if __name__ == '__main__':
    unittest.main()
