try:
    import unittest2 as unittest
except ImportError:
    import unittest


from ropetest import testutils
from rope.contrib.fixmodnames import FixModuleNames
from rope.contrib.generate import create_module, create_package


# HACK: for making this test work on case-insensitive file-systems, it
# uses a name.replace('x', '_') fixer.
class FixModuleNamesTest(unittest.TestCase):

    def setUp(self):
        super(FixModuleNamesTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(FixModuleNamesTest, self).tearDown()

    def test_simple_module_renaming(self):
        mod = create_module(self.project, 'xod')
        self.project.do(FixModuleNames(self.project).get_changes(_fixer))
        self.assertFalse(mod.exists())
        self.assertTrue(self.project.get_resource('_od.py').exists())

    def test_packages_module_renaming(self):
        pkg = create_package(self.project, 'xkg')
        self.project.do(FixModuleNames(self.project).get_changes(_fixer))
        self.assertFalse(pkg.exists())
        self.assertTrue(self.project.get_resource('_kg/__init__.py').exists())

    def test_fixing_contents(self):
        mod1 = create_module(self.project, 'xod1')
        mod2 = create_module(self.project, 'xod2')
        mod1.write('import xod2\n')
        mod2.write('import xod1\n')
        self.project.do(FixModuleNames(self.project).get_changes(_fixer))
        newmod1 = self.project.get_resource('_od1.py')
        newmod2 = self.project.get_resource('_od2.py')
        self.assertEqual('import _od2\n', newmod1.read())
        self.assertEqual('import _od1\n', newmod2.read())

    def test_handling_nested_modules(self):
        pkg = create_package(self.project, 'xkg')
        mod = create_module(self.project, 'xkg.xod')  # noqa
        self.project.do(FixModuleNames(self.project).get_changes(_fixer))
        self.assertFalse(pkg.exists())
        self.assertTrue(self.project.get_resource('_kg/__init__.py').exists())
        self.assertTrue(self.project.get_resource('_kg/_od.py').exists())


def _fixer(name):
    return name.replace('x', '_')

if __name__ == '__main__':
    unittest.main()
