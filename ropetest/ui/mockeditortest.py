import unittest

import rope.ui.editingtools
from rope.ui import editingcontexts, editingtools
from ropetest.ui.mockeditor import *
from rope.ui.editor import *

class TextEditorTest(unittest.TestCase):

    _editorFactory = None
    def __init__(self, *args, **kws):
        self.__factory = self.__class__._editorFactory
        unittest.TestCase.__init__(self, *args, **kws)

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.editor = self.__factory.create(get_sample_editingcontext())
        self.editor.set_text('sample text')

    def tearDown(self):
        unittest.TestCase.tearDown(self)

    def testSetGetText(self):
        self.assertEquals('sample text', self.editor.get_text())
        self.editor.set_text('')
        self.assertEquals('', self.editor.get_text())

    def testTextIndices(self):
        self.assertTrue(self.editor.get_start() < self.editor.get_end())
        self.editor.set_text('')
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())
        self.assertEquals(self.editor.get_insert(), self.editor.get_end())

    def testTextIndicesMoving(self):
        index = self.editor.get_insert()
        newIndex = self.editor.get_relative(index, 2)
        self.assertTrue(index < newIndex)
        self.assertEquals(index, self.editor.get_relative(newIndex, -2))

    def testTextIndicesMovingOutOfBounds(self):
        index = self.editor.get_start()
        self.assertEquals(self.editor.get_relative(index, 100), self.editor.get_end())
        self.assertEquals(self.editor.get_relative(index, -100), self.editor.get_start())

    def testAbsoluteTextIndicesMovingOutOfBounds(self):
        index = self.editor.get_start()
        self.assertEquals(self.editor.get_index(100), self.editor.get_end())
        self.assertEquals(self.editor.get_index(-100), self.editor.get_start())

    def testMovingInsertIndex(self):
        self.assertEquals(self.editor.get_start(), self.editor.get_insert())
        self.editor.set_insert(self.editor.get_index(3))
        self.assertEquals(self.editor.get_index(3), self.editor.get_insert())

    def testReading(self):
        self.assertEquals('s', self.editor.get())

    def testReadingAnyIndex(self):
        self.assertEquals('a', self.editor.get(self.editor.get_index(1)))

    def testReadingRanges(self):
        self.assertEquals('sample', self.editor.get(self.editor.get_start(),
                                                    self.editor.get_index(6)))

    def testInsertingText(self):
        self.editor.insert(self.editor.get_index(6), ' tricky')
        self.assertEquals('sample tricky text', self.editor.get_text())

    def testInsertingTextAtTheEnd(self):
        self.editor.insert(self.editor.get_end(), ' note')
        self.assertEquals('sample text note', self.editor.get_text())

    def testInsertingTextAtTheBeginning(self):
        self.editor.insert(self.editor.get_start(), 'new ')
        self.assertEquals('new sample text', self.editor.get_text())

    def testReadingAtTheEnd(self):
        self.assertEquals('', self.editor.get(self.editor.get_end()))

    def testMultiLineContent(self):
        self.editor.insert(self.editor.get_end(), '\nanother piece of text')
        self.assertEquals('sample text\nanother piece of text', self.editor.get_text())
        self.assertEquals('text',
                          self.editor.get(self.editor.get_relative(self.editor.get_end(), -4),
                                          self.editor.get_end()))
        self.assertEquals('a', self.editor.get(self.editor.get_index(12)))

    def testDeleting(self):
        self.editor.delete()
        self.assertEquals('ample text', self.editor.get_text())
        self.editor.set_insert(self.editor.get_index(3))
        self.editor.delete()
        self.editor.delete()
        self.assertEquals('amp text', self.editor.get_text())

    def testDeletingFromTheMiddle(self):
        self.editor.delete(self.editor.get_index(1),
                                self.editor.get_index(7))
        self.assertEquals('stext', self.editor.get_text())
        self.editor.delete(self.editor.get_index(2),
                                self.editor.get_end())
        self.assertEquals('st', self.editor.get_text())

    def testDeletingFromTheEnd(self):
        self.editor.delete(self.editor.get_end())
        self.assertEquals('sample text', self.editor.get_text())

    def testMultiLineDeleting(self):
        self.editor.insert(self.editor.get_end(), '\nanother piece of text')
        self.editor.delete(self.editor.get_index(11))
        self.assertEquals('sample textanother piece of text', self.editor.get_text())

    def test_searching(self):
        found = self.editor.search('s', self.editor.get_insert())
        self.assertEquals(self.editor.get_start(), found)

    def test_searching_not_found(self):
        found = self.editor.search('aa', self.editor.get_insert())
        self.assertTrue(found is None)

    def test_reverse_searching(self):
        self.editor.set_insert(self.editor.get_index(len('sample text') - 1))
        found = self.editor.search('te', self.editor.get_insert(), forwards=False)
        self.assertEquals(self.editor.get_index(7), found)

    def test_case_sensetivity(self):
        self.editor.set_text('aAb')
        self.assertTrue(self.editor.search('aB', self.editor.get_insert()) is None)
        self.assertTrue(self.editor.search('aB', self.editor.get_insert(), case = False) is not None)

    def test_simple_line_editor(self):
        self.editor.set_text('line1')
        line_editor = self.editor.line_editor()
        self.assertEquals('line1', line_editor.get_line(1))

    def test_line_editor_multiline(self):
        self.editor.set_text('line1\nline2\nline3\n')
        line_editor = self.editor.line_editor()
        self.assertEquals('line1', line_editor.get_line(1))
        self.assertEquals('line3', line_editor.get_line(3))
        self.assertEquals('', line_editor.get_line(4))

    def test_line_editor_indenting(self):
        self.editor.set_text('line1\nline2\nline3\n')
        line_editor = self.editor.line_editor()
        line_editor.indent_line(2, 2)
        self.assertEquals('  line2', line_editor.get_line(2))
        self.assertEquals('line1\n  line2\nline3\n', self.editor.get_text())

    def test_line_editor_indenting_with_negative_indent(self):
        self.editor.set_text('line1\nline2\nline3\n')
        line_editor = self.editor.line_editor()
        line_editor.indent_line(2, -2)
        self.assertEquals('ne2', line_editor.get_line(2))
        self.assertEquals('line1\nne2\nline3\n', self.editor.get_text())

    def test_line_editor_length(self):
        self.editor.set_text('line1')
        line_editor = self.editor.line_editor()
        self.assertEquals(1, line_editor.length())

def get_sample_editingcontext():
    return editingcontexts.others

def suite():
    result = unittest.TestSuite()
    import Tkinter
    TextEditorTest._editorFactory = GraphicalEditorFactory(Tkinter.Frame())
    result.addTests(unittest.makeSuite(TextEditorTest))
    TextEditorTest._editorFactory = MockEditorFactory()
    result.addTests(unittest.makeSuite(TextEditorTest))
    return result


if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(suite())

