import unittest

import rope.codeanalyze
import rope.refactor.rename
from rope.refactor import Undo
from rope.exceptions import RefactoringException
from rope.project import Project
from rope.refactor.change import *
from ropetest import testutils
import ropetest.refactor.renametest
import ropetest.refactor.extracttest
import ropetest.refactor.movetest
import ropetest.refactor.inlinetest


class IntroduceFactoryTest(unittest.TestCase):

    def setUp(self):
        super(IntroduceFactoryTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(IntroduceFactoryTest, self).tearDown()
    
    def test_adding_the_method(self):
        code = 'class AClass(object):\n    an_attr = 10\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_the_main_module(self):
        code = 'class AClass(object):\n    an_attr = 10\na_var = AClass()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'\
                   'a_var = AClass.create()'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_with_arguments(self):
        code = 'class AClass(object):\n    def __init__(self, arg):\n        pass\n' \
               'a_var = AClass(10)\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    def __init__(self, arg):\n        pass\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n' \
                   'a_var = AClass.create(10)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_other_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1, 'create')
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.AClass.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_for_non_classes(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write('def a_func():\n    pass\n')
        self.refactoring.introduce_factory(mod, mod.read().index('a_func') + 1, 'create')

    def test_undoing_introduce_factory(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        code1 = 'class AClass(object):\n    an_attr = 10\n'
        mod1.write(code1)
        code2 = 'from mod1 import AClass\na_var = AClass()\n'
        mod2.write(code2)
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1, 'create')
        self.refactoring.undo()
        self.assertEquals(code1, mod1.read())
        self.assertEquals(code2, mod2.read())
    
    def test_using_on_an_occurance_outside_the_main_module(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod2, mod2.read().index('AClass') + 1, 'create')
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.AClass.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    def test_introduce_factory_in_nested_scopes(self):
        code = 'def create_var():\n'\
               '    class AClass(object):\n'\
               '        an_attr = 10\n'\
               '    return AClass()\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'def create_var():\n'\
                   '    class AClass(object):\n'\
                   '        an_attr = 10\n\n'\
                   '        @staticmethod\n        def create(*args, **kwds):\n'\
                   '            return AClass(*args, **kwds)\n'\
                   '    return AClass.create()\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_adding_factory_for_global_factories(self):
        code = 'class AClass(object):\n    an_attr = 10\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   'def create(*args, **kwds):\n' \
                   '    return AClass(*args, **kwds)\n'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)
        self.assertEquals(expected, mod.read())

    @testutils.assert_raises(rope.exceptions.RefactoringException)
    def test_raising_exception_for_global_factory_for_nested_classes(self):
        code = 'def create_var():\n'\
               '    class AClass(object):\n'\
               '        an_attr = 10\n'\
               '    return AClass()\n'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)

    def test_changing_occurances_in_the_main_module_for_global_factories(self):
        code = 'class AClass(object):\n    an_attr = 10\na_var = AClass()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   'def create(*args, **kwds):\n' \
                   '    return AClass(*args, **kwds)\n'\
                   'a_var = create()'
        self.refactoring.introduce_factory(mod, mod.read().index('AClass') + 1,
                                           'create', global_factory=True)
        self.assertEquals(expected, mod.read())

    def test_changing_occurances_in_other_modules_for_global_factories(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1,
                                           'create', global_factory=True)
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                    'def create(*args, **kwds):\n' \
                    '    return AClass(*args, **kwds)\n'
        expected2 = 'import mod1\na_var = mod1.create()\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    def test_importing_if_necessary_in_other_modules_for_global_factories(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('class AClass(object):\n    an_attr = 10\n')
        mod2.write('from mod1 import AClass\npair = AClass(), AClass\n')
        self.refactoring.introduce_factory(mod1, mod1.read().index('AClass') + 1,
                                           'create', global_factory=True)
        expected1 = 'class AClass(object):\n    an_attr = 10\n\n' \
                    'def create(*args, **kwds):\n' \
                    '    return AClass(*args, **kwds)\n'
        expected2 = 'from mod1 import AClass\nimport mod1\npair = mod1.create(), AClass\n'
        self.assertEquals(expected1, mod1.read())
        self.assertEquals(expected2, mod2.read())

    # XXX: Should we replace `a_class` here with `AClass.create` too
    def test_changing_occurances_for_renamed_classes(self):
        code = 'class AClass(object):\n    an_attr = 10\na_class = AClass\na_var = a_class()'
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write(code)
        expected = 'class AClass(object):\n    an_attr = 10\n\n' \
                   '    @staticmethod\n    def create(*args, **kwds):\n' \
                   '        return AClass(*args, **kwds)\n' \
                   'a_class = AClass\n' \
                   'a_var = a_class()'
        self.refactoring.introduce_factory(mod, mod.read().index('a_class') + 1, 'create')
        self.assertEquals(expected, mod.read())

    def test_transform_module_to_package(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod2)
        mod2 = self.project.get_resource('mod2')
        root_folder = self.project.get_root_folder()
        self.assertFalse(root_folder.has_child('mod2.py'))
        self.assertEquals('class AClass(object):\n    pass\n', root_folder.get_child('mod2').
                          get_child('__init__.py').read())

    def test_transform_module_to_package_undoing(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod = self.pycore.create_module(pkg, 'mod')
        self.refactoring.transform_module_to_package(mod)
        self.assertFalse(pkg.has_child('mod.py'))
        self.assertTrue(pkg.get_child('mod').has_child('__init__.py'))
        self.refactoring.undo()
        self.assertTrue(pkg.has_child('mod.py'))
        self.assertFalse(pkg.has_child('mod'))

    def test_transform_module_to_package_with_relative_imports(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod1.write('import mod2\nfrom mod2 import AClass\n')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('class AClass(object):\n    pass\n')
        self.refactoring.transform_module_to_package(mod1)
        new_init = self.project.get_resource('pkg/mod1/__init__.py')
        self.assertEquals('import pkg.mod2\nfrom pkg.mod2 import AClass\n',
                          new_init.read())

class RefactoringUndoTest(unittest.TestCase):

    def setUp(self):
        super(RefactoringUndoTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.file = self.project.get_root_folder().create_file('file.txt')
        self.undo = Undo()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RefactoringUndoTest, self).tearDown()

    def test_simple_undo(self):
        change = ChangeFileContents(self.file, '1')
        change.do()
        self.assertEquals('1', self.file.read())
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('', self.file.read())

    def test_simple_redo(self):
        change = ChangeFileContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.undo.redo()
        self.assertEquals('1', self.file.read())

    def test_simple_re_undo(self):
        change = ChangeFileContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.undo.redo()
        self.undo.undo()
        self.assertEquals('', self.file.read())

    def test_multiple_undos(self):
        change = ChangeFileContents(self.file, '1')
        change.do()
        self.undo.add_change(change)
        change = ChangeFileContents(self.file, '2')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('1', self.file.read())
        change = ChangeFileContents(self.file, '3')
        change.do()
        self.undo.add_change(change)
        self.undo.undo()
        self.assertEquals('1', self.file.read())
        self.undo.redo()
        self.assertEquals('3', self.file.read())


class EncapsulateFieldTest(unittest.TestCase):

    def setUp(self):
        super(EncapsulateFieldTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        self.mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        self.a_class = 'class A(object):\n    def __init__(self):\n        self.attr = 1\n'
        self.setter_and_getter = '\n    def get_attr(self):\n        return self.attr\n\n' \
                                 '    def set_attr(self, value):\n        self.attr = value\n'

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(EncapsulateFieldTest, self).tearDown()

    def test_adding_getters_and_setters(self):
        code = 'class A(object):\n    def __init__(self):\n        self.attr = 1\n'
        self.mod.write(code)
        self.refactoring.encapsulate_field(self.mod, code.index('attr') + 1)
        expected = 'class A(object):\n    def __init__(self):\n        self.attr = 1\n\n' \
                   '    def get_attr(self):\n        return self.attr\n\n' \
                   '    def set_attr(self, value):\n        self.attr = value\n'
        self.assertEquals(expected, self.mod.read())

    def test_changing_getters_in_other_modules(self):
        self.mod1.write('import mod\na_var = mod.A()\nrange(a_var.attr)\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals('import mod\na_var = mod.A()\nrange(a_var.get_attr())\n',
                          self.mod1.read())

    # TODO: After ``0.3m5`` release
    def xxx_test_changing_setters_in_other_modules(self):
        self.mod1.write('import mod\na_var = mod.A()\na_var.attr = 1\n')
        self.mod.write(self.a_class)
        self.refactoring.encapsulate_field(self.mod, self.mod.read().index('attr') + 1)
        self.assertEquals('import mod\na_var = mod.A()\na_var.set_attr(1))\n',
                          self.mod1.read())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(ropetest.refactor.renametest.RenameRefactoringTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.extracttest.ExtractMethodTest))
    result.addTests(unittest.makeSuite(IntroduceFactoryTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.movetest.MoveRefactoringTest))
    result.addTests(unittest.makeSuite(RefactoringUndoTest))
    result.addTests(unittest.makeSuite(ropetest.refactor.inlinetest.InlineLocalVariableTest))
    result.addTests(unittest.makeSuite(EncapsulateFieldTest))
    return result



if __name__ == '__main__':
    unittest.main()
#    runner = unittest.TextTestRunner()
#    runner.run(suite())
