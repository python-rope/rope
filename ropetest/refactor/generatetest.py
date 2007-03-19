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

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(GenerateTest, self).tearDown()

    def _get_generate(self, offset):
        return generate.GenerateVariable(self.project, self.mod, offset)

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
        self.assertEquals('name = None\na_var = name\n', self.mod.read())

    def test_generating_variable_inserting_before_statement(self):
        code = 'c = 1\nc = b\n'
        self.mod.write(code)
        changes = self._get_generate(code.index('b')).get_changes()
        self.project.do(changes)
        self.assertEquals('c = 1\nb = None\nc = b\n', self.mod.read())

    def test_generating_variable_in_local_scopes(self):
        code = 'def f():\n    c = 1\n    c = b\n'
        self.mod.write(code)
        changes = self._get_generate(code.index('b')).get_changes()
        self.project.do(changes)
        self.assertEquals('def f():\n    c = 1\n    b = None\n    c = b\n',
                          self.mod.read())

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
            'class C(object):\n    def f(self):\n        pass\n    attr = None\n' \
            'c = C()\na_var = c.attr', self.mod.read())

    def test_generating_variable_in_classes_removing_pass(self):
        code = 'class C(object):\n    pass\nc = C()\na_var = c.attr'
        self.mod.write(code)
        changes = self._get_generate(code.index('attr')).get_changes()
        self.project.do(changes)
        self.assertEquals('class C(object):\n    attr = None\n' \
                          'c = C()\na_var = c.attr', self.mod.read())


if __name__ == '__main__':
    unittest.main()
