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

    def test_get_block_end(self):
        finder = self.get_range_finder('a = 10\nb = 12\nc = 14', 1)
        self.assertEquals(3,  finder.get_block_end())

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

    def test_source_lines_get_line_start(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEquals(0, to_lines.get_line_start(1))
        self.assertEquals(6, to_lines.get_line_start(2))
        self.assertEquals(12, to_lines.get_line_start(3))

    def test_source_lines_get_line_end(self):
        to_lines = SourceLinesAdapter('line1\nline2\n')
        self.assertEquals(5, to_lines.get_line_end(1))
        self.assertEquals(11, to_lines.get_line_end(2))
        self.assertEquals(12, to_lines.get_line_end(3))

        
class WordRangeFinderTest(unittest.TestCase):

    def setUp(self):
        super(WordRangeFinderTest, self).setUp()

    def tearDown(self):
        super(WordRangeFinderTest, self).tearDown()

    def test_inside_parans(self):
        word_finder = WordRangeFinder('a_func(a_var)')
        self.assertEquals('a_var', word_finder.get_statement_at(10))

    def test_simple_names(self):
        word_finder = WordRangeFinder('a_var = 10')
        self.assertEquals('a_var', word_finder.get_statement_at(3))

    def test_function_calls(self):
        word_finder = WordRangeFinder('sample_function()')
        self.assertEquals('sample_function', word_finder.get_statement_at(10))
    
    def test_attribute_accesses(self):
        word_finder = WordRangeFinder('a_var.an_attr')
        self.assertEquals('a_var.an_attr', word_finder.get_statement_at(10))
    
    def test_strings(self):
        word_finder = WordRangeFinder('"a string".split()')
        self.assertEquals('"a string".split', word_finder.get_statement_at(14))

    def test_function_calls(self):
        word_finder = WordRangeFinder('file("afile.txt").read()')
        self.assertEquals('file("afile.txt").read',
                          word_finder.get_statement_at(18))

    def test_parens(self):
        word_finder = WordRangeFinder('("afile.txt").split()')
        self.assertEquals('("afile.txt").split',
                          word_finder.get_statement_at(18))

    def test_function_with_no_param(self):
        word_finder = WordRangeFinder('AClass().a_func()')
        self.assertEquals('AClass().a_func', word_finder.get_statement_at(12))

    def test_function_with_multiple_param(self):
        word_finder = WordRangeFinder('AClass(a_param, another_param, "a string").a_func()')
        self.assertEquals('AClass(a_param, another_param, "a string").a_func',
                          word_finder.get_statement_at(44))
    
    def test_param_expressions(self):
        word_finder = WordRangeFinder('AClass(an_object.an_attr).a_func()')
        self.assertEquals('an_object.an_attr',
                          word_finder.get_statement_at(20))

    def test_string_parens(self):
        word_finder = WordRangeFinder('a_func("(").an_attr')
        self.assertEquals('a_func("(").an_attr',
                          word_finder.get_statement_at(16))

    def test_extra_spaces(self):
        word_finder = WordRangeFinder('a_func  (  "(" ) .   an_attr')
        self.assertEquals('a_func  (  "(" ) .   an_attr',
                          word_finder.get_statement_at(26))

    def test_splitted_statement(self):
        word_finder = WordRangeFinder('an_object.an_attr')
        self.assertEquals(('an_object', 'an_at', 10),
                          word_finder.get_splitted_statement_before(15))

    def test_empty_splitted_statement(self):
        word_finder = WordRangeFinder('an_attr')
        self.assertEquals(('', 'an_at', 0),
                          word_finder.get_splitted_statement_before(5))

    def test_empty_splitted_statement2(self):
        word_finder = WordRangeFinder('an_object.')
        self.assertEquals(('an_object', '', 10),
                          word_finder.get_splitted_statement_before(10))

    def test_empty_splitted_statement3(self):
        word_finder = WordRangeFinder('')
        self.assertEquals(('', '', 0),
                          word_finder.get_splitted_statement_before(0))

    def test_empty_splitted_statement4(self):
        word_finder = WordRangeFinder('a_var = ')
        self.assertEquals(('', '', 8),
                          word_finder.get_splitted_statement_before(8))

    def test_operators_inside_parens(self):
        word_finder = WordRangeFinder('(a_var + another_var).reverse()')
        self.assertEquals('(a_var + another_var).reverse',
                          word_finder.get_statement_at(25))

    def test_dictionaries(self):
        word_finder = WordRangeFinder('print {1: "one", 2: "two"}.keys()')
        self.assertEquals('print {1: "one", 2: "two"}.keys',
                          word_finder.get_statement_at(29))

    # TODO: eliminating comments
    def xxx_test_comments_for_finding_statements(self):
        word_finder = WordRangeFinder('# var2 . \n  var3')
        self.assertEquals('var3',
                          word_finder.get_statement_at(14))

    def test_comments_for_finding_statements2(self):
        word_finder = WordRangeFinder('var1 + "# var2".\n  var3')
        self.assertEquals('"# var2".\n  var3',
                          word_finder.get_statement_at(21))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(StatementRangeFinderTest))
    result.addTests(unittest.makeSuite(WordRangeFinderTest))
    return result

if __name__ == '__main__':
    unittest.main()


