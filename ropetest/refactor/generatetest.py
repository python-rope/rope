import unittest

import rope.base.project
import ropetest.testutils
from rope.refactor import generate


class GenerateTest(unittest.TestCase):

    def setUp(self):
        super(GenerateTest, self).setUp()
        self.project_root = 'sample_project'
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.mod = self.pycore.create_module(self.project.root, 'mod1')
        self.mod2 = self.pycore.create_module(self.project.root, 'mod2')
        self.pkg = self.pycore.create_package(self.project.root, 'pkg')

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(GenerateTest, self).tearDown()

    def _get_generate(self, offset):
        return generate.GenerateVariable(self.project, self.mod, offset)

    def _get_generate_class(self, offset):
        return generate.GenerateClass(self.project, self.mod, offset)

    def _get_generate_module(self, offset):
        return generate.GenerateModule(self.project, self.mod, offset)

    def _get_generate_package(self, offset):
        return generate.GeneratePackage(self.project, self.mod, offset)

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
            'class C(object):\n    def f(self):\n        pass\n\n    attr = None\n' \
            'c = C()\na_var = c.attr', self.mod.read())

    def test_generating_variable_in_classes_removing_pass(self):
        code = 'class C(object):\n    pass\nc = C()\na_var = c.attr'
        self.mod.write(code)
        changes = self._get_generate(code.index('attr')).get_changes()
        self.project.do(changes)
        self.assertEquals('class C(object):\n\n    attr = None\n' \
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

    def test_generating_modules(self):
        code = 'import pkg\npkg.mod\n'
        self.mod.write(code)
        generator = self._get_generate_module(code.rindex('mod'))
        self.project.do(generator.get_changes())
        mod = self.pkg.get_child('mod.py')
        self.assertEquals((mod, 1), generator.get_location())

    def test_generating_packages(self):
        code = 'import pkg\npkg.pkg2\n'
        self.mod.write(code)
        generator = self._get_generate_package(code.rindex('pkg2'))
        self.project.do(generator.get_changes())
        pkg2 = self.pkg.get_child('pkg2')
        init = pkg2.get_child('__init__.py')
        self.assertEquals((init, 1), generator.get_location())


if __name__ == '__main__':
    unittest.main()
