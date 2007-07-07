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
            self.project, '${?f}()', '${?f}(2)')
        self.project.do(refactoring.get_changes({'?f.object':f_pyobject}))
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

    def test_using_make_checks(self):
        self.mod.write('def f(p=1):\n    return p\ng = f\ng()\n')
        refactoring = restructure.Restructure(
            self.project, '${?f}()', '${?f}(2)')
        checks = refactoring.make_checks({'?f.object': 'mod.f'})
        self.project.do(refactoring.get_changes(checks))
        self.assertEquals('def f(p=1):\n    return p\ng = f\ng(2)\n',
                          self.mod.read())

    def test_using_make_checking_builtin_types(self):
        self.mod.write('a = 1 + 1\n')
        refactoring = restructure.Restructure(
            self.project, '${?i} + ${?i}', '${?i} * 2')
        checks = refactoring.make_checks({'?i.type': '__builtin__.int'})
        self.project.do(refactoring.get_changes(checks))
        self.assertEquals('a = 1 * 2\n', self.mod.read())

    def test_auto_indentation_when_no_indentation(self):
        self.mod.write('a = 2\n')
        refactoring = restructure.Restructure(
            self.project, '${?a} = 2', '${?a} = 1\n${?a} += 1')
        self.project.do(refactoring.get_changes())
        self.assertEquals('a = 1\na += 1\n', self.mod.read())

    def test_auto_indentation(self):
        self.mod.write('def f():\n    a = 2\n')
        refactoring = restructure.Restructure(
            self.project, '${?a} = 2', '${?a} = 1\n${?a} += 1')
        self.project.do(refactoring.get_changes())
        self.assertEquals('def f():\n    a = 1\n    a += 1\n', self.mod.read())

    def test_auto_indentation_and_not_indenting_blanks(self):
        self.mod.write('def f():\n    a = 2\n')
        refactoring = restructure.Restructure(
            self.project, '${?a} = 2', '${?a} = 1\n\n${?a} += 1')
        self.project.do(refactoring.get_changes())
        self.assertEquals('def f():\n    a = 1\n\n    a += 1\n',
                          self.mod.read())

    def test_importing_names(self):
        self.mod.write('a = 2\n')
        refactoring = restructure.Restructure(
            self.project, '${?a} = 2', '${?a} = myconsts.two')
        self.project.do(refactoring.get_changes(imports=['import myconsts']))
        self.assertEquals('import myconsts\na = myconsts.two\n',
                          self.mod.read())

    def test_not_importing_names_when_there_are_no_changes(self):
        self.mod.write('a = True\n')
        refactoring = restructure.Restructure(
            self.project, '${?a} = 2', '${?a} = myconsts.two')
        self.project.do(refactoring.get_changes(imports=['import myconsts']))
        self.assertEquals('a = True\n', self.mod.read())


if __name__ == '__main__':
    unittest.main()
