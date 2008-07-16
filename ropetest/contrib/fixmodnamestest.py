import unittest

from ropetest import testutils
from rope.contrib.fixmodnames import FixModuleNames
from rope.contrib.generate import create_module, create_package


class FixModuleNamesTest(unittest.TestCase):

    def setUp(self):
        super(FixModuleNamesTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(FixModuleNamesTest, self).tearDown()

    def test_simple_module_renaming(self):
        mod = create_module(self.project, 'Mod')
        self.project.do(FixModuleNames(self.project).get_changes())
        self.assertFalse(mod.exists())
        self.assertTrue(self.project.get_resource('mod.py').exists())

    def test_packages_module_renaming(self):
        pkg = create_package(self.project, 'Pkg')
        self.project.do(FixModuleNames(self.project).get_changes())
        self.assertFalse(pkg.exists())
        self.assertTrue(self.project.get_resource('pkg/__init__.py').exists())

    def test_fixing_contents(self):
        mod1 = create_module(self.project, 'Mod1')
        mod2 = create_module(self.project, 'Mod2')
        mod1.write('import Mod2\n')
        mod2.write('import Mod1\n')
        self.project.do(FixModuleNames(self.project).get_changes())
        newmod1 = self.project.get_resource('mod1.py')
        newmod2 = self.project.get_resource('mod2.py')
        self.assertEquals('import mod2\n', newmod1.read())
        self.assertEquals('import mod1\n', newmod2.read())


if __name__ == '__main__':
    unittest.main()
