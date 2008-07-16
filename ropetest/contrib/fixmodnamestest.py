import unittest

from ropetest import testutils
from rope.contrib.fixmodnames import FixModuleNames


class FixModuleNamesTest(unittest.TestCase):

    def setUp(self):
        super(FixModuleNamesTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(FixModuleNamesTest, self).tearDown()

    def test_simple_module_renaming(self):
        mod = self.project.root.create_file('Mod.py')
        self.project.do(FixModuleNames(self.project).get_changes())
        self.assertFalse(mod.exists())
        self.assertTrue(self.project.get_resource('mod.py').exists)


if __name__ == '__main__':
    unittest.main()
