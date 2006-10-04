import unittest

import rope.codeanalyze
import rope.refactor.rename
from rope.refactor import PythonRefactoring, Undo
from rope.exceptions import RefactoringException
from rope.project import Project
from rope.refactor.change import *
from ropetest import testutils


class RenameRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(RenameRefactoringTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(RenameRefactoringTest, self).tearDown()
        
    def do_local_rename(self, source_code, offset, new_name):
        testmod = self.pycore.create_module(self.project.get_root_folder(), 'testmod')
        testmod.write(source_code)
        self.refactoring.local_rename(testmod, offset, new_name)
        return testmod.read()

    def test_simple_global_variable_renaming(self):
        refactored = self.do_local_rename('a_var = 20\n', 2, 'new_var')
        self.assertEquals('new_var = 20\n', refactored)

    def test_variable_renaming_only_in_its_scope(self):
        refactored = self.do_local_rename('a_var = 20\ndef a_func():\n    a_var = 10\n',
                                                   32, 'new_var')
        self.assertEquals('a_var = 20\ndef a_func():\n    new_var = 10\n', refactored)

    def test_not_renaming_dot_name(self):
        refactored = self.do_local_rename("replace = True\n'aaa'.replace('a', 'b')\n", 1, 'new_var')
        self.assertEquals("new_var = True\n'aaa'.replace('a', 'b')\n", refactored)
    
    def test_renaming_multiple_names_in_the_same_line(self):
        refactored = self.do_local_rename('a_var = 10\na_var = 10 + a_var / 2\n', 2, 'new_var')
        self.assertEquals('new_var = 10\nnew_var = 10 + new_var / 2\n', refactored)

    def test_renaming_names_when_getting_some_attribute(self):
        refactored = self.do_local_rename("a_var = 'a b c'\na_var.split('\\n')\n", 2, 'new_var')
        self.assertEquals("new_var = 'a b c'\nnew_var.split('\\n')\n", refactored)

    def test_renaming_names_when_getting_some_attribute2(self):
        refactored = self.do_local_rename("a_var = 'a b c'\na_var.split('\\n')\n", 20, 'new_var')
        self.assertEquals("new_var = 'a b c'\nnew_var.split('\\n')\n", refactored)

    def test_renaming_function_parameters1(self):
        refactored = self.do_local_rename("def f(a_param):\n    print a_param\n", 8, 'new_param')
        self.assertEquals("def f(new_param):\n    print new_param\n", refactored)

    def test_renaming_function_parameters2(self):
        refactored = self.do_local_rename("def f(a_param):\n    print a_param\n", 30, 'new_param')
        self.assertEquals("def f(new_param):\n    print new_param\n", refactored)

    def test_renaming_with_backslash_continued_names(self):
        refactored = self.do_local_rename("replace = True\n'ali'.\\\nreplace\n", 2, 'is_replace')
        self.assertEquals("is_replace = True\n'ali'.\\\nreplace\n", refactored)

    def test_not_renaming_string_contents(self):
        refactored = self.do_local_rename("a_var = 20\na_string='a_var'\n", 2, 'new_var')
        self.assertEquals("new_var = 20\na_string='a_var'\n", refactored)

    def test_not_renaming_comment_contents(self):
        refactored = self.do_local_rename("a_var = 20\n# a_var\n", 2, 'new_var')
        self.assertEquals("new_var = 20\n# a_var\n", refactored)

    def test_renaming_all_occurances_in_containing_scope(self):
        code = 'if True:\n    a_var = 1\nelse:\n    a_var = 20\n'
        refactored = self.do_local_rename(code, 16, 'new_var')
        self.assertEquals('if True:\n    new_var = 1\nelse:\n    new_var = 20\n',
                          refactored)
    
    def test_renaming_a_variable_with_arguement_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print a_var\n'
        refactored = self.do_local_rename(code, 1, 'new_var')
        self.assertEquals('new_var = 10\ndef a_func(a_var):\n    print a_var\n',
                          refactored)
    
    def test_renaming_an_arguement_with_variable_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print a_var\n'
        refactored = self.do_local_rename(code, len(code) - 3, 'new_var')
        self.assertEquals('a_var = 10\ndef a_func(new_var):\n    print new_var\n',
                          refactored)
    
    def test_renaming_function_with_local_variable_name(self):
        code = 'def a_func():\n    a_func=20\na_func()'
        refactored = self.do_local_rename(code, len(code) - 3, 'new_func')
        self.assertEquals('def new_func():\n    a_func=20\nnew_func()',
                          refactored)
    
    def test_renaming_functions(self):
        code = 'def a_func():\n    pass\na_func()\n'
        refactored = self.do_local_rename(code, len(code) - 5, 'new_func')
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
    
    def test_renaming_methods_in_subclasses(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n')

        self.refactoring.rename(mod, mod.read().rindex('a_method') + 1, 'new_method')
        self.assertEquals('class A(object):\n    def new_method(self):\n        pass\n'
                          'class B(A):\n    def new_method(self):\n        pass\n', mod.read())
    
    def test_renaming_methods_in_sibling_classes(self):
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n'
                  'class C(A):\n    def a_method(self):\n        pass\n')

        self.refactoring.rename(mod, mod.read().rindex('a_method') + 1, 'new_method')
        self.assertEquals('class A(object):\n    def new_method(self):\n        pass\n'
                  'class B(A):\n    def new_method(self):\n        pass\n'
                  'class C(A):\n    def new_method(self):\n        pass\n', mod.read())
    
    def test_undoing_refactorings(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        self.refactoring.rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.refactoring.undo()
        self.assertEquals('def a_func():\n    pass\na_func()\n', mod1.read())
        
    def test_undoing_renaming_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('from mod1 import a_func\n')
        self.refactoring.rename(mod2, 6, 'newmod')
        self.refactoring.undo()
        self.assertEquals('mod1.py', mod1.get_path())
        self.assertEquals('from mod1 import a_func\n', mod2.read())
    
    def test_rename_in_module_renaming_one_letter_names_for_expressions(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('a = 10\nprint (1+a)\n')
        pymod = self.pycore.get_module('mod1')
        old_pyname = pymod.get_attribute('a')
        rename_in_module = rope.refactor.rename.RenameInModule(
            self.pycore, [old_pyname], 'a', 'new_var', replace_primary=True)
        refactored = rename_in_module.get_changed_module(pymodule=pymod)
        self.assertEquals('new_var = 10\nprint (1+new_var)\n', refactored)
    
    def test_renaming_for_loop_variable(self):
        code = 'for var in range(10):\n    print var\n'
        refactored = self.do_local_rename(code, code.find('var') + 1, 'new_var')
        self.assertEquals('for new_var in range(10):\n    print new_var\n',
                          refactored)
    

class ExtractMethodTest(unittest.TestCase):

    def setUp(self):
        super(ExtractMethodTest, self).setUp()
        self.project_root = 'sample_project'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(ExtractMethodTest, self).tearDown()
        
    def do_extract_method(self, source_code, start, end, extracted):
        testmod = self.pycore.create_module(self.project.get_root_folder(), 'testmod')
        testmod.write(source_code)
        self.refactoring.extract_method(testmod, start, end, extracted)
        return testmod.read()

    def _convert_line_range_to_offset(self, code, start, end):
        lines = rope.codeanalyze.SourceLinesAdapter(code)
        return lines.get_line_start(start), lines.get_line_end(end)
    
    def test_simple_extract_function(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_after_scope(self):
        code = "def a_func():\n    print 'one'\n    print 'two'\n\nprint 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'extracted')
        expected = "def a_func():\n    extracted()\n    print 'two'\n\n" \
                   "def extracted():\n    print 'one'\n\nprint 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func(a_var)\n\n" \
                   "def new_func(a_var):\n    print a_var\n"
        self.assertEquals(expected, refactored)

    def test_not_unread_variables_as_parameter(self):
        code = "def a_func():\n    a_var = 10\n    print 'hey'\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    new_func()\n\n" \
                   "def new_func():\n    print 'hey'\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_two_parameter(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    new_func(a_var, another_var)\n\n" \
                   "def new_func(a_var, another_var):\n    third_var = a_var + another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_function_with_return_value(self):
        code = "def a_func():\n    a_var = 10\n    print a_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = new_func()\n    print a_var\n\n" \
                   "def new_func():\n    a_var = 10\n    return a_var\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_with_multiple_return_values(self):
        code = "def a_func():\n    a_var = 10\n    another_var = 20\n" \
               "    third_var = a_var + another_var\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var, another_var = new_func()\n" \
                   "    third_var = a_var + another_var\n\n" \
                   "def new_func():\n    a_var = 10\n    another_var = 20\n" \
                   "    return a_var, another_var\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_method(self):
        code = "class AClass(object):\n\n" \
               "    def a_func(self):\n        print 'one'\n        print 'two'\n"
        start, end = self._convert_line_range_to_offset(code, 4, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
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
        refactored = self.do_extract_method(code, start, end, 'new_func')
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
        refactored = self.do_extract_method(code, start, end, 'new_func')
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
        refactored = self.do_extract_method(code, start, end, 'new_func')
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
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    inner_func = new_func()\n    inner_func()\n\n" \
                   "def new_func():\n    def inner_func():\n        pass\n    return inner_func\n"
        self.assertEquals(expected, refactored)

    def test_simple_extract_global_function(self):
        code = "print 'one'\nprint 'two'\nprint 'three'\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "print 'one'\n\ndef new_func():\n    print 'two'\n\nnew_func()\nprint 'three'\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_while_inner_function_reads(self):
        code = "def a_func():\n    a_var = 10\n    " \
               "def inner_func():\n        print a_var\n    return inner_func\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func():\n    a_var = 10\n" \
                   "    inner_func = new_func(a_var)\n    return inner_func\n\n" \
                   "def new_func(a_var):\n    def inner_func():\n        print a_var\n" \
                   "    return inner_func\n"
        self.assertEquals(expected, refactored)

    @testutils.assert_raises(RefactoringException)
    def test_extract_method_bad_range(self):
        code = "def a_func():\n    pass\na_var = 10\n"
        start, end = self._convert_line_range_to_offset(code, 2, 3)
        self.do_extract_method(code, start, end, 'new_func')

    @testutils.assert_raises(RefactoringException)
    def test_extract_method_bad_range2(self):
        code = "class AClass(object):\n    pass\n"
        start, end = self._convert_line_range_to_offset(code, 1, 1)
        self.do_extract_method(code, start, end, 'new_func')

    @testutils.assert_raises(RefactoringException)
    def test_extract_method_containing_return(self):
        code = "def a_func(arg):\n    return arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        self.do_extract_method(code, start, end, 'new_func')

    @testutils.assert_raises(RefactoringException)
    def test_extract_method_containing_yield(self):
        code = "def a_func(arg):\n    yield arg * 2\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        self.do_extract_method(code, start, end, 'new_func')

    def test_extract_function_and_argument_as_paramenter(self):
        code = "def a_func(arg):\n    print arg\n"
        start, end = self._convert_line_range_to_offset(code, 2, 2)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    new_func(arg)\n\n" \
                   "def new_func(arg):\n    print arg\n"
        self.assertEquals(expected, refactored)

    def test_extract_function_and_indented_blocks(self):
        code = "def a_func(arg):\n    if True:\n        if True:\n            print arg\n"
        start, end = self._convert_line_range_to_offset(code, 3, 4)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(arg):\n    if True:\n        new_func(arg)\n\n" \
                   "def new_func(arg):\n    if True:\n        print arg\n"
        self.assertEquals(expected, refactored)
    
    def test_extract_method_and_multi_line_headers(self):
        code = "def a_func(\n           arg):\n    print arg\n"
        start, end = self._convert_line_range_to_offset(code, 3, 3)
        refactored = self.do_extract_method(code, start, end, 'new_func')
        expected = "def a_func(\n           arg):\n    new_func(arg)\n\n" \
                   "def new_func(arg):\n    print arg\n"
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


class MoveRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(MoveRefactoringTest, self).setUp()
        self.project_root = 'sampleproject'
        testutils.remove_recursively(self.project_root)
        self.project = Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()
        self.mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        self.mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        self.mod3 = self.pycore.create_module(self.project.get_root_folder(), 'mod3')
        self.pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        self.mod4 = self.pycore.create_module(self.pkg, 'mod4')
        self.mod5 = self.pycore.create_module(self.pkg, 'mod5')
    
    def tearDown(self):
        testutils.remove_recursively(self.project_root)
        super(MoveRefactoringTest, self).tearDown()
    
    def test_simple_moving(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('', self.mod1.read())
        self.assertEquals('class AClass(object):\n    pass\n',
                          self.mod2.read())
    
    def test_changing_other_modules_adding_normal_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod3.write('import mod1\na_var = mod1.AClass()\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('import mod1\nimport mod2\na_var = mod2.AClass()\n',
                          self.mod3.read())

    def test_changing_other_modules_removing_from_imports(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod3.write('from mod1 import AClass\na_var = AClass()\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('import mod2\na_var = mod2.AClass()\n',
                          self.mod3.read())
    
    def test_changing_source_module(self):
        self.mod1.write('class AClass(object):\n    pass\na_var = AClass()\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('import mod2\na_var = mod2.AClass()\n',
                          self.mod1.read())
    
    def test_changing_destination_module(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.mod2.write('from mod1 import AClass\na_var = AClass()\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)
        self.assertEquals('class AClass(object):\n    pass\na_var = AClass()\n',
                          self.mod2.read())

    @testutils.assert_raises(RefactoringException)
    def test_folder_destination(self):
        self.mod1.write('class AClass(object):\n    pass\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1, self.pkg)
    
    @testutils.assert_raises(RefactoringException)
    def test_raising_exception_for_moving_non_global_elements(self):
        self.mod1.write('def a_func():\n    class AClass(object):\n        pass\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('AClass') + 1,
                              self.mod2)

    def test_moving_used_imports_to_destination_module(self):
        self.mod3.write('a_var = 10')
        self.mod1.write('import mod3\nfrom mod3 import a_var\n' \
                        'def a_func():\n    print mod3, a_var\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('a_func') + 1,
                              self.mod2)
        self.assertEquals('import mod3\n\n\n' \
                          'def a_func():\n    print mod3, mod3.a_var\n',
                          self.mod2.read())

    def test_moving_used_names_to_destination_module(self):
        self.mod1.write('a_var = 10\n' \
                        'def a_func():\n    print a_var\n')
        self.refactoring.move(self.mod1, self.mod1.read().index('a_func') + 1,
                              self.mod2)
        self.assertEquals('a_var = 10\n', self.mod1.read())
        self.assertEquals('import mod1\n\n\ndef a_func():\n    print mod1.a_var\n',
                          self.mod2.read())

    def test_moving_and_used_relative_imports(self):
        self.mod4.write('import mod5\n' \
                        'def a_func():\n    print mod5\n')
        self.refactoring.move(self.mod4, self.mod4.read().index('a_func') + 1,
                              self.mod1)
        self.assertEquals('import pkg.mod5\n\n\ndef a_func():\n    print pkg.mod5\n',
                          self.mod1.read())
    
    def test_moving_modules(self):
        self.mod2.write('import mod1\nprint mod1')
        self.refactoring.move(self.mod2, self.mod2.read().index('mod1') + 1, self.pkg)
        self.assertEquals('import pkg.mod1\nprint pkg.mod1', self.mod2.read())
        self.assertEquals('pkg/mod1.py', self.mod1.get_path())
        
    def test_moving_modules_and_removing_out_of_date_imports(self):
        self.mod2.write('import pkg.mod4\nprint pkg.mod4')
        self.refactoring.move(self.mod2, self.mod2.read().index('mod4') + 1,
                              self.project.get_root_folder())
        self.assertEquals('import mod4\nprint mod4', self.mod2.read())
        self.assertEquals('mod4.py', self.mod4.get_path())
    
    def test_moving_modules_and_removing_out_of_date_froms(self):
        self.mod2.write('from pkg import mod4\nprint mod4')
        self.refactoring.move(self.mod2, self.mod2.read().index('mod4') + 1,
                              self.project.get_root_folder())
        self.assertEquals('import mod4\nprint mod4', self.mod2.read())
        self.assertEquals('mod4.py', self.mod4.get_path())
    
    # TODO: removing out of date froms
    def xxx_test_moving_modules_and_removing_out_of_date_froms2(self):
        self.mod4.write('a_var = 10')
        self.mod2.write('from pkg.mod4 import a_var\nprint a_var\n')
        self.refactoring.move(self.mod2, self.mod2.read().index('mod4') + 1,
                              self.project.get_root_folder())
        self.assertEquals('import mod4\nprint mod4.a_var\n', self.mod2.read())
    
    def test_moving_modules_and_relative_import(self):
        self.mod4.write('import mod5\nprint mod5\n')
        self.mod2.write('import pkg.mod4\nprint pkg.mod4')
        self.refactoring.move(self.mod2, self.mod2.read().index('mod4') + 1,
                              self.project.get_root_folder())
        self.assertEquals('import pkg.mod5\nprint pkg.mod5\n', self.mod4.read())


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


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(RenameRefactoringTest))
    result.addTests(unittest.makeSuite(ExtractMethodTest))
    result.addTests(unittest.makeSuite(IntroduceFactoryTest))
    result.addTests(unittest.makeSuite(MoveRefactoringTest))
    result.addTests(unittest.makeSuite(RefactoringUndoTest))
    return result


if __name__ == '__main__':
    unittest.main()

