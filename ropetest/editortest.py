import unittest

from rope.core import Core
from rope.searching import Searcher
from ropetest.mockeditortest import GraphicalEditorFactory, MockEditorFactory
from rope.indenter import PythonCodeIndenter

class GraphicalEditorTest(unittest.TestCase):
    __factory = GraphicalEditorFactory()
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create()
        self.editor.set_text('sample text')
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def test_undo(self):
        self.editor.undo_separator()
        self.editor.insert(self.editor.get_end(), '.')
        self.assertEquals('sample text.', self.editor.get_text())
        self.editor.undo()
        self.assertEquals('sample text', self.editor.get_text(),self.editor.get_text())

    def test_redo(self):
        self.editor.undo_separator()
        self.editor.insert(self.editor.get_end(), '.')
        self.editor.undo()
        self.editor.redo()
        self.assertEquals('sample text.', self.editor.get_text(),self.editor.get_text())

    def test_nothing_to_undo(self):
        self.editor.undo()
        self.editor.undo()
        self.editor.undo()

    def test_nothing_to_redo(self):
        self.editor.redo()

    def test_copying(self):
        self.editor.setMark()
        self.editor.goToTheEnd()
        self.editor.copyRegion()
        self.editor.paste()
        self.assertEquals('sample textsample text', self.editor.get_text())

    def test_copying_in_the_middle(self):
        self.editor.nextWord()
        self.editor.setMark()
        self.editor.goToTheEnd()
        self.editor.copyRegion()
        self.editor.goToTheStart()
        self.editor.paste()
        self.assertEquals(' textsample text', self.editor.get_text())

    def test_cutting(self):
        self.editor.setMark()
        self.editor.nextWord()
        self.editor.cutRegion()
        self.assertEquals(' text', self.editor.get_text())
        self.editor.paste()
        self.assertEquals('sample text', self.editor.get_text())

    def test_mark_not_set(self):
        self.editor.cutRegion()
        self.editor.copyRegion()
        self.assertEquals('sample text', self.editor.get_text())

    def test_clear_mark(self):
        self.editor.setMark()
        self.editor.nextWord()
        self.editor.clearMark()
        self.editor.cutRegion()
        self.assertEquals('sample text', self.editor.get_text())

    def test_when_insert_while_mark_precedes(self):
        self.editor.nextWord()
        self.editor.setMark()
        self.editor.goToTheStart()
        self.editor.cutRegion()
        self.assertEquals(' text', self.editor.get_text())

    def test_swap_mark_and_insert(self):
        self.editor.setMark()
        self.editor.nextWord()
        self.editor.swapMarkAndInsert()
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())
        self.editor.cutRegion()
        self.assertEquals(' text', self.editor.get_text())

    def test_no_mark_swap_mark_and_insert(self):
        self.editor.swapMarkAndInsert()
        self.assertEquals('sample text', self.editor.get_text())

    def test_swap_mark_and_insert_while_insert_precedes(self):
        self.editor.nextWord()
        self.editor.setMark()
        self.editor.goToTheStart()
        self.editor.swapMarkAndInsert()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())
        self.editor.cutRegion()
        self.assertEquals(' text', self.editor.get_text())

    def test_insert_tab(self):
        self.editor.set_text('')
        self.editor.insertTab()
        self.assertEquals((' ' * 4), self.editor.get_text())
        self.editor.insertTab(self.editor.get_end())
        self.assertEquals((' ' * 8), self.editor.get_text())

    def test_clear_undo(self):
        self.editor.set_text('sample text')
        self.editor.clear_undo()
        self.editor.undo()
        self.assertEquals('sample text', self.editor.get_text())

    def test_current_line_number(self):
        self.assertEquals(1, self.editor.get_current_line_number())
        self.editor.set_text('sample\n text \n end')
        self.editor.set_insert(self.editor.get_index(9))
        self.assertEquals(2, self.editor.get_current_line_number())
        self.editor.set_insert(self.editor.get_end())
        self.assertEquals(3, self.editor.get_current_line_number())


if __name__ == '__main__':
    unittest.main()

