import unittest

import rope.base.exceptions
import rope.base.project
import ropetest
from rope.refactor import move


class MoveRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(MoveRefactoringTest, self).setUp()
        self.project_root = 'sampleproject'
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.mod1 = self.pycore.create_module(self.project.root, 'mod1')
        self.mod2 = self.pycore.create_module(self.project.root, 'mod2')
        self.mod3 = self.pycore.create_module(self.project.root, 'mod3')
        self.pkg = self.pycore.create_package(self.project.root, 'pkg')
        self.mod4 = self.pycore.create_module(self.pkg, 'mod4')
        self.mod5 = self.pycore.create_module(self.pkg, 'mod5')

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
        super(MoveRefactoringTest, self).tearDown()

    def _move(self, resource, offset, dest_resource):
        changes = move.MoveRefactoring(self.project, resource, offset).\
                  get_changes(dest_resource)
        self.project.do(changes)

    def test_simple_moving(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('', self.mod1.read())
        self.assertEquals('class AClass(object):\n    pass\n',
                          self.mod2.read())

    def test_changing_other_modules_adding_normal_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)
        self.assertEquals('import mod1\nimport mod2\na_var = mod2.AClass()\n',
                          self.mod3.read())

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
        self.assertEquals('class AClass(object):\n    pass\na_var = AClass()\n',
                          self.mod2.read())

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringError)
    def test_folder_destination(self):
        folder = self.project.root.create_folder('folder')
        self.mod1.write('class AClass(object):\n    pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1, folder)

    @ropetest.testutils.assert_raises(rope.base.exceptions.RefactoringError)
    def test_raising_exception_for_moving_non_global_elements(self):
        self.mod1.write('def a_func():\n    class AClass(object):\n        pass\n')
        self._move(self.mod1, self.mod1.read().index('AClass') + 1,
                   self.mod2)

    def test_moving_used_imports_to_destination_module(self):
        self.mod3.write('a_var = 10')
        self.mod1.write('import mod3\nfrom mod3 import a_var\n' \
                        'def a_func():\n    print mod3, a_var\n')
        self._move(self.mod1, self.mod1.read().index('a_func') + 1,
                   self.mod2)
        self.assertEquals('import mod3\n\n\n' \
                          'def a_func():\n    print mod3, mod3.a_var\n',
                          self.mod2.read())

    def test_moving_used_names_to_destination_module2(self):
        self.mod1.write('a_var = 10\n' \
                        'def a_func():\n    print a_var\n')
        self._move(self.mod1, self.mod1.read().index('a_func') + 1,
                   self.mod2)
        self.assertEquals('a_var = 10\n', self.mod1.read())
        self.assertEquals('import mod1\n\n\ndef a_func():\n    print mod1.a_var\n',
                          self.mod2.read())

    def test_moving_and_used_relative_imports(self):
        self.mod4.write('import mod5\n' \
                        'def a_func():\n    print mod5\n')
        self._move(self.mod4, self.mod4.read().index('a_func') + 1,
                   self.mod1)
        self.assertEquals('import pkg.mod5\n\n\ndef a_func():\n    print pkg.mod5\n',
                          self.mod1.read())

    def test_moving_modules(self):
        self.mod2.write('import mod1\nprint mod1')
        self._move(self.mod2, self.mod2.read().index('mod1') + 1, self.pkg)
        self.assertEquals('import pkg.mod1\nprint pkg.mod1', self.mod2.read())
        self.assertTrue(not self.mod1.exists() and
                        self.pycore.find_module('pkg.mod1') is not None)

    def test_moving_modules_and_removing_out_of_date_imports(self):
        self.mod2.write('import pkg.mod4\nprint pkg.mod4')
        self._move(self.mod2, self.mod2.read().index('mod4') + 1,
                   self.project.root)
        self.assertEquals('import mod4\nprint mod4', self.mod2.read())
        self.assertTrue(self.pycore.find_module('mod4') is not None)

    def test_moving_modules_and_removing_out_of_date_froms(self):
        self.mod2.write('from pkg import mod4\nprint mod4')
        self._move(self.mod2, self.mod2.read().index('mod4') + 1,
                   self.project.root)
        self.assertEquals('import mod4\nprint mod4', self.mod2.read())

    def test_moving_modules_and_removing_out_of_date_froms2(self):
        self.mod4.write('a_var = 10')
        self.mod2.write('from pkg.mod4 import a_var\nprint a_var\n')
        self._move(self.mod2, self.mod2.read().index('mod4') + 1,
                   self.project.root)
        self.assertEquals('from mod4 import a_var\nprint a_var\n',
                          self.mod2.read())

    def test_moving_modules_and_relative_import(self):
        self.mod4.write('import mod5\nprint mod5\n')
        self.mod2.write('import pkg.mod4\nprint pkg.mod4')
        self._move(self.mod2, self.mod2.read().index('mod4') + 1,
                   self.project.root)
        moved = self.pycore.find_module('mod4')
        self.assertEquals('import pkg.mod5\nprint pkg.mod5\n', moved.read())

    def test_moving_packages(self):
        pkg2 = self.pycore.create_package(self.project.root, 'pkg2')
        self.mod1.write('import pkg.mod4\nprint pkg.mod4')
        self._move(self.mod1, self.mod1.read().index('pkg') + 1, pkg2)
        self.assertFalse(self.pkg.exists())
        self.assertTrue(self.pycore.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.pycore.find_module('pkg2.pkg.mod4') is not None)
        self.assertTrue(self.pycore.find_module('pkg2.pkg.mod5') is not None)
        self.assertEquals('import pkg2.pkg.mod4\nprint pkg2.pkg.mod4', self.mod1.read())

    def test_moving_modules_with_self_imports(self):
        self.mod1.write('import mod1\nprint mod1\n')
        self.mod2.write('import mod1\n')
        self._move(self.mod2, self.mod2.read().index('mod1') + 1, self.pkg)
        moved = self.pycore.find_module('pkg.mod1')
        self.assertEquals('import pkg.mod1\nprint pkg.mod1\n', moved.read())

    def test_moving_funtions_to_imported_module(self):
        self.mod1.write('a_var = 1\n')
        self.mod2.write('import mod1\ndef a_func():\n    var = mod1.a_var\n')
        self._move(self.mod2, self.mod2.read().index('a_func') + 1, self.mod1)
        self.assertEquals('def a_func():\n    var = a_var\na_var = 1\n', self.mod1.read())

    def test_moving_resources_using_move_module_refactoring(self):
        self.mod1.write('a_var = 1')
        self.mod2.write('import mod1\nmy_var = mod1.a_var\n')
        mover = move.MoveRefactoring(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        self.assertEquals('import pkg.mod1\nmy_var = pkg.mod1.a_var\n', self.mod2.read())
        self.assertTrue(self.pkg.get_child('mod1.py') is not None)

    def test_moving_resources_using_move_module_refactoring_for_packages(self):
        self.mod1.write('import pkg\nmy_pkg = pkg')
        pkg2 = self.pycore.create_package(self.project.root, 'pkg2')
        mover = move.MoveRefactoring(self.project, self.pkg)
        mover.get_changes(pkg2).do()
        self.assertEquals('import pkg2.pkg\nmy_pkg = pkg2.pkg', self.mod1.read())
        self.assertTrue(pkg2.get_child('pkg') is not None)

    def test_moving_resources_using_move_module_refactoring_for_init_dot_py(self):
        self.mod1.write('import pkg\nmy_pkg = pkg')
        pkg2 = self.pycore.create_package(self.project.root, 'pkg2')
        mover = move.MoveRefactoring(self.project, self.pkg.get_child('__init__.py'))
        mover.get_changes(pkg2).do()
        self.assertEquals('import pkg2.pkg\nmy_pkg = pkg2.pkg', self.mod1.read())
        self.assertTrue(pkg2.get_child('pkg') is not None)

    def test_moving_module_refactoring_and_star_imports(self):
        self.mod1.write('a_var = 1')
        self.mod2.write('from mod1 import *\na = a_var\n')
        mover = move.MoveRefactoring(self.project, self.mod1)
        mover.get_changes(self.pkg).do()
        self.assertEquals('from pkg.mod1 import *\na = a_var\n', self.mod2.read())

    # XXX: Removing imports, removes blanks lines after it
    def xxx_test_moving_module_refactoring_and_not_changing_other_modules(self):
        self.mod4.write('a_var = 1')
        self.mod2.write('from pkg import mod4\n'
                        'import os\n\n\nprint mod4.a_var\n')
        mover = move.MoveRefactoring(self.project, self.mod4)
        mover.get_changes(self.project.root).do()
        self.assertEquals('import os\nimport mod4\n\n\n'
                          'print mod4.a_var\n', self.mod2.read())


if __name__ == '__main__':
    unittest.main()
