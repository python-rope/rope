import unittest

from ropetest import testutils
from rope.contrib import autoimport


class AutoImportTest(unittest.TestCase):

    def setUp(self):
        super(AutoImportTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.pkg = testutils.create_package(self.project, 'pkg')
        self.mod2 = testutils.create_module(self.project, 'mod2', self.pkg)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AutoImportTest, self).tearDown()

    def test_simple_case(self):
        importer = autoimport.AutoImport(self.project)
        self.assertEquals([], importer.get_imports('A'))

    def test_update_resource(self):
        importer = autoimport.AutoImport(self.project)
        self.mod1.write('myvar = None')
        importer.update_resource(self.mod1)
        self.assertEquals([('myvar', 'mod1')],
                          importer.get_imports('myva'))

    def test_update_module(self):
        importer = autoimport.AutoImport(self.project)
        self.mod1.write('myvar = None')
        importer.update_module('mod1')
        self.assertEquals([('myvar', 'mod1')],
                          importer.get_imports('myva'))


if __name__ == '__main__':
    unittest.main()
