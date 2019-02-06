try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from rope.contrib import generate
from ropetest import testutils


class GenerateTest(unittest.TestCase):

    def setUp(self):
        super(GenerateTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.pycore
        self.mod = testutils.create_module(self.project, 'mod1')
        self.mod2 = testutils.create_module(self.project, 'mod2')
        self.pkg = testutils.create_package(self.project, 'pkg')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(GenerateTest, self).tearDown()

    def _get_generate(self, offset):
        return generate.GenerateVariable(self.project, self.mod, offset)

    def _get_generate_class(self, offset, goal_mod=None):
        return generate.GenerateClass(self.project, self.mod, offset, goal_resource=goal_mod)

    def _get_generate_module(self, offset):
        return generate.GenerateModule(self.project, self.mod, offset)

    def _get_generate_package(self, offset):
        return generate.GeneratePackage(self.project, self.mod, offset)

    def _get_generate_function(self, offset):
        return generate.GenerateFunction(self.project, self.mod, offset)

    def test_getting_location(self):
        code = 'a_var = name\n'
        self.mod.write(code)
        generator = self._get_generate(code.index('name'))
        self.assertEquals((self.mod, 1), generator.get_location())

    def test_generating_variable(self):
        code = 'a_var = name\n'
        self.mod.write(code)
        changes = self._get_generate(code.index('name')).get_changes()
        self.project.do(changes)
        self.assertEquals('name = None\n\n\na_var = name\n', self.mod.read())

    def test_generating_variable_inserting_before_statement(self):
        code = 'c = 1\nc = b\n'
        self.mod.write(code)
        changes = self._get_generate(code.index('b')).get_changes()
        self.project.do(changes)
        self.assertEquals('c = 1\nb = None\n\n\nc = b\n', self.mod.read())

    def test_generating_variable_in_local_scopes(self):
        code = 'def f():\n    c = 1\n    c = b\n'
        self.mod.write(code)
        changes = self._get_generate(code.index('b')).get_changes()
        self.project.do(changes)
        self.assertEquals('def f():\n    c = 1\n    b = None\n    c = b\n',
                          self.mod.read())

    def test_generating_variable_in_other_modules(self):
        code = 'import mod2\nc = mod2.b\n'
        self.mod.write(code)
        generator = self._get_generate(code.index('b'))
        self.project.do(generator.get_changes())
        self.assertEquals((self.mod2, 1), generator.get_location())
        self.assertEquals('b = None\n', self.mod2.read())

    def test_generating_variable_in_classes(self):
        code = 'class C(object):\n    def f(self):\n        pass\n' \
               'c = C()\na_var = c.attr'
        self.mod.write(code)
        changes = self._get_generate(code.index('attr')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n    def f(self):\n        '
            'pass\n\n    attr = None\n'
            'c = C()\na_var = c.attr', self.mod.read())

    def test_generating_variable_in_classes_removing_pass(self):
        code = 'class C(object):\n    pass\nc = C()\na_var = c.attr'
        self.mod.write(code)
        changes = self._get_generate(code.index('attr')).get_changes()
        self.project.do(changes)
        self.assertEquals('class C(object):\n\n    attr = None\n'
                          'c = C()\na_var = c.attr', self.mod.read())

    def test_generating_variable_in_packages(self):
        code = 'import pkg\na = pkg.a\n'
        self.mod.write(code)
        generator = self._get_generate(code.rindex('a'))
        self.project.do(generator.get_changes())
        init = self.pkg.get_child('__init__.py')
        self.assertEquals((init, 1), generator.get_location())
        self.assertEquals('a = None\n', init.read())

    def test_generating_classes(self):
        code = 'c = C()\n'
        self.mod.write(code)
        changes = self._get_generate_class(code.index('C')).get_changes()
        self.project.do(changes)
        self.assertEquals('class C(object):\n    pass\n\n\nc = C()\n',
                          self.mod.read())

    def test_generating_classes_in_other_module(self):
        code = 'c = C()\n'
        self.mod.write(code)
        changes = self._get_generate_class(code.index('C'), self.mod2).get_changes()
        self.project.do(changes)
        self.assertEquals('class C(object):\n    pass\n',
                          self.mod2.read())
        self.assertEquals('from mod2 import C\nc = C()\n',
                          self.mod.read())

    def test_generating_modules(self):
        code = 'import pkg\npkg.mod\n'
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex('mod'))
        self.project.do(generator.get_changes())
        mod = self.pkg.get_child('mod.py')
        self.assertEquals((mod, 1), generator.get_location())
        self.assertEquals('import pkg.mod\npkg.mod\n', self.mod.read())

    def test_generating_packages(self):
        code = 'import pkg\npkg.pkg2\n'
        self.mod.write(code)
        generator = self._get_generate_package(code.rindex('pkg2'))
        self.project.do(generator.get_changes())
        pkg2 = self.pkg.get_child('pkg2')
        init = pkg2.get_child('__init__.py')
        self.assertEquals((init, 1), generator.get_location())
        self.assertEquals('import pkg.pkg2\npkg.pkg2\n', self.mod.read())

    def test_generating_function(self):
        code = 'a_func()\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals('def a_func():\n    pass\n\n\na_func()\n',
                          self.mod.read())

    def test_generating_modules_with_empty_primary(self):
        code = 'mod\n'
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex('mod'))
        self.project.do(generator.get_changes())
        mod = self.project.root.get_child('mod.py')
        self.assertEquals((mod, 1), generator.get_location())
        self.assertEquals('import mod\nmod\n', self.mod.read())

    def test_generating_variable_already_exists(self):
        code = 'b = 1\nc = b\n'
        self.mod.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            self._get_generate(code.index('b')).get_changes()

    def test_generating_variable_primary_cannot_be_determined(self):
        code = 'c = can_not_be_found.b\n'
        self.mod.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            self._get_generate(code.rindex('b')).get_changes()

    def test_generating_modules_when_already_exists(self):
        code = 'mod2\n'
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex('mod'))
        with self.assertRaises(exceptions.RefactoringError):
            self.project.do(generator.get_changes())

    def test_generating_static_methods(self):
        code = 'class C(object):\n    pass\nC.a_func()\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n\n    @staticmethod'
            '\n    def a_func():\n        pass\nC.a_func()\n',
            self.mod.read())

    def test_generating_methods(self):
        code = 'class C(object):\n    pass\nc = C()\nc.a_func()\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n\n    def a_func(self):\n        pass\n'
            'c = C()\nc.a_func()\n',
            self.mod.read())

    def test_generating_constructors(self):
        code = 'class C(object):\n    pass\nc = C()\n'
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex('C')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n\n    def __init__(self):\n        pass\n'
            'c = C()\n',
            self.mod.read())

    def test_generating_calls(self):
        code = 'class C(object):\n    pass\nc = C()\nc()\n'
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex('c')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n\n    def __call__(self):\n        pass\n'
            'c = C()\nc()\n',
            self.mod.read())

    def test_generating_calls_in_other_modules(self):
        self.mod2.write('class C(object):\n    pass\n')
        code = 'import mod2\nc = mod2.C()\nc()\n'
        self.mod.write(code)
        changes = self._get_generate_function(code.rindex('c')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'class C(object):\n\n    def __call__(self):\n        pass\n',
            self.mod2.read())

    def test_generating_function_handling_arguments(self):
        code = 'a_func(1)\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals('def a_func(arg0):\n    pass\n\n\na_func(1)\n',
                          self.mod.read())

    def test_generating_function_handling_keyword_xarguments(self):
        code = 'a_func(p=1)\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals('def a_func(p):\n    pass\n\n\na_func(p=1)\n',
                          self.mod.read())

    def test_generating_function_handling_arguments_better_naming(self):
        code = 'a_var = 1\na_func(a_var)\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals('a_var = 1\ndef a_func(a_var):'
                          '\n    pass\n\n\na_func(a_var)\n',
                          self.mod.read())

    def test_generating_variable_in_other_modules2(self):
        self.mod2.write('\n\n\nprint(1)\n')
        code = 'import mod2\nc = mod2.b\n'
        self.mod.write(code)
        generator = self._get_generate(code.index('b'))
        self.project.do(generator.get_changes())
        self.assertEquals((self.mod2, 5), generator.get_location())
        self.assertEquals('\n\n\nprint(1)\n\n\nb = None\n', self.mod2.read())

    def test_generating_function_in_a_suite(self):
        code = 'if True:\n    a_func()\n'
        self.mod.write(code)
        changes = self._get_generate_function(
            code.index('a_func')).get_changes()
        self.project.do(changes)
        self.assertEquals('def a_func():\n    pass'
                          '\n\n\nif True:\n    a_func()\n',
                          self.mod.read())

    def test_generating_function_in_a_suite_in_a_function(self):
        code = 'def f():\n    a = 1\n    if 1:\n        g()\n'
        self.mod.write(code)
        changes = self._get_generate_function(code.index('g()')).get_changes()
        self.project.do(changes)
        self.assertEquals(
            'def f():\n    a = 1\n    def g():\n        pass\n'
            '    if 1:\n        g()\n',
            self.mod.read())


if __name__ == '__main__':
    unittest.main()
