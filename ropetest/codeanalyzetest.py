import unittest

from rope.codeanalyze import StatementRangeFinder, ArrayLinesAdapter

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
        


if __name__ == '__main__':
    unittest.main()
    
