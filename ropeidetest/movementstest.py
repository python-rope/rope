import unittest
import ropeide.movements


class StatementsTest(unittest.TestCase):

    def setUp(self):
        super(StatementsTest, self).setUp()

    def tearDown(self):
        super(StatementsTest, self).tearDown()

    def test_trivial_case(self):
        statements = ropeide.movements.Statements('')
        self.assertEquals(0, statements.next(0))

    def test_real_statements(self):
        code = 'a = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(code.index('\n'), statements.next(0))

    def test_next_statement(self):
        code = 'a = 1\nb = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(code.rindex('\n'),
                          statements.next(code.index('\n')))

    def test_trivial_prev(self):
        statements = ropeide.movements.Statements('')
        self.assertEquals(0, statements.prev(0))

    def test_prev_statement_at_the_start(self):
        code = 'a = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(0, statements.prev(0))

    def test_prev_statement_at_the_start(self):
        code = 'a = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('1')))

    def test_prev_statement(self):
        code = 'a = 1\nb = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('b')))
        self.assertEquals(code.index('b'), statements.prev(code.rindex('1')))

    def test_prev_statement_with_blank_lines(self):
        code = 'a = 1\n\nb = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('b')))
        self.assertEquals(code.index('b'), statements.prev(code.rindex('1')))

    def test_prev_statement_with_indented_lines(self):
        code = 'def f():\n    a = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(code.index('a'), statements.prev(len(code)))

    def test_prev_statement_and_comments(self):
        code = 'a = 1\n# ccc\nb = 1\n'
        statements = ropeide.movements.Statements(code)
        self.assertEquals(0, statements.prev(code.index('b')))


class ScopesTest(unittest.TestCase):

    def test_trivial_case(self):
        code = ''
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(0, scopes.next(0))

    def test_next_on_functions(self):
        code = 'def f():\n    pass\n'
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(len(code) - 1, scopes.next(0))

    def test_next_on_functions(self):
        code = 'def f():\n    pass\n\ndef g():\n    pass\n'
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(code.index('\n\n'), scopes.next(0))
        self.assertEquals(code.index('\n\n'), scopes.next(1))
        self.assertEquals(len(code) - 1, scopes.next(code.index('g')))
        self.assertEquals(len(code) - 1, scopes.next(code.index('\n\n')))

    def test_trivial_prev(self):
        code = ''
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(0, scopes.prev(0))

    def test_prev_on_functions(self):
        code = 'def f():\n    pass\n'
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(0, scopes.prev(10))
        self.assertEquals(0, scopes.prev(len(code)))

    def test_prev_on_functions(self):
        code = 'def f():\n    pass\n\ndef g():\n    pass\n'
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(0, scopes.prev(code.index('()')))
        self.assertEquals(code.index('def g'), scopes.prev(len(code)))

    def test_prev_on_indented_functions(self):
        code = 'class A(object):\n    def f():\n        pass\n\n\n' \
               '    def g():\n        pass\n'
        scopes = ropeide.movements.Scopes(code)
        self.assertEquals(code.index('def f'),
                          scopes.prev(code.index('def g')))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(StatementsTest))
    result.addTests(unittest.makeSuite(ScopesTest))
    return result


if __name__ == '__main__':
    unittest.main()
