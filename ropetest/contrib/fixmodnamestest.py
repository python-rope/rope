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


if __name__ == '__main__':
    unittest.main()
