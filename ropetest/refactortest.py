import unittest

import rope.codeanalyze
from rope.refactor import PythonRefactoring, RefactoringException
from rope.project import Project
from ropetest import testutils

class RefactoringTest(unittest.TestCase):

    def setUp(self):
        super(RefactoringTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RefactoringTest, self).tearDown()

    def test_simple_global_variable_renaming(self):
        refactored = self.refactoring.local_rename('a_var = 20\n', 2, 'new_var')
        self.assertEquals('new_var = 20\n', refactored)

    def test_variable_renaming_only_in_its_scope(self):
        refactored = self.refactoring.local_rename('a_var = 20\ndef a_func():\n    a_var = 10\n',
                                                   32, 'new_var')
        self.assertEquals('a_var = 20\ndef a_func():\n    new_var = 10\n', refactored)

    def test_not_renaming_dot_name(self):
        refactored = self.refactoring.local_rename("replace = True\n'aaa'.replace('a', 'b')\n", 1, 'new_var')
        self.assertEquals("new_var = True\n'aaa'.replace('a', 'b')\n", refactored)
    
    def test_renaming_multiple_names_in_the_same_line(self):
        refactored = self.refactoring.local_rename('a_var = 10\na_var = 10 + a_var / 2\n', 2, 'new_var')
        self.assertEquals('new_var = 10\nnew_var = 10 + new_var / 2\n', refactored)

    def test_renaming_names_when_getting_some_attribute(self):
        refactored = self.refactoring.local_rename("a_var = 'a b c'\na_var.split('\\n')\n", 2, 'new_var')
        self.assertEquals("new_var = 'a b c'\nnew_var.split('\\n')\n", refactored)

    def test_renaming_names_when_getting_some_attribute2(self):
        refactored = self.refactoring.local_rename("a_var = 'a b c'\na_var.split('\\n')\n", 20, 'new_var')
        self.assertEquals("new_var = 'a b c'\nnew_var.split('\\n')\n", refactored)

    def test_renaming_function_parameters1(self):
        refactored = self.refactoring.local_rename("def f(a_param):\n    print a_param\n", 8, 'new_param')
        self.assertEquals("def f(new_param):\n    print new_param\n", refactored)

    def test_renaming_function_parameters2(self):
        refactored = self.refactoring.local_rename("def f(a_param):\n    print a_param\n", 30, 'new_param')
        self.assertEquals("def f(new_param):\n    print new_param\n", refactored)

    def test_renaming_with_backslash_continued_names(self):
        refactored = self.refactoring.local_rename("replace = True\n'ali'.\\\nreplace\n", 2, 'is_replace')
        self.assertEquals("is_replace = True\n'ali'.\\\nreplace\n", refactored)

    def test_not_renaming_string_contents(self):
        refactored = self.refactoring.local_rename("a_var = 20\na_string='a_var'\n", 2, 'new_var')
        self.assertEquals("new_var = 20\na_string='a_var'\n", refactored)

    def test_not_renaming_comment_contents(self):
        refactored = self.refactoring.local_rename("a_var = 20\n# a_var\n", 2, 'new_var')
        self.assertEquals("new_var = 20\n# a_var\n", refactored)

    def test_renaming_all_occurances_in_containing_scope(self):
        code = 'if True:\n    a_var = 1\nelse:\n    a_var = 20\n'
        refactored = self.refactoring.local_rename(code, 16, 'new_var')
        self.assertEquals('if True:\n    new_var = 1\nelse:\n    new_var = 20\n',
                          refactored)
    
    def test_renaming_a_variable_with_arguement_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print a_var\n'
        refactored = self.refactoring.local_rename(code, 1, 'new_var')
        self.assertEquals('new_var = 10\ndef a_func(a_var):\n    print a_var\n',
                          refactored)
    
    def test_renaming_an_arguement_with_variable_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print a_var\n'
        refactored = self.refactoring.local_rename(code, len(code) - 3, 'new_var')
        self.assertEquals('a_var = 10\ndef a_func(new_var):\n    print new_var\n',
                          refactored)
    
    def test_renaming_function_with_local_variable_name(self):
        code = 'def a_func():\n    a_func=20\na_func()'
        refactored = self.refactoring.local_rename(code, len(code) - 3, 'new_func')
        self.assertEquals('def new_func():\n    a_func=20\nnew_func()',
                          refactored)
    
    def test_renaming_functions(self):
        code = 'def a_func():\n    pass\na_func()\n'
        refactored = self.refactoring.local_rename(code, len(code) - 5, 'new_func')
        self.assertEquals('def new_func():\n    pass\nnew_func()\n',
                          refactored)
    
    def test_renaming_functions_across_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('import mod1\nmod1.a_func()\n')
        self.refactoring.rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.assertEquals('def new_func():\n    pass\nnew_func()\n', mod1.read())
        self.assertEquals('import mod1\nmod1.new_func()\n', mod2.read())
        
    def test_renaming_functions_across_modules_from_import(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('from mod1 import a_func\na_func()\n')
        self.refactoring.rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.assertEquals('def new_func():\n    pass\nnew_func()\n', mod1.read())
        self.assertEquals('from mod1 import new_func\nnew_func()\n', mod2.read())
        
    def test_renaming_functions_from_another_module(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('import mod1\nmod1.a_func()\n')
        self.refactoring.rename(mod2, len(mod2.read()) - 5, 'new_func')
        self.assertEquals('def new_func():\n    pass\nnew_func()\n', mod1.read())
        self.assertEquals('import mod1\nmod1.new_func()\n', mod2.read())

    def test_applying_all_changes_together(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('import mod2\nmod2.a_func()\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('def a_func():\n    pass\na_func()\n')
        self.refactoring.rename(mod2, len(mod2.read()) - 5, 'new_func')
        self.assertEquals('import mod2\nmod2.new_func()\n', mod1.read())
        self.assertEquals('def new_func():\n    pass\nnew_func()\n', mod2.read())
    
    def test_renaming_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('from mod1 import a_func\n')
        self.refactoring.rename(mod2, 6, 'newmod')
        self.assertEquals('newmod.py', mod1.get_path())
        self.assertEquals('from newmod import a_func\n', mod2.read())

    def test_renaming_packages(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        mod1 = self.pycore.create_module(pkg, 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = self.pycore.create_module(pkg, 'mod2')
        mod2.write('from pkg.mod1 import a_func\n')
        self.refactoring.rename(mod2, 6, 'newpkg')
        self.assertEquals('newpkg/mod1.py', mod1.get_path())
        self.assertEquals('from newpkg.mod1 import a_func\n', mod2.read())

    def test_module_dependencies(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('class AClass(object):\n    pass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.pycore.resource_to_pyobject(mod2).get_attributes()['mod1']
        mod1.write('def AClass():\n    return 0\n')
        
        self.refactoring.rename(mod2, len(mod2.read()) - 3, 'a_func')
        self.assertEquals('def a_func():\n    return 0\n', mod1.read())
        self.assertEquals('import mod1\na_var = mod1.a_func()\n', mod2.read())
    
    # TODO: Renaming attributes in the whole hierarchy
    def xxx_test_renaming_attributes_in_subclasses(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n')

        self.refactoring.rename(mod, mod.read().rindex('a_method') + 1, 'new_method')
        self.assertEquals('class A(object):\n    def new_method(self):\n        pass\n'
                          'class B(A):\n    def new_method(self):\n        pass\n', mod.read())
    
    def test_undoing_refactorings(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        self.refactoring.rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.refactoring.undo_last_refactoring()
        self.assertEquals('def a_func():\n    pass\na_func()\n', mod1.read())
        
    def test_undoing_renaming_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('from mod1 import a_func\n')
        self.refactoring.rename(mod2, 6, 'newmod')
        self.refactoring.undo_last_refactoring()
        self.assertEquals('mod1.py', mod1.get_path())
        self.assertEquals('from mod1 import a_func\n', mod2.read())
    
    def _convert_line_range_to_offset(self, code, start, end):
        lines = rope.codeanalyze.SourceLinesAdapter(code)
        return lines.get_line_start(start), lines.get_line_end(end)
    
    def test_simple_extract_function(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.refactoring.extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_after_scope(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n\nprint 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.refactoring.extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n\nprint 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func(a_var)\n\n" \
                   "def new_func(a_var):\n    print a_var\n"
        self.assertEquals(expected, refactored)

    def test_not_unread_variables_as_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func()\n\n" \
                   "def new_func():\n    print 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_two_parameter(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    new_func(a_var, another_var)\n\n" \
                   "def new_func(a_var, another_var):\n    third_var = a_var + another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_return_value(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = new_func()\n    print a_var\n\n" \
                   "def new_func():\n    a_var = 10\n    return a_var\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_with_multiple_return_values(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var, another_var = new_func()\n" \
                   "    third_var = a_var + another_var\n\n" \
                   "def new_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    return a_var, another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_method(self):
        code = "class AClass(object):\n\n" \
               "    def a_func(self):\n        print 'one'\n        print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n\n" \
                   "    def a_func(self):\n        self.new_func()\n        print 'two'\n\n" \
                   "    def new_func(self):\n        print 'one'\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_args_and_returns(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        a_var = 10\n" \
               "        another_var = a_var * 3\n" \
               "        third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        a_var = 10\n" \
                   "        another_var = self.new_func(a_var)\n" \
                   "        third_var = a_var + another_var\n\n" \
                   "    def new_func(self, a_var):\n" \
                   "        another_var = a_var * 3\n" \
                   "        return another_var\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_self_as_argument(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        print self\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        self.new_func()\n\n" \
                   "    def new_func(self):\n" \
                   "        print self\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_with_multiple_methods(self):
        code = "class AClass(object):\n" \
               "    def a_func(self):\n" \
               "        print self\n\n" \
               "    def another_func(self):\n" \
               "        pass\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "class AClass(object):\n" \
                   "    def a_func(self):\n" \
                   "        self.new_func()\n\n" \
                   "    def new_func(self):\n" \
                   "        print self\n\n" \
                   "    def another_func(self):\n" \
                   "        pass\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_with_function_returns(self):
        code = "def a_func():\n    def inner_func():\n        pass\n    inner_func()\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    inner_func = new_func()\n    inner_func()\n\n" \
                   "def new_func():\n    def inner_func():\n        pass\n    return inner_func\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_global_function(self):
        code = "print 'one'\nprint 'two'\nprint 'three'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "print 'one'\n\ndef new_func():\n    print 'two'\n\nnew_func()\nprint 'three'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_while_inner_function_reads(self):
        code = "def a_func():\n    a_var = 10\n    " \
               "def inner_func():\n        print a_var\n    return inner_func\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n" \
                   "    inner_func = new_func(a_var)\n    return inner_func\n\n" \
                   "def new_func(a_var):\n    def inner_func():\n        print a_var\n" \
                   "    return inner_func\n"
        self.assertEquals(expected, refactored)

    def test_extract_method_bad_range(self):
        code = "def a_func():\n    pass\na_var = 10\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        try:
            self.refactoring.extract_method(code, start, end, 'new_func')
        except RefactoringException:
            pass
        else:
            self.fail('Should have thrown exception')

    def test_extract_method_bad_range2(self):
        code = "class AClass(object):\n    pass\n"
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        try:
            self.refactoring.extract_method(code, start, end, 'new_func')
        except RefactoringException:
            pass
        else:
            self.fail('Should have thrown exception')

    def test_extract_method_containing_return(self):
        code = "def a_func(arg):\n    return arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        try:
            self.refactoring.extract_method(code, start, end, 'new_func')
        except RefactoringException:
            pass
        else:
            self.fail('Should have thrown exception')

    def test_extract_function_and_argument_as_paramenter(self):
        code = "def a_func(arg):\n    print arg\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    new_func(arg)\n\n" \
                   "def new_func(arg):\n    print arg\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_and_indented_blocks(self):
        code = "def a_func(arg):\n    if True:\n        if True:\n            print arg\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.refactoring.extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    if True:\n        new_func(arg)\n\n" \
                   "def new_func(arg):\n    if True:\n        print arg\n"
        self.assertEquals(expected, refactored)
    
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
        self.refactoring.undo_last_refactoring()
        self.assertTrue(pkg.has_child('mod.py'))
        self.assertFalse(pkg.has_child('mod'))


if __name__ == '__main__':
    unittest.main()

