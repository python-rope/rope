import unittest
import Tkinter

import rope.ui.editingtools
from rope.ui.core import Core
from ropetest.ui.mockeditortest import GraphicalEditorFactory, MockEditorFactory
from rope.ui.indenter import PythonCodeIndenter
from rope.ui.editor import _TextChangeInspector
from rope.codeassist import CodeAssist


class GraphicalEditorTest(unittest.TestCase):
    '''This class only tests features that are specific to GraphicalEditor; see mockeditortest'''
    
    __factory = GraphicalEditorFactory(Tkinter.Frame())
    
    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create(rope.ui.editingtools.NormalEditingTools())
        self.editor.set_text('sample text')
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def test_move_next_word(self):
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get(), 'Expected <%c> but was <%c>' % (' ', self.editor.get()))

    def test_move_next_word_on_spaces(self):
        self.editor.next_word()
        self.editor.insert(self.editor.get_end(), ' and\n')
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get())
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def test_next_word_on_end(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.next_word()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    def test_next_word_on_new_line(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -1))
        self.editor.insert(self.editor.get_end(), '\non a new line')
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def test_next_word_on_new_line(self):
        self.editor.set_text('hello \n world\n')
        self.editor.next_word()
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get(), self.editor.get())

    def test_next_one_character_word(self):
        self.editor.set_text('1 2\n')
        self.editor.next_word()
        self.assertEquals(' ', self.editor.get())
        self.editor.next_word()
        self.assertEquals('\n', self.editor.get())

    def test_prev_word_on_the_begining(self):
        self.editor.prev_word()
        self.assertEquals('s', self.editor.get())

    def test_prev_word(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals('t', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('s', self.editor.get())

    def test_prev_word_on_the_middle_of_a_word(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -2))
        self.editor.prev_word()
        self.assertEquals('t', self.editor.get())

    def test_prev_one_character_word(self):
        self.editor.set_text('1 2 3')
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals('3', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('2', self.editor.get())
        self.editor.prev_word()
        self.assertEquals('1', self.editor.get())

    def test_deleting_next_word(self):
        self.editor.delete_next_word()
        self.assertEquals(' text', self.editor.get_text())

    def test_deleting_next_word_in_the_middle(self):
        self.editor.set_insert(self.editor.get_index(2))
        self.editor.delete_next_word()
        self.assertEquals('sa text', self.editor.get_text())

    def test_deleting_prev_word(self):
        self.editor.set_insert(self.editor.get_end())
        self.editor.delete_prev_word()
        self.assertEquals('sample ', self.editor.get_text(), self.editor.get_text())

    def test_deleting_prev_word_in_the_middle(self):
        self.editor.set_insert(self.editor.get_relative(self.editor.get_end(), -2))
        self.editor.delete_prev_word()
        self.assertEquals('sample xt', self.editor.get_text(), self.editor.get_text())

    def test_deleting_prev_word_at_the_beginning(self):
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

    def test_next_word_stopping_at_end_of_line_preceded_by_a_space(self):
        self.editor.set_text('sampleText ')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(10), self.editor.get_insert())
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(11), self.editor.get_insert())

    def test_next_word_stopping_at_capitals1(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_start())
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_next_word_stopping_at_capitals2(self):
        self.editor.set_text('sampleText')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.next_word()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    def test_next_word_stopping_at_capitals3(self):
        self.editor.set_text('MyHTTPClient')
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(2), self.editor.get_insert())
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_next_word_stopping_at_capitals4(self):
        self.editor.set_text('INSERT')
        self.editor.next_word()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    def test_next_word_stopping_at_capitals5(self):
        self.editor.set_text('INSERT ')
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

    def test_next_word_stopping_at_capitals6(self):
        self.editor.set_text(' Hello')
        self.editor.next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())

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

    def test_prev_word_stopping_at_capitals3(self):
        self.editor.set_text('MyHTTPText')
        self.editor.set_insert(self.editor.get_index(6))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(2), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals4(self):
        self.editor.set_text('INSERT')
        self.editor.set_insert(self.editor.get_end())
        self.editor.prev_word()
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals5(self):
        self.editor.set_text(' INSERT')
        self.editor.set_insert(self.editor.get_index(4))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(1), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals6(self):
        self.editor.set_text('AClass')
        self.editor.set_insert(self.editor.get_index(4))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(1), self.editor.get_insert())

    def test_prev_word_stopping_at_capitals7(self):
        self.editor.set_text('MyClass')
        self.editor.set_insert(self.editor.get_index(2))
        self.editor.prev_word()
        self.assertEquals(self.editor.get_index(0), self.editor.get_insert())

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

    def test_upper_next_word(self):
        self.editor.set_text('sample text')
        self.editor.set_insert(self.editor.get_index(1))
        self.editor.upper_next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())
        self.assertEquals('sAMPLE text', self.editor.get_text())

    def test_lower_next_word(self):
        self.editor.set_text('SAMPLE TEXT')
        self.editor.set_insert(self.editor.get_index(1))
        self.editor.lower_next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())
        self.assertEquals('Sample TEXT', self.editor.get_text())

    def test_upper_next_word(self):
        self.editor.set_text('sample text')
        self.editor.set_insert(self.editor.get_index(1))
        self.editor.capitalize_next_word()
        self.assertEquals(self.editor.get_index(6), self.editor.get_insert())
        self.assertEquals('sAmple text', self.editor.get_text())

    def test_going_to_the_start(self):
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.goto_start()
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())

    def test_going_to_the_end(self):
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.goto_end()
        self.assertEquals(self.editor.get_end(), self.editor.get_insert())

    def test_undo(self):
        self.editor.saving_editor()
        self.editor.insert(self.editor.get_end(), '.')
        self.assertEquals('sample text.', self.editor.get_text())
        self.editor.undo()
        self.assertEquals('sample text', self.editor.get_text(),self.editor.get_text())

    def test_redo(self):
        self.editor.saving_editor()
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

