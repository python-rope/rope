import unittest

from rope.codeanalyze import (StatementRangeFinder, ArrayLinesAdapter,
                              SourceLinesAdapter, WordRangeFinder)

class StatementRangeFinderTest(unittest.TestCase):

    def setUp(self):
        super(StatementRangeFinderTest, self).setUp()

    def tearDown(self):
        super(StatementRangeFinderTest, self).tearDown()

    def get_range_finder(self, code, line):
        result = StatementRangeFinder(ArrayLinesAdapter(code.split('\n')), line)
        result.analyze()
        return result

    def test_simple_statement_finding(self):
        finder = self.get_range_finder('a = 10', 1)
        self.assertEquals(1,  finder.get_statement_start())

    def test_get_start(self):
        finder = self.get_range_finder('a = 10\nb = 12\nc = 14', 1)
        self.assertEquals(1,  finder.get_statement_start())

    def test_get_scope_end(self):
        finder = self.get_range_finder('a = 10\nb = 12\nc = 14', 1)
        self.assertEquals(3,  finder.get_scope_end())

    def test_get_last_open_parens(self):
        finder = self.get_range_finder('a = 10', 1)
        self.assertTrue(finder.last_open_parens() is None)
        
    def test_get_last_open_parens2(self):
        finder = self.get_range_finder('a = (10 +', 1)
        self.assertEquals((1, 4), finder.last_open_parens())
        
    def test_is_line_continued(self):
        finder = self.get_range_finder('a = 10', 1)
        self.assertFalse(finder.is_line_continued())
        
    def test_is_line_continued2(self):
        finder = self.get_range_finder('a = (10 +', 1)
        self.assertTrue(finder.is_line_continued())
        
    def test_source_lines_simple(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEquals('line1', to_lines.get_line(1))
        self.assertEquals('line2', to_lines.get_line(2))
        self.assertEquals('', to_lines.get_line(3))
        self.assertEquals(3, to_lines.length())

    def test_source_lines_get_line_number(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEquals(1, to_lines.get_line_number(0))
        self.assertEquals(2, to_lines.get_line_number(7))

        
class WordRangeFinderTest(unittest.TestCase):

    def setUp(self):
        super(WordRangeFinderTest, self).setUp()

    def tearDown(self):
        super(WordRangeFinderTest, self).tearDown()

    def test_inside_parans(self):
        word_finder = WordRangeFinder('a_func(a_var)')
        self.assertEquals(['a_v'], word_finder.get_name_list_before(10))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(StatementRangeFinderTest))
    result.addTests(unittest.makeSuite(WordRangeFinderTest))
    return result

if __name__ == '__main__':
    unittest.main()


