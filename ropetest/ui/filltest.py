import unittest

from rope.ui import fill


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

    # Handling lists
    def xxx_test_indented_broken_lines(self):
        self.assertEquals('* simple\n  paragraph',
                          self.fill.fill('* simple paragraph'))


if __name__ == '__main__':
    unittest.main()
