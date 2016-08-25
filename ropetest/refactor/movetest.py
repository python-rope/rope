try:
    import unittest2 as unittest
except ImportError:
    import unittest

from rope.base import exceptions
from rope.refactor import move
from ropetest import testutils


class MoveRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(MoveRefactoringTest, self).setUp()
        self.project = testutils.sample_project()
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.mod2 = testutils.create_module(self.project, 'mod2')
        self.mod3 = testutils.create_module(self.project, 'mod3')
        self.pkg = testutils.create_package(self.project, 'pkg')
        self.mod4 = testutils.create_module(self.project, 'mod4', self.pkg)
        self.mod5 = testutils.create_module(self.project, 'mod5', self.pkg)

    def tearDown(self):
        testutils.remove_project(self.project)
        super(MoveRefactoringTest, self).tearDown()

    def _move(self, resource, offset, dest_resource):
        changes = move.create_move(self.project, resource, offset).\
            get_changes(dest_resource)
        self.project.do(changes)

    def test_move_constant(self):
        self.mod1.write('foo = 123\n')
        self._move(self.mod1, self.mod1.read().index('foo') + 1,
                   self.mod2)
        self.assertEquals('', self.mod1.read())
        self.assertEquals('foo = 123\n', self.mod2.read())

    def test_move_constant_2(self):
        self.mod1.write('bar = 321\nfoo = 123\n')
        self._move(self.mod1, self.mod1.read().index('foo') + 1,
                   self.mod2)
        self.assertEquals('bar = 321\n', self.mod1.read())
        self.assertEquals('foo = 123\n', self.mod2.read())

    def test_move_constant_multiline(self):
        self.mod1.write('foo = (\n    123\n)\n')
        self._move(self.mod1, self.mod1.read().index('foo') + 1,
                   self.mod2)
        self.assertEquals('', self.mod1.read())
        self.assertEquals('foo = (\n    123\n)\n', self.mod2.read())

    def test_move_constant_multiple_statements(self):
        self.mod1.write('foo = 123\nfoo += 3\nfoo = 4\n')
        self._move(self.mod1, self.mod1.read().index('foo') + 1,
                   self.mod2)
        self.assertEquals('import mod2\nmod2.foo += 3\nmod2.foo = 4\n',
                          self.mod1.read())
        self.assertEquals('foo = 123\n', self.mod2.read())

    def test_simple_moving(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('', self.mod1.read())
        self.assertEquals('class AClass(object):\n    pass\n',
                          self.mod2.read())

    def test_moving_with_comment_prefix(self):
        self.mod1.write('a = 1\n# 1\n# 2\nclass AClass(object):\n    pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('a = 1\n', self.mod1.read())
        self.assertEquals('# 1\n# 2\nclass AClass(object):\n    pass\n',
                          self.mod2.read())

    def test_moving_with_comment_prefix_imports(self):
        self.mod1.write('import foo\na = 1\n# 1\n# 2\n'
                        'class AClass(foo.FooClass):\n    pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('a = 1\n', self.mod1.read())
        self.assertEquals('import foo\n\n\n# 1\n# 2\n'
                          'class AClass(foo.FooClass):\n    pass\n',
                          self.mod2.read())

    def test_changing_other_modules_replacing_normal_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod2\na_var = mod2.AClass()\n',
                          self.mod3.read())

    def test_changing_other_modules_adding_normal_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n'
                        'def a_function():\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n'
                        'mod1.a_function()')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod1\nimport mod2\na_var = mod2.AClass()\n' +
                          'mod1.a_function()', self.mod3.read())

    def test_adding_imports_prefer_from_module(self):
        self.project.prefs['prefer_module_from_imports'] = True
        self.mod1.write('class AClass(object):\n    pass\n'
                        'def a_function():\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n'
                        'mod1.a_function()')
        # Move to mod4 which is in a different package
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod4)
        self.assertEquals('import mod1\nfrom pkg import mod4\n'
                          'a_var = mod4.AClass()\nmod1.a_function()',
                          self.mod3.read())

    def test_adding_imports_noprefer_from_module(self):
        self.project.prefs['prefer_module_from_imports'] = False
        self.mod1.write('class AClass(object):\n    pass\n'
                        'def a_function():\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n'
                        'mod1.a_function()')
        # Move to mod4 which is in a different package
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod4)
        self.assertEquals('import mod1\nimport pkg.mod4\n'
                          'a_var = pkg.mod4.AClass()\nmod1.a_function()',
                          self.mod3.read())

    def test_adding_imports_prefer_from_module_top_level_module(self):
        self.project.prefs['prefer_module_from_imports'] = True
        self.mod1.write('class AClass(object):\n    pass\n'
                        'def a_function():\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n'
                        'mod1.a_function()')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod1\nimport mod2\na_var = mod2.AClass()\n' +
                          'mod1.a_function()', self.mod3.read())

    def test_changing_other_modules_removing_from_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod3.write('from mod1 import AClass\na_var = AClass()\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod2\na_var = mod2.AClass()\n',
                          self.mod3.read())

    def test_changing_source_module(self):
        self.mod1.write('class AClass(object):\n    pass\na_var = AClass()\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod2\na_var = mod2.AClass()\n',
                          self.mod1.read())

    def test_changing_destination_module(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod2.write('from mod1 import AClass\na_var = AClass()\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('class AClass(object):\n    '
                          'pass\na_var = AClass()\n',
                          self.mod2.read())

    def test_folder_destination(self):
        folder = self.project.root.create_folder('folder')
        self.mod1.write('class AClass(object):\n    pass\n')
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index('AClass') + 1, folder)

    def test_raising_exception_for_moving_non_global_elements(self):
        self.mod1.write(
            'def a_func():\n    class AClass(object):\n        pass\n')
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                       self.mod2)

    def test_raising_an_exception_for_moving_non_global_variable(self):
        code = 'class TestClass:\n    CONSTANT = 5\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod1,
                                     code.index('CONSTANT') + 1)

    def test_raising_exception_for_mov_glob_elemnts_to_the_same_module(self):
        self.mod1.write('def a_func():\n    pass\n')
        with self.assertRaises(exceptions.RefactoringError):
            self._move(self.mod1, self.mod1.read().index('a_func'), self.mod1)

    def test_moving_used_imports_to_destination_module(self):
        self.mod3.write('a_var = 10')
        code = 'import mod3\n' \
               'from mod3 import a_var\n' \
               'def a_func():\n' \
               '    print(mod3, a_var)\n'
        self.mod1.write(code)
        self._move(self.mod1, code.index('a_func') + 1, self.mod2)
        expected = 'import mod3\n' \
                   'from mod3 import a_var\n\n\n' \
                   'def a_func():\n    print(mod3, a_var)\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_used_names_to_destination_module2(self):
        code = 'a_var = 10\n' \
               'def a_func():\n' \
               '    print(a_var)\n'
        self.mod1.write(code)
        self._move(self.mod1, code.index('a_func') + 1, self.mod2)
        self.assertEquals('a_var = 10\n', self.mod1.read())
        expected = 'from mod1 import a_var\n\n\n' \
                   'def a_func():\n' \
                   '    print(a_var)\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_used_underlined_names_to_destination_module(self):
        code = '_var = 10\n' \
               'def a_func():\n' \
               '    print(_var)\n'
        self.mod1.write(code)
        self._move(self.mod1, code.index('a_func') + 1, self.mod2)
        expected = 'from mod1 import _var\n\n\n' \
                   'def a_func():\n' \
                   '    print(_var)\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_and_used_relative_imports(self):
        code = 'import mod5\n' \
               'def a_func():\n' \
               '    print(mod5)\n'
        self.mod4.write(code)
        self._move(self.mod4, code.index('a_func') + 1, self.mod1)
        expected = 'import pkg.mod5\n\n\n' \
                   'def a_func():\n' \
                   '    print(pkg.mod5)\n'
        self.assertEquals(expected, self.mod1.read())
        self.assertEquals('', self.mod4.read())

    def test_moving_modules(self):
        code = 'import mod1\nprint(mod1)'
        self.mod2.write(code)
        self._move(self.mod2, code.index('mod1') + 1, self.pkg)
        expected = 'import pkg.mod1\nprint(pkg.mod1)'
        self.assertEquals(expected, self.mod2.read())
        self.assertTrue(not self.mod1.exists() and
                        self.project.find_module('pkg.mod1') is not None)

    def test_moving_modules_and_removing_out_of_date_imports(self):
        code = 'import pkg.mod4\nprint(pkg.mod4)'
        self.mod2.write(code)
        self._move(self.mod2, code.index('mod4') + 1, self.project.root)
        expected = 'import mod4\nprint(mod4)'
        self.assertEquals(expected, self.mod2.read())
        self.assertTrue(self.project.find_module('mod4') is not None)

    def test_moving_modules_and_removing_out_of_date_froms(self):
        code = 'from pkg import mod4\nprint(mod4)'
        self.mod2.write(code)
        self._move(self.mod2, code.index('mod4') + 1, self.project.root)
        self.assertEquals('import mod4\nprint(mod4)', self.mod2.read())

    def test_moving_modules_and_removing_out_of_date_froms2(self):
        self.mod4.write('a_var = 10')
        code = 'from pkg.mod4 import a_var\nprint(a_var)\n'
        self.mod2.write(code)
        self._move(self.mod2, code.index('mod4') + 1, self.project.root)
        expected = 'from mod4 import a_var\nprint(a_var)\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_modules_and_relative_import(self):
        self.mod4.write('import mod5\nprint(mod5)\n')
        code = 'import pkg.mod4\nprint(pkg.mod4)'
        self.mod2.write(code)
        self._move(self.mod2, code.index('mod4') + 1, self.project.root)
        moved = self.project.find_module('mod4')
        expected = 'import pkg.mod5\nprint(pkg.mod5)\n'
        self.assertEquals(expected, moved.read())

    def test_moving_module_kwarg_same_name_as_old(self):
        self.mod1.write('def foo(mod1=0):\n    pass')
        code = 'import mod1\nmod1.foo(mod1=1)'
        self.mod2.write(code)
        self._move(self.mod1, None, self.pkg)
        moved = self.project.find_module('mod2')
        expected = 'import pkg.mod1\npkg.mod1.foo(mod1=1)'
        self.assertEquals(expected, moved.read())

    def test_moving_packages(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        code = 'import pkg.mod4\nprint(pkg.mod4)'
        self.mod1.write(code)
        self._move(self.mod1, code.index('pkg') + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.project.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.project.find_module('pkg2.pkg.mod5') is not None)
        expected = 'import pkg2.pkg.mod4\nprint(pkg2.pkg.mod4)'
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_with_self_imports(self):
        self.mod1.write('import mod1\nprint(mod1)\n')
        self.mod2.write('import mod1\n')
        self._move(self.mod2, self.mod2.read().index('mod1') + 1, self.pkg)
        moved = self.project.find_module('pkg.mod1')
        self.assertEquals('import pkg.mod1\nprint(pkg.mod1)\n', moved.read())

    def test_moving_modules_with_from_imports(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        code = ('from pkg import mod4\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod1, code.index('pkg') + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.project.find_module('pkg2.pkg.mod5') is not None)
        expected = ('from pkg2.pkg import mod4\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_with_from_import(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('from pkg import mod4\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('from pkg2.pkg3.pkg4 import mod4\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_with_multi_from_imports(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('from pkg import mod4, mod5\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('from pkg import mod5\n'
                    'from pkg2.pkg3.pkg4 import mod4\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_with_from_and_normal_imports(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('from pkg import mod4\n'
                'import pkg.mod4\n'
                'print(mod4)\n'
                'print(pkg.mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('import pkg2.pkg3.pkg4.mod4\n'
                    'from pkg2.pkg3.pkg4 import mod4\n'
                    'print(mod4)\n'
                    'print(pkg2.pkg3.pkg4.mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_with_normal_and_from_imports(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('import pkg.mod4\n'
                'from pkg import mod4\n'
                'print(mod4)\n'
                'print(pkg.mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('import pkg2.pkg3.pkg4.mod4\n'
                    'from pkg2.pkg3.pkg4 import mod4\n'
                    'print(mod4)\n'
                    'print(pkg2.pkg3.pkg4.mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_from_import_variable(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('from pkg.mod4 import foo\n'
                'print(foo)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('from pkg2.pkg3.pkg4.mod4 import foo\n'
                    'print(foo)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_modules_normal_import(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        pkg3 = testutils.create_package(self.project, 'pkg3', pkg2)
        pkg4 = testutils.create_package(self.project, 'pkg4', pkg3)
        code = ('import pkg.mod4\n'
                'print(pkg.mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg4)
        self.assertTrue(
            self.project.find_module('pkg2.pkg3.pkg4.mod4') is not None)
        expected = ('import pkg2.pkg3.pkg4.mod4\n'
                    'print(pkg2.pkg3.pkg4.mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_package_with_from_and_normal_imports(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        code = ('from pkg import mod4\n'
                'import pkg.mod4\n'
                'print(pkg.mod4)\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod1, code.index('pkg') + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.project.find_module('pkg2.pkg.mod5') is not None)
        expected = ('from pkg2.pkg import mod4\n'
                    'import pkg2.pkg.mod4\n'
                    'print(pkg2.pkg.mod4)\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_package_with_from_and_normal_imports2(self):
        pkg2 = testutils.create_package(self.project, 'pkg2')
        code = ('import pkg.mod4\n'
                'from pkg import mod4\n'
                'print(pkg.mod4)\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod1, code.index('pkg') + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.project.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.project.find_module('pkg2.pkg.mod5') is not None)
        expected = ('import pkg2.pkg.mod4\n'
                    'from pkg2.pkg import mod4\n'
                    'print(pkg2.pkg.mod4)\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_package_and_retaining_blank_lines(self):
        pkg2 = testutils.create_package(self.project, 'pkg2', self.pkg)
        code = ('"""Docstring followed by blank lines."""\n\n'
                'import pkg.mod4\n\n'
                'from pkg import mod4\n'
                'from x import y\n'
                'from y import z\n'
                'from a import b\n'
                'from b import c\n'
                'print(pkg.mod4)\n'
                'print(mod4)')
        self.mod1.write(code)
        self._move(self.mod4, None, pkg2)
        expected = ('"""Docstring followed by blank lines."""\n\n'
                    'import pkg.pkg2.mod4\n\n'
                    'from x import y\n'
                    'from y import z\n'
                    'from a import b\n'
                    'from b import c\n'
                    'from pkg.pkg2 import mod4\n'
                    'print(pkg.pkg2.mod4)\n'
                    'print(mod4)')
        self.assertEquals(expected, self.mod1.read())

    def test_moving_functions_to_imported_module(self):
        code = 'import mod1\n' \
               'def a_func():\n' \
               '    var = mod1.a_var\n'
        self.mod1.write('a_var = 1\n')
        self.mod2.write(code)
        self._move(self.mod2, code.index('a_func') + 1, self.mod1)
        expected = 'def a_func():\n' \
                   '    var = a_var\n' \
                   'a_var = 1\n'
        self.assertEquals(expected, self.mod1.read())

    def test_moving_resources_using_move_module_refactoring(self):
        self.mod1.write('a_var = 1')
        self.mod2.write('import mod1\nmy_var = mod1.a_var\n')
        mover = move.create_move(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        expected = 'import pkg.mod1\nmy_var = pkg.mod1.a_var\n'
        self.assertEquals(expected, self.mod2.read())
        self.assertTrue(self.pkg.get_child('mod1.py') is not None)

    def test_moving_resources_using_move_module_for_packages(self):
        self.mod1.write('import pkg\nmy_pkg = pkg')
        pkg2 = testutils.create_package(self.project, 'pkg2')
        mover = move.create_move(self.project, self.pkg)
        mover.get_changes(pkg2).do()
        expected = 'import pkg2.pkg\nmy_pkg = pkg2.pkg'
        self.assertEquals(expected, self.mod1.read())
        self.assertTrue(pkg2.get_child('pkg') is not None)

    def test_moving_resources_using_move_module_for_init_dot_py(self):
        self.mod1.write('import pkg\nmy_pkg = pkg')
        pkg2 = testutils.create_package(self.project, 'pkg2')
        init = self.pkg.get_child('__init__.py')
        mover = move.create_move(self.project, init)
        mover.get_changes(pkg2).do()
        self.assertEquals('import pkg2.pkg\nmy_pkg = pkg2.pkg',
                          self.mod1.read())
        self.assertTrue(pkg2.get_child('pkg') is not None)

    def test_moving_module_and_star_imports(self):
        self.mod1.write('a_var = 1')
        self.mod2.write('from mod1 import *\na = a_var\n')
        mover = move.create_move(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        self.assertEquals('from pkg.mod1 import *\na = a_var\n',
                          self.mod2.read())

    def test_moving_module_and_not_removing_blanks_after_imports(self):
        self.mod4.write('a_var = 1')
        self.mod2.write('from pkg import mod4\n'
                        'import os\n\n\nprint(mod4.a_var)\n')
        mover = move.create_move(self.project, self.mod4)
        mover.get_changes(self.project.root).do()
        self.assertEquals('import os\nimport mod4\n\n\n'
                          'print(mod4.a_var)\n', self.mod2.read())

    def test_moving_module_refactoring_and_nonexistent_destinations(self):
        self.mod4.write('a_var = 1')
        self.mod2.write('from pkg import mod4\n'
                        'import os\n\n\nprint(mod4.a_var)\n')
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod4)
            mover.get_changes(None).do()

    def test_moving_methods_choosing_the_correct_class(self):
        code = 'class A(object):\n    def a_method(self):\n        pass\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertTrue(isinstance(mover, move.MoveMethod))

    def test_moving_methods_getting_new_method_for_empty_methods(self):
        code = 'class A(object):\n    def a_method(self):\n        pass\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self):\n    pass\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_getting_new_method_for_constant_methods(self):
        code = 'class A(object):\n    def a_method(self):\n        return 1\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self):\n    return 1\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_getting_new_method_passing_simple_paremters(self):
        code = 'class A(object):\n' \
               '    def a_method(self, p):\n        return p\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self, p):\n    return p\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_getting_new_method_using_main_object(self):
        code = 'class A(object):\n    attr = 1\n' \
               '    def a_method(host):\n        return host.attr\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self, host):'
                          '\n    return host.attr\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_getting_new_method_renaming_main_object(self):
        code = 'class A(object):\n    attr = 1\n' \
               '    def a_method(self):\n        return self.attr\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self, host):'
                          '\n    return host.attr\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_gettin_new_method_with_keyword_arguments(self):
        code = 'class A(object):\n    attr = 1\n' \
               '    def a_method(self, p=None):\n        return p\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals('def new_method(self, p=None):\n    return p\n',
                          mover.get_new_method('new_method'))

    def test_moving_methods_gettin_new_method_with_many_kinds_arguments(self):
        code = 'class A(object):\n    attr = 1\n' \
               '    def a_method(self, p1, *args, **kwds):\n' \
               '        return self.attr\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        expected = 'def new_method(self, host, p1, *args, **kwds):\n' \
                   '    return host.attr\n'
        self.assertEquals(expected, mover.get_new_method('new_method'))

    def test_moving_methods_getting_new_method_for_multi_line_methods(self):
        code = 'class A(object):\n' \
               '    def a_method(self):\n' \
               '        a = 2\n' \
               '        return a\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        self.assertEquals(
            'def new_method(self):\n    a = 2\n    return a\n',
            mover.get_new_method('new_method'))

    def test_moving_methods_getting_old_method_for_constant_methods(self):
        self.mod2.write('class B(object):\n    pass\n')
        code = 'import mod2\n\n' \
               'class A(object):\n' \
               '    attr = mod2.B()\n' \
               '    def a_method(self):\n' \
               '        return 1\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        expected = 'import mod2\n\n' \
                   'class A(object):\n' \
                   '    attr = mod2.B()\n' \
                   '    def a_method(self):\n' \
                   '        return self.attr.new_method()\n'
        self.assertEquals(expected, self.mod1.read())

    def test_moving_methods_getting_getting_changes_for_goal_class(self):
        self.mod2.write('class B(object):\n    var = 1\n')
        code = 'import mod2\n\n' \
               'class A(object):\n' \
               '    attr = mod2.B()\n' \
               '    def a_method(self):\n' \
               '        return 1\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        expected = 'class B(object):\n' \
                   '    var = 1\n\n\n' \
                   '    def new_method(self):\n' \
                   '        return 1\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class2(self):
        code = 'class B(object):\n    var = 1\n\n' \
               'class A(object):\n    attr = B()\n' \
               '    def a_method(self):\n        return 1\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        self.assertEquals(
            'class B(object):\n    var = 1\n\n\n'
            '    def new_method(self):\n'
            '        return 1\n\n'
            'class A(object):\n    attr = B()\n'
            '    def a_method(self):\n'
            '        return self.attr.new_method()\n',
            self.mod1.read())

    def test_moving_methods_and_nonexistent_attributes(self):
        code = 'class A(object):\n' \
               '    def a_method(self):\n        return 1\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod1,
                                     code.index('a_method'))
            mover.get_changes('x', 'new_method')

    def test_unknown_attribute_type(self):
        code = 'class A(object):\n    attr = 1\n' \
               '    def a_method(self):\n        return 1\n'
        self.mod1.write(code)
        with self.assertRaises(exceptions.RefactoringError):
            mover = move.create_move(self.project, self.mod1,
                                     code.index('a_method'))
            mover.get_changes('attr', 'new_method')

    def test_moving_methods_and_moving_used_imports(self):
        self.mod2.write('class B(object):\n    var = 1\n')
        code = 'import sys\nimport mod2\n\n' \
               'class A(object):\n' \
               '    attr = mod2.B()\n' \
               '    def a_method(self):\n' \
               '        return sys.version\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        code = 'import sys\n' \
               'class B(object):\n' \
               '    var = 1\n\n\n' \
               '    def new_method(self):\n' \
               '        return sys.version\n'
        self.assertEquals(code, self.mod2.read())

    def test_moving_methods_getting_getting_changes_for_goal_class3(self):
        self.mod2.write('class B(object):\n    pass\n')
        code = 'import mod2\n\n' \
               'class A(object):\n' \
               '    attr = mod2.B()\n' \
               '    def a_method(self):\n' \
               '        return 1\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        expected = 'class B(object):\n\n' \
                   '    def new_method(self):\n' \
                   '        return 1\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_methods_and_source_class_with_parameters(self):
        self.mod2.write('class B(object):\n    pass\n')
        code = 'import mod2\n\n' \
               'class A(object):\n' \
               '    attr = mod2.B()\n' \
               '    def a_method(self, p):\n        return p\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('a_method'))
        mover.get_changes('attr', 'new_method').do()
        expected1 = 'import mod2\n\n' \
                    'class A(object):\n' \
                    '    attr = mod2.B()\n' \
                    '    def a_method(self, p):\n' \
                    '        return self.attr.new_method(p)\n'
        self.assertEquals(expected1, self.mod1.read())
        expected2 = 'class B(object):\n\n' \
                    '    def new_method(self, p):\n' \
                    '        return p\n'
        self.assertEquals(expected2, self.mod2.read())

    def test_moving_globals_to_a_module_with_only_docstrings(self):
        self.mod1.write('import sys\n\n\ndef f():\n    print(sys.version)\n')
        self.mod2.write('"""doc\n\nMore docs ...\n\n"""\n')
        mover = move.create_move(self.project, self.mod1,
                                 self.mod1.read().index('f()') + 1)
        self.project.do(mover.get_changes(self.mod2))
        self.assertEquals(
            '"""doc\n\nMore docs ...\n\n"""\n'
            'import sys\n\n\ndef f():\n    print(sys.version)\n',
            self.mod2.read())

    def test_moving_globals_to_a_module_with_only_docstrings2(self):
        code = 'import os\n' \
               'import sys\n\n\n' \
               'def f():\n' \
               '    print(sys.version, os.path)\n'
        self.mod1.write(code)
        self.mod2.write('"""doc\n\nMore docs ...\n\n"""\n')
        mover = move.create_move(self.project, self.mod1,
                                 self.mod1.read().index('f()') + 1)
        self.project.do(mover.get_changes(self.mod2))
        expected = '"""doc\n\nMore docs ...\n\n"""\n' \
                   'import os\n' \
                   'import sys\n\n\n' \
                   'def f():\n' \
                   '    print(sys.version, os.path)\n'
        self.assertEquals(expected, self.mod2.read())

    def test_moving_a_global_when_it_is_used_after_a_multiline_str(self):
        code = 'def f():\n    pass\ns = """\\\n"""\nr = f()\n'
        self.mod1.write(code)
        mover = move.create_move(self.project, self.mod1,
                                 code.index('f()') + 1)
        self.project.do(mover.get_changes(self.mod2))
        expected = 'import mod2\ns = """\\\n"""\nr = mod2.f()\n'
        self.assertEquals(expected, self.mod1.read())

    def test_raising_an_exception_when_moving_non_package_folders(self):
        dir = self.project.root.create_folder('dir')
        with self.assertRaises(exceptions.RefactoringError):
            move.create_move(self.project, dir)

    def test_moving_to_a_module_with_encoding_cookie(self):
        code1 = '# -*- coding: utf-8 -*-'
        self.mod1.write(code1)
        code2 = 'def f(): pass\n'
        self.mod2.write(code2)
        mover = move.create_move(self.project, self.mod2,
                                 code2.index('f()') + 1)
        self.project.do(mover.get_changes(self.mod1))
        expected = '%s\n%s' % (code1, code2)
        self.assertEquals(expected, self.mod1.read())


if __name__ == '__main__':
    unittest.main()
