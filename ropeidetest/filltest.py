import unittest

from ropeide import fill


class FillTest(unittest.TestCase):

    def setUp(self):
        super(FillTest, self).setUp()
        self.fill = fill.Fill(width=10)

    def tearDown(self):
        super(FillTest, self).tearDown()

    def test_trivial_case(self):
        self.assertEquals('', self.fill.fill(''))

    def test_trivial_case2(self):
        self.assertEquals('simple', self.fill.fill('simple'))

    def test_trivial_case_for_multi_lines(self):
        self.assertEquals('one two',
                          self.fill.fill('one two'))

    def test_folding_for_two_words(self):
        self.assertEquals('simple\nparagraph',
                          self.fill.fill('simple paragraph'))

    def test_fixing_extra_spaces(self):
        self.assertEquals('one two',
                          self.fill.fill('one  two'))

    def test_using_tabs(self):
        self.assertEquals('simple\nparagraph',
                          self.fill.fill('simple\tparagraph'))

    def test_converting_tabs_to_spaces(self):
        self.assertEquals('one two',
                          self.fill.fill('one\ttwo'))

    def test_joining_lines(self):
        self.assertEquals('one two',
                          self.fill.fill('one\ntwo'))

    def test_indented_blocks(self):
        self.assertEquals(' one two',
                          self.fill.fill(' one two'))

    def test_indented_broken_lines(self):
        self.assertEquals(' simple\n block',
                          self.fill.fill(' simple block'))

    def test_fill_paragraph(self):
        code = 'simple\nblock'
        self.assertEquals(
            (0, len(code), 'simple\nblock'),
            self.fill.fill_paragraph('simple block', 0))

    def test_fill_paragraph_multiple_paragraphs(self):
        code = 'simple\n\nblock'
        self.assertEquals(
            (0, code.index('\n'), 'simple'),
            self.fill.fill_paragraph(code, 0))

    def test_fill_paragraph_multiple_paragraphs2(self):
        code = 'simple\n\nblock'
        self.assertEquals(
            (code.index('block'), len(code), 'block'),
            self.fill.fill_paragraph(code, len(code)))

    def test_fill_paragraph_multiple_lists(self):
        code = '* simple  block\n* main paragraph\n* another\n'
        self.assertEquals(
            (code.index('main') - 2, code.index('aph') + 3,
             '* main\n  paragraph'),
            self.fill.fill_paragraph(code, code.index('main')))

    def test_fill_paragraph_multiple_lists2(self):
        code = '* simple\n  block\n* main paragraph\n* another\n'
        self.assertEquals(
            (code.index('main') - 2, code.index('aph') + 3,
             '* main\n  paragraph'),
            self.fill.fill_paragraph(code, code.index('main')))

    def test_when_dots_are_involved(self):
        self.assertEquals('a b.  c d.',
                          self.fill.fill('a b.  c d.'))

    def test_when_non_end_line_dots_are_involved(self):
        self.assertEquals('a b.c. d',
                          self.fill.fill('a b.c. d'))

    def test_when_end_line_dots_are_involved2(self):
        self.assertEquals('a b.  c d.',
                          self.fill.fill('a b.\nc d.'))

    def test_handling_simple_unordered_lists(self):
        self.assertEquals('* simple\n  paragraph',
                          self.fill.fill('* simple paragraph'))

    def test_handling_definition_lists(self):
        self.assertEquals('name\n  value',
                          self.fill.fill('name\n  value'))

    def test_handling_simple_unordered_lists(self):
        self.assertEquals('* simple\n  word in\n  list',
                          self.fill.fill('* simple word\n  in list'))


if __name__ == '__main__':
    unittest.main()
