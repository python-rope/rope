import unittest
from rope.ide import movements


class StatementsTest(unittest.TestCase):

    def setUp(self):
        super(StatementsTest, self).setUp()

    def tearDown(self):
        super(StatementsTest, self).tearDown()

    def test_trivial_case(self):
        statements = movements.Statements('')
        self.assertEquals(0, statements.next(0))

    def test_real_statements(self):
        code = 'a = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(code.index('\n'), statements.next(0))

    def test_next_statement(self):
        code = 'a = 1\nb = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(code.rindex('\n'),
                          statements.next(code.index('\n')))

    def test_trivial_prev(self):
        statements = movements.Statements('')
        self.assertEquals(0, statements.prev(0))

    def test_prev_statement_at_the_start(self):
        code = 'a = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(0, statements.prev(0))

    def test_prev_statement_at_the_start(self):
        code = 'a = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('1')))

    def test_prev_statement(self):
        code = 'a = 1\nb = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('b')))
        self.assertEquals(code.index('b'), statements.prev(code.rindex('1')))

    def test_prev_statement_with_blank_lines(self):
        code = 'a = 1\n\nb = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('b')))
        self.assertEquals(code.index('b'), statements.prev(code.rindex('1')))

    def test_prev_statement_with_indented_lines(self):
        code = 'def f():\n    a = 1\n'
        statements = movements.Statements(code)
        self.assertEquals(code.index('a'), statements.prev(len(code)))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(StatementsTest))
    return result


if __name__ == '__main__':
    unittest.main()
