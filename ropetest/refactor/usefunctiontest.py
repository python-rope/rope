try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from ropetest import testutils
from rope.refactor.usefunction import UseFunction


class UseFunctionTest(unittest.TestCase):

    def setUp(self):
        super(UseFunctionTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.mod2 = testutils.create_module(self.project, 'mod2')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(UseFunctionTest, self).tearDown()

    def test_simple_case(self):
        code = 'def f():\n    pass\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual(code, self.mod1.read())

    def test_simple_function(self):
        code = 'def f(p):\n    print(p)\nprint(1)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual('def f(p):\n    print(p)\nf(1)\n',
                          self.mod1.read())

    def test_simple_function2(self):
        code = 'def f(p):\n    print(p + 1)\nprint(1 + 1)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual('def f(p):\n    print(p + 1)\nf(1)\n',
                          self.mod1.read())

    def test_functions_with_multiple_statements(self):
        code = 'def f(p):\n    r = p + 1\n    print(r)\nr = 2 + 1\nprint(r)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual('def f(p):\n    r = p + 1\n    print(r)\nf(2)\n',
                          self.mod1.read())

    def test_returning(self):
        code = 'def f(p):\n    return p + 1\nr = 2 + 1\nprint(r)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual(
            'def f(p):\n    return p + 1\nr = f(2)\nprint(r)\n',
            self.mod1.read())

    def test_returning_a_single_expression(self):
        code = 'def f(p):\n    return p + 1\nprint(2 + 1)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual(
            'def f(p):\n    return p + 1\nprint(f(2))\n',
            self.mod1.read())

    def test_occurrences_in_other_modules(self):
        code = 'def f(p):\n    return p + 1\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.mod2.write('print(2 + 1)\n')
        self.project.do(user.get_changes())
        self.assertEqual('import mod1\nprint(mod1.f(2))\n',
                          self.mod2.read())

    def test_when_performing_on_non_functions(self):
        code = 'var = 1\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.rindex('var'))

    def test_differing_in_the_inner_temp_names(self):
        code = 'def f(p):\n    a = p + 1\n    print(a)\nb = 2 + 1\nprint(b)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual('def f(p):\n    a = p + 1\n    print(a)\nf(2)\n',
                          self.mod1.read())

    # TODO: probably new options should be added to restructure
    def xxx_test_being_a_bit_more_intelligent_when_returning_assigneds(self):
        code = 'def f(p):\n    a = p + 1\n    return a\n'\
               'var = 2 + 1\nprint(var)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEqual('def f(p):\n    a = p + 1\n    return a\n'
                          'var = f(p)\nprint(var)\n', self.mod1.read())

    def test_exception_when_performing_a_function_with_yield(self):
        code = 'def func():\n    yield 1\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index('func'))

    def test_exception_when_performing_a_function_two_returns(self):
        code = 'def func():\n    return 1\n    return 2\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index('func'))

    def test_exception_when_returns_is_not_the_last_statement(self):
        code = 'def func():\n    return 2\n    a = 1\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            UseFunction(self.project, self.mod1, code.index('func'))


if __name__ == '__main__':
    unittest.main()
