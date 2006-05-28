import unittest

from rope.codeanalyze import StatementRangeFinder

class StatementRangeFinderTest(unittest.TestCase):

    def setUp(self):
        super(StatementRangeFinderTest, self).setUp()

    def tearDown(self):
        super(StatementRangeFinderTest, self).tearDown()

    def test_simple_statement_finding(self):
        finder = StatementRangeFinder('a = 10', 1)
        self.assertEquals((1, 1),  finder.get_range())


if __name__ == '__main__':
    unittest.main()
    
