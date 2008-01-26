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
        self.importer = autoimport.AutoImport(self.project, observe=False)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AutoImportTest, self).tearDown()

    def test_simple_case(self):
        self.assertEquals([], self.importer.import_assist('A'))

    def test_update_resource(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([('myvar', 'mod1')],
                          self.importer.import_assist('myva'))

    def test_update_module(self):
        self.mod1.write('myvar = None')
        self.importer.update_module('mod1')
        self.assertEquals([('myvar', 'mod1')],
                          self.importer.import_assist('myva'))

    def test_update_non_existent_module(self):
        self.importer.update_module('does_not_exists_this')
        self.assertEquals([], self.importer.import_assist('myva'))

    def test_module_with_syntax_errors(self):
        self.mod1.write('this is a syntax error\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([], self.importer.import_assist('myva'))

    def test_excluding_imported_names(self):
        self.mod1.write('import pkg\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals([], self.importer.import_assist('pkg'))

    def test_get_modules(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEquals(['mod1'], self.importer.get_modules('myvar'))

    def test_get_modules_inside_packages(self):
        self.mod1.write('myvar = None\n')
        self.mod2.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.importer.update_resource(self.mod2)
        self.assertEquals(set(['mod1', 'pkg.mod2']),
                          set(self.importer.get_modules('myvar')))

    def test_trivial_insertion_line(self):
        result = self.importer.find_insertion_line('')
        self.assertEquals(1, result)

    def test_insertion_line(self):
        result = self.importer.find_insertion_line('import mod\n')
        self.assertEquals(2, result)

    def test_insertion_line_with_pydocs(self):
        result = self.importer.find_insertion_line(
            '"""docs\n\ndocs"""\nimport mod\n')
        self.assertEquals(5, result)

    def test_insertion_line_with_multiple_imports(self):
        result = self.importer.find_insertion_line(
            'import mod1\n\nimport mod2\n')
        self.assertEquals(4, result)


class AutoImportObservingTest(unittest.TestCase):

    def setUp(self):
        super(AutoImportObservingTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.pkg = testutils.create_package(self.project, 'pkg')
        self.mod2 = testutils.create_module(self.project, 'mod2', self.pkg)
        self.importer = autoimport.AutoImport(self.project, observe=True)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AutoImportObservingTest, self).tearDown()

    def test_writing_files(self):
        self.mod1.write('myvar = None\n')
        self.assertEquals(['mod1'], self.importer.get_modules('myvar'))

    def test_moving_files(self):
        self.mod1.write('myvar = None\n')
        self.mod1.move('mod3.py')
        self.assertEquals(['mod3'], self.importer.get_modules('myvar'))

    def test_removing_files(self):
        self.mod1.write('myvar = None\n')
        self.mod1.remove()
        self.assertEquals([], self.importer.get_modules('myvar'))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(AutoImportTest))
    result.addTests(unittest.makeSuite(AutoImportObservingTest))
    return result

if __name__ == '__main__':
    unittest.main()
