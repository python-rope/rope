try:
    import unittest2 as unittest
except ImportError:
    import unittest

from ropetest import testutils
from rope.contrib import autoimport


class AutoImportTest(unittest.TestCase):

    def setUp(self):
        super(AutoImportTest, self).setUp()
        self.project = testutils.sample_project(extension_modules=['sys'])
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.pkg = testutils.create_package(self.project, 'pkg')
        self.mod2 = testutils.create_module(self.project, 'mod2', self.pkg)
        self.importer = autoimport.AutoImport(self.project, observe=False)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(AutoImportTest, self).tearDown()

    def test_simple_case(self):
        self.assertEqual([], self.importer.import_assist('A'))

    def test_update_resource(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual([('myvar', 'mod1')],
                          self.importer.import_assist('myva'))

    def test_update_module(self):
        self.mod1.write('myvar = None')
        self.importer.update_module('mod1')
        self.assertEqual([('myvar', 'mod1')],
                          self.importer.import_assist('myva'))

    def test_update_non_existent_module(self):
        self.importer.update_module('does_not_exists_this')
        self.assertEqual([], self.importer.import_assist('myva'))

    def test_module_with_syntax_errors(self):
        self.mod1.write('this is a syntax error\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual([], self.importer.import_assist('myva'))

    def test_excluding_imported_names(self):
        self.mod1.write('import pkg\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual([], self.importer.import_assist('pkg'))

    def test_get_modules(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual(['mod1'], self.importer.get_modules('myvar'))

    def test_get_modules_inside_packages(self):
        self.mod1.write('myvar = None\n')
        self.mod2.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.importer.update_resource(self.mod2)
        self.assertEqual(set(['mod1', 'pkg.mod2']),
                          set(self.importer.get_modules('myvar')))

    def test_trivial_insertion_line(self):
        result = self.importer.find_insertion_line('')
        self.assertEqual(1, result)

    def test_insertion_line(self):
        result = self.importer.find_insertion_line('import mod\n')
        self.assertEqual(2, result)

    def test_insertion_line_with_pydocs(self):
        result = self.importer.find_insertion_line(
            '"""docs\n\ndocs"""\nimport mod\n')
        self.assertEqual(5, result)

    def test_insertion_line_with_multiple_imports(self):
        result = self.importer.find_insertion_line(
            'import mod1\n\nimport mod2\n')
        self.assertEqual(4, result)

    def test_insertion_line_with_blank_lines(self):
        result = self.importer.find_insertion_line(
            'import mod1\n\n# comment\n')
        self.assertEqual(2, result)

    def test_empty_cache(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual(['mod1'], self.importer.get_modules('myvar'))
        self.importer.clear_cache()
        self.assertEqual([], self.importer.get_modules('myvar'))

    def test_not_caching_underlined_names(self):
        self.mod1.write('_myvar = None\n')
        self.importer.update_resource(self.mod1, underlined=False)
        self.assertEqual([], self.importer.get_modules('_myvar'))
        self.importer.update_resource(self.mod1, underlined=True)
        self.assertEqual(['mod1'], self.importer.get_modules('_myvar'))

    def test_caching_underlined_names_passing_to_the_constructor(self):
        importer = autoimport.AutoImport(self.project, False, True)
        self.mod1.write('_myvar = None\n')
        importer.update_resource(self.mod1)
        self.assertEqual(['mod1'], importer.get_modules('_myvar'))

    def test_name_locations(self):
        self.mod1.write('myvar = None\n')
        self.importer.update_resource(self.mod1)
        self.assertEqual([(self.mod1, 1)],
                          self.importer.get_name_locations('myvar'))

    def test_name_locations_with_multiple_occurrences(self):
        self.mod1.write('myvar = None\n')
        self.mod2.write('\nmyvar = None\n')
        self.importer.update_resource(self.mod1)
        self.importer.update_resource(self.mod2)
        self.assertEqual(set([(self.mod1, 1), (self.mod2, 2)]),
                          set(self.importer.get_name_locations('myvar')))

    def test_handling_builtin_modules(self):
        self.importer.update_module('sys')
        self.assertTrue('sys' in self.importer.get_modules('exit'))

    def test_submodules(self):
        self.assertEqual(set([self.mod1]),
                          autoimport.submodules(self.mod1))
        self.assertEqual(set([self.mod2, self.pkg]),
                          autoimport.submodules(self.pkg))


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
        self.assertEqual(['mod1'], self.importer.get_modules('myvar'))

    def test_moving_files(self):
        self.mod1.write('myvar = None\n')
        self.mod1.move('mod3.py')
        self.assertEqual(['mod3'], self.importer.get_modules('myvar'))

    def test_removing_files(self):
        self.mod1.write('myvar = None\n')
        self.mod1.remove()
        self.assertEqual([], self.importer.get_modules('myvar'))


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(AutoImportTest))
    result.addTests(unittest.makeSuite(AutoImportObservingTest))
    return result

if __name__ == '__main__':
    unittest.main()
