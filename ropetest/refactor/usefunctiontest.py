import unittest

import ropetest.testutils as testutils
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
        self.assertEquals(code, self.mod1.read())

    def test_simple_function(self):
        code = 'def f(p):\n    print(p)\nprint(1)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEquals('def f(p):\n    print(p)\nf(1)\n',
                          self.mod1.read())

    def test_simple_function2(self):
        code = 'def f(p):\n    print(p + 1)\nprint(1 + 1)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEquals('def f(p):\n    print(p + 1)\nf(1)\n',
                          self.mod1.read())

    def test_functions_with_multiple_statements(self):
        code = 'def f(p):\n    r = p + 1\n    print(r)\nr = 2 + 1\nprint(r)\n'
        self.mod1.write(code)
        user = UseFunction(self.project, self.mod1, code.rindex('f'))
        self.project.do(user.get_changes())
        self.assertEquals('def f(p):\n    r = p + 1\n    print(r)\nf(2)\n',
                          self.mod1.read())


if __name__ == '__main__':
    unittest.main()
