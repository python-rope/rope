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

    def test_writing_files_that_does_not_change_contents(self):
        my_file = self.project.root.create_file('my_file.txt')
        my_file.write('')
        self.project.history.undo()
        self.assertFalse(my_file.exists())
        

class IsolatedHistoryTest(unittest.TestCase):

    def setUp(self):
        super(IsolatedHistoryTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = project.Project(self.project_root)
        self.history = rope.base.history.History()
        self.file1 = self.project.root.create_file('file1.txt')
        self.file2 = self.project.root.create_file('file2.txt')

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(IsolatedHistoryTest, self).tearDown()

    def test_simple_undo(self):
        change = ChangeContents(self.file1, '1')
        self.history.do(change)
        self.assertEquals('1', self.file1.read())
        self.history.undo()
        self.assertEquals('', self.file1.read())

    @testutils.assert_raises(exceptions.HistoryError)
    def test_undo_limit(self):
        history = rope.base.history.History(maxundos=1)
        history.do(ChangeContents(self.file1, '1'))
        history.do(ChangeContents(self.file1, '2'))
        try:
            history.undo()
            history.undo()
        finally:
            self.assertEquals('1', self.file1.read())

    def test_simple_redo(self):
        change = ChangeContents(self.file1, '1')
        self.history.do(change)
        self.history.undo()
        self.history.redo()
        self.assertEquals('1', self.file1.read())

    def test_simple_re_undo(self):
        change = ChangeContents(self.file1, '1')
        self.history.do(change)
        self.history.undo()
        self.history.redo()
        self.history.undo()
        self.assertEquals('', self.file1.read())

    def test_multiple_undos(self):
        change = ChangeContents(self.file1, '1')
        self.history.do(change)
        change = ChangeContents(self.file1, '2')
        self.history.do(change)
        self.history.undo()
        self.assertEquals('1', self.file1.read())
        change = ChangeContents(self.file1, '3')
        self.history.do(change)
        self.history.undo()
        self.assertEquals('1', self.file1.read())
        self.history.redo()
        self.assertEquals('3', self.file1.read())

    @testutils.assert_raises(exceptions.HistoryError)
    def test_undo_list_underflow(self):
        self.history.undo()

    @testutils.assert_raises(exceptions.HistoryError)
    def test_redo_list_underflow(self):
        self.history.redo()

    def test_undoing_choosen_changes(self):
        change = ChangeContents(self.file1, '1')
        self.history.do(change)
        self.history.undo(change)
        self.assertEquals('', self.file1.read())
        self.assertFalse(self.history.undo_list)

    def test_undoing_choosen_changes2(self):
        change1 = ChangeContents(self.file1, '1')
        self.history.do(change1)
        self.history.do(ChangeContents(self.file1, '2'))
        self.history.undo(change1)
        self.assertEquals('', self.file1.read())
        self.assertFalse(self.history.undo_list)

    def test_undoing_choosen_changes_not_undoing_others(self):
        change1 = ChangeContents(self.file1, '1')
        self.history.do(change1)
        self.history.do(ChangeContents(self.file2, '2'))
        self.history.undo(change1)
        self.assertEquals('', self.file1.read())
        self.assertEquals('2', self.file2.read())

    def test_undoing_writing_after_moving(self):
        change1 = ChangeContents(self.file1, '1')
        self.history.do(change1)
        self.history.do(MoveResource(self.file1, 'file3.txt'))
        file3 = self.project.get_resource('file3.txt')
        self.history.undo(change1)
        self.assertEquals('', self.file1.read())
        self.assertFalse(file3.exists())

    def test_undoing_folder_movements_for_undoing_writes_inside_it(self):
        folder = self.project.root.create_folder('folder')
        file3 = folder.create_file('file3.txt')
        change1 = ChangeContents(file3, '1')
        self.history.do(change1)
        self.history.do(MoveResource(folder, 'new_folder'))
        new_folder = self.project.get_resource('new_folder')
        self.history.undo(change1)
        self.assertEquals('', file3.read())
        self.assertFalse(new_folder.exists())

    def test_undoing_changes_that_depend_on_a_dependant_change(self):
        change1 = ChangeContents(self.file1, '1')
        self.history.do(change1)
        changes = ChangeSet('2nd change')
        changes.add_change(ChangeContents(self.file1, '2'))
        changes.add_change(ChangeContents(self.file2, '2'))
        self.history.do(changes)
        self.history.do(MoveResource(self.file2, 'file3.txt'))
        file3 = self.project.get_resource('file3.txt')

        self.history.undo(change1)
        self.assertEquals('', self.file1.read())
        self.assertEquals('', self.file2.read())
        self.assertFalse(file3.exists())

    def test_undoing_writes_for_undoing_folder_movements_containing_it(self):
        folder = self.project.root.create_folder('folder')
        old_file = folder.create_file('file3.txt')
        change1 = MoveResource(folder, 'new_folder')
        self.history.do(change1)
        new_file = self.project.get_resource('new_folder/file3.txt')
        self.history.do(ChangeContents(new_file, '1'))
        self.history.undo(change1)
        self.assertEquals('', old_file.read())
        self.assertFalse(new_file.exists())

    @testutils.assert_raises(exceptions.HistoryError)
    def test_undoing_not_available_change(self):
        change = ChangeContents(self.file1, '1')
        self.history.undo(change)


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(HistoryTest))
    result.addTests(unittest.makeSuite(IsolatedHistoryTest))
    return result

if __name__ == '__main__':
    unittest.main()
