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
        self.importer = autoimport.AutoImport(self.project)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AutoImportTest, self).tearDown()

    def test_simple_case(self):
        self.assertEquals([], self.importer.get_imports('A'))

    def test_update_resource(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([('myvar', 'mod1')],
                          self.importer.get_imports('myva'))

    def test_update_module(self):
        self.mod1.write('myvar = None')
        self.importer.update_module('mod1')
        self.assertEquals([('myvar', 'mod1')],
                          self.importer.get_imports('myva'))

    def test_update_non_existent_module(self):
        self.importer.update_module('does_not_exists_this')
        self.assertEquals([], self.importer.get_imports('myva'))

    def test_module_with_syntax_errors(self):
        self.mod1.write('this is a syntax error\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([], self.importer.get_imports('myva'))

    def test_excluding_imported_names(self):
        self.mod1.write('import pkg\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([], self.importer.get_imports('pkg'))


if __name__ == '__main__':
    unittest.main()
