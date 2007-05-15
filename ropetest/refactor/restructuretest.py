from rope.refactor import restructure
from ropetest import testutils

import unittest


class RestructureTest(unittest.TestCase):

    def setUp(self):
        super(RestructureTest, self).setUp()
        self.project = testutils.sample_project()
        self.pycore = self.project.get_pycore()
        self.mod = self.pycore.create_module(self.project.root, 'mod')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(RestructureTest, self).tearDown()

    def test_trivial_case(self):
        refactoring = restructure.Restructure(self.project,
                                              'a = 1', 'a = 0')
        self.mod.write('b = 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('b = 1\n', self.mod.read())

    def test_replacing_simple_patterns(self):
        refactoring = restructure.Restructure(self.project,
                                              'a = 1', 'a = int(1)')
        self.mod.write('a = 1\nb = 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = int(1)\nb = 1\n', self.mod.read())

    def test_replacing_patterns_with_normal_names(self):
        refactoring = restructure.Restructure(self.project,
                                              '${a} = 1', '${a} = int(1)')
        self.mod.write('a = 1\nb = 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = int(1)\nb = 1\n', self.mod.read())

    def test_replacing_patterns_with_any_names(self):
        refactoring = restructure.Restructure(self.project,
                                              '${?a} = 1', '${?a} = int(1)')
        self.mod.write('a = 1\nb = 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = int(1)\nb = int(1)\n', self.mod.read())

    def test_replacing_patterns_with_any_names2(self):
        refactoring = restructure.Restructure(
            self.project, '${?a} + ${?a}', '${?a} * 2')
        self.mod.write('a = 1 + 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = 1 * 2\n', self.mod.read())

    def test_replacing_patterns_with_checks(self):
        self.mod.write('def f(p=1):\n    return p\ng = f\ng()\n')
        pymod = self.pycore.resource_to_pyobject(self.mod)
        f_pyobject = pymod.get_attribute('f').get_object()
        refactoring = restructure.Restructure(
            self.project, '${?f}()', '${?f}(2)', {'?f.object':f_pyobject})
        self.project.do(refactoring.get_changes())
        self.assertEquals('def f(p=1):\n    return p\ng = f\ng(2)\n',
                          self.mod.read())

    def test_replacing_assignments_with_sets(self):
        refactoring = restructure.Restructure(
            self.project, '${?a} = ${?b}', '${?a}.set(${?b})')
        self.mod.write('a = 1\nb = 1\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a.set(1)\nb.set(1)\n', self.mod.read())

    def test_replacing_sets_with_assignments(self):
        refactoring = restructure.Restructure(
            self.project, '${?a}.set(${?b})', '${?a} = ${?b}')
        self.mod.write('a.set(1)\nb.set(1)\n')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = 1\nb = 1\n', self.mod.read())


if __name__ == '__main__':
    unittest.main()
