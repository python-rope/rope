import unittest

from rope.core import Core
from rope.searching import Searcher
from ropetest.mockeditortest import GraphicalEditorFactory, MockEditorFactory
from rope.indenter import PythonCodeIndenter
from rope.codeassist import CodeAssist

class GraphicalEditorTest(unittest.TestCase):
    '''This class only tests features that are specific to GraphicalEditor; see mockeditortest'''
    __factory = GraphicalEditorFactory()
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create()
        self.editor.set_text('sample text')
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def testMoveNextWord(self):
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get(), 'Expected <%c> but was <%c>' % (' ', self.editor.get()))

    def testMoveNextWordOnSpaces(self):
        self.editor.next_word()
        self.editor.insert(self.editor.get_end(), ' and\n')
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get())
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def testNextWordOnEnd(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.next_word()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    def testNextWordOnNewLine(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -1))
        self.editor.insert(self.editor.get_end(), '\non a new line')
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def testNextWordOnNewLine(self):
        self.editor.set_text('hello \n world\n')
        self.editor.next_word()
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get(), self.editor.get())

    def testNextOneCharacterWord(self):
        self.editor.set_text('1 2\n')
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get())
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def testPrevWordOnTheBegining(self):
        self.editor.prev_word()
        self.assertEquals('s', self.editor.get())

    def testPrevWord(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals('t', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('s', self.editor.get())

    def testPrevWordOnTheMiddleOfAWord(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -2))
        self.editor.prev_word()
        self.assertEquals('t', self.editor.get())

    def testPrevOneCharacterWord(self):
        self.editor.set_text('1 2 3')
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals('3', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('2', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('1', self.editor.get())

    def testDeletingNextWord(self):
        self.editor.delete_next_word()
        self.assertEquals(' text', self.editor.get_text())

    def testDeletingNextWordInTheMiddle(self):
        self.editor.set_insert(self.editor.get_index(2))
        self.editor.delete_next_word()
        self.assertEquals('sa text', self.editor.get_text())

    def testDeletingPrevWord(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.delete_prev_word()
        self.assertEquals('sample ', self.editor.get_text(), self.editor.get_text())

    def testDeletingPrevWordInTheMiddle(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -2))
        self.editor.delete_prev_word()
        self.assertEquals('sample xt', self.editor.get_text(), self.editor.get_text())

    def testDeletingPrevWordAtTheBeginning(self):
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.delete_prev_word()
        self.assertEquals('ple text', self.editor.get_text(), self.editor.get_text())

    def test_next_word_stopping_at_underline(self):
        self.editor.set_text('sample_text')
        self.editor.set_insert(self.editor.get_start())
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_prev_word_stopping_at_underline(self):
        self.editor.set_text('sample_text')
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(7), self.editor.get_insert())

    def test_next_word_stopping_at_capitals(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_start())
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_next_word_stopping_at_capitals2(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.next_word()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    # TODO: handle this case
    def xxx_test_next_word_stopping_at_capitals3(self):
        self.editor.set_text('sampleMYText')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(8), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals2(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_index(7))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_next_word_stopping_at_end_of_line(self):
        self.editor.set_text('sample \n   text')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(7), self.editor.get_insert())

    def test_next_word_stopping_at_start_of_line(self):
        self.editor.set_text('sample \n   text')
        self.editor.set_insert(self.editor.get_index(7))
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(8), self.editor.get_insert())

    def test_prev_word_stopping_at_end_of_line(self):
        self.editor.set_text('sample \n   text')
        self.editor.set_insert(self.editor.get_index(9))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(8), self.editor.get_insert())

    def test_prev_word_stopping_at_start_of_line(self):
        self.editor.set_text('sample \n   text')
        self.editor.set_insert(self.editor.get_index(8))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(7), self.editor.get_insert())

    def test_going_to_the_start(self):
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.goto_start()
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())

    def test_going_to_the_end(self):
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.goto_end()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

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
        self.editor.set_mark()
        self.editor.goto_end()
        self.editor.copy_region()
        self.editor.paste()
        self.assertEquals('sample textsample text', self.editor.get_text())

    def test_copying_in_the_middle(self):
        self.editor.next_word()
        self.editor.set_mark()
        self.editor.goto_end()
        self.editor.copy_region()
        self.editor.goto_start()
        self.editor.paste()
        self.assertEquals(' textsample text', self.editor.get_text())

    def test_cutting(self):
        self.editor.set_mark()
        self.editor.next_word()
        self.editor.cut_region()
        self.assertEquals(' text', self.editor.get_text())
        self.editor.paste()
        self.assertEquals('sample text', self.editor.get_text())

    def test_mark_not_set(self):
        self.editor.cut_region()
        self.editor.copy_region()
        self.assertEquals('sample text', self.editor.get_text())

    def test_clear_mark(self):
        self.editor.set_mark()
        self.editor.next_word()
        self.editor.clear_mark()
        self.editor.cut_region()
        self.assertEquals('sample text', self.editor.get_text())

    def test_when_insert_while_mark_precedes(self):
        self.editor.next_word()
        self.editor.set_mark()
        self.editor.goto_start()
        self.editor.cut_region()
        self.assertEquals(' text', self.editor.get_text())

    def test_swap_mark_and_insert(self):
        self.editor.set_mark()
        self.editor.next_word()
        self.editor.swap_mark_and_insert()
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())
        self.editor.cut_region()
        self.assertEquals(' text', self.editor.get_text())

    def test_no_mark_swap_mark_and_insert(self):
        self.editor.swap_mark_and_insert()
        self.assertEquals('sample text', self.editor.get_text())

    def test_swap_mark_and_insert_while_insert_precedes(self):
        self.editor.next_word()
        self.editor.set_mark()
        self.editor.goto_start()
        self.editor.swap_mark_and_insert()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())
        self.editor.cut_region()
        self.assertEquals(' text', self.editor.get_text())

    def test_insert_tab(self):
        self.editor.set_text('')
        self.editor.insert_tab()
        self.assertEquals((' ' * 4), self.editor.get_text())
        self.editor.insert_tab(self.editor.get_end())
        self.assertEquals((' ' * 8), self.editor.get_text())

    def test_current_line_number(self):
        self.assertEquals(1, self.editor.get_current_line_number())
        self.editor.set_text('sample\n text \n end')
        self.editor.set_insert(self.editor.get_index(9))
        self.assertEquals(2, self.editor.get_current_line_number())
        self.editor.set_insert(self.editor.get_end())
        self.assertEquals(3, self.editor.get_current_line_number())

    def test_resetting_undo_after_set_text(self):
        self.editor.set_text('sample text')
        self.editor.undo()
        self.editor.undo()
        self.assertEquals('sample text', self.editor.get_text())

    def test_get_current_offset(self):
        self.editor.set_text('sample text')
        self.editor.set_insert(self.editor.get_start())
        self.assertEquals(0, self.editor.get_current_offset())
        self.editor.set_insert(self.editor.get_end())
        self.assertEquals(11, self.editor.get_current_offset())

    def test_get_current_offset_multiline(self):
        self.editor.set_text('sample text\n another text \n and yet another')
        self.editor.set_insert(self.editor.get_index(20))
        self.assertEquals(20, self.editor.get_current_offset())
        self.editor.set_insert(self.editor.get_index(30))
        self.assertEquals(30, self.editor.get_current_offset())
        self.editor.set_insert(self.editor.get_index(40))
        self.assertEquals(40, self.editor.get_current_offset())

    def test_after_indenting_insert_position(self):
        self.editor.set_indenter(PythonCodeIndenter(self.editor))
        self.editor.set_text("print 'hello'\n        print 'hello'\n")
        self.editor.set_insert(self.editor.get_index(15))
        self.editor.correct_line_indentation()
        self.assertEquals(self.editor.get_index(14), self.editor.get_insert())

    def test_after_indenting_insert_position2(self):
        self.editor.set_indenter(PythonCodeIndenter(self.editor))
        self.editor.set_text("def f():\n        print 'hello'\n")
        self.editor.set_insert(self.editor.get_index(9))
        self.editor.correct_line_indentation()
        self.assertEquals(self.editor.get_index(13), self.editor.get_insert())

    def test_after_indenting_insert_position3(self):
        self.editor.set_indenter(PythonCodeIndenter(self.editor))
        self.editor.set_text("def f():\n        print 'hello'\n")
        self.editor.set_insert(self.editor.get_index(22))
        self.editor.correct_line_indentation()
        self.assertEquals(self.editor.get_index(18), self.editor.get_insert())

    def test_goto_definition(self):
        class GotoDefinitionCodeAssist(CodeAssist):
            def get_definition_location(self, *arg):
                return (None, 2)
        code_assist = GotoDefinitionCodeAssist()
        self.editor.set_code_assist(code_assist)
        self.editor.set_text('\ndef a_func():\n    pass\na_func()\n')
        self.editor.set_insert(self.editor.get_index(26))
        self.editor.goto_definition()
        self.assertEquals(2, self.editor.get_current_line_number())


if __name__ == '__main__':
    unittest.main()