class TextChangeInspectorTest(unittest.TestCase):

    __factory = GraphicalEditorFactory(Tkinter.Frame())

    def setUp(self):
        super(TextChangeInspectorTest, self).setUp()
        editor = TextChangeInspectorTest.__factory.create(rope.ui.editingtools.NormalEditingTools())
        self.text = editor.text
        self.change_inspector = editor.change_inspector

    def tearDown(self):
        super(TextChangeInspectorTest, self).tearDown()

    def test_is_changed(self):
        self.text.insert('insert', 'sample text')
        self.assertTrue(self.change_inspector.is_changed())
        self.change_inspector.clear_changed()
        self.assertFalse(self.change_inspector.is_changed())

    def test_get_changed_region_after_inserts(self):
        self.text.insert('insert', 'sample text')
        self.change_inspector.clear_changed()
        self.text.insert('1.3', 'a')
        self.assertEquals(('1.3', '1.4'), self.change_inspector.get_changed_region())
        self.text.insert('1.6', 'a')
        self.assertEquals(('1.3', '1.7'), self.change_inspector.get_changed_region())

    def test_get_changed_region_after_inserts2(self):
        self.text.insert('insert', 'sample text')
        self.change_inspector.clear_changed()
        self.text.insert('1.3', 'a')
        self.text.insert('1.2', 'aa')
        self.assertEquals(('1.2', '1.6'), self.change_inspector.get_changed_region())

    def test_get_changed_region_after_deletes(self):
        self.text.insert('insert', 'sample text')
        self.change_inspector.clear_changed()
        self.text.delete('1.3', '1.4')
        self.assertEquals(('1.3', '1.3'), self.change_inspector.get_changed_region())
        self.text.delete('1.5', '1.6')
        self.assertEquals(('1.3', '1.5'), self.change_inspector.get_changed_region())

    def test_get_changed_region_after_deletes2(self):
        self.text.insert('insert', 'sample text')
        self.change_inspector.clear_changed()
        self.text.delete('1.5', '1.6')
        self.text.delete('1.1', '1.2')
        self.assertEquals(('1.1', '1.4'), self.change_inspector.get_changed_region())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(GraphicalEditorTest))
    result.addTests(unittest.makeSuite(TextChangeInspectorTest))
    return result


if __name__ == '__main__':
    unittest.main()

