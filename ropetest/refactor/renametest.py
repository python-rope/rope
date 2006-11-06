import unittest
import rope.base.codeanalyze
import rope.refactor.rename
import rope.base.project
import ropetest


class RenameRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(RenameRefactoringTest, self).setUp()
        self.project_root = 'sample_project'
        ropetest.testutils.remove_recursively(self.project_root)
        self.project = rope.base.project.Project(self.project_root)
        self.pycore = self.project.get_pycore()
        self.refactoring = self.project.get_pycore().get_refactoring()

    def tearDown(self):
        ropetest.testutils.remove_recursively(self.project_root)
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
    
    def test_renaming_function_parameters_of_class_init(self):
        code = 'class A(object):\n    def __init__(self, a_param):\n        pass\n' \
               'a_var = A(a_param=1)\n'
        refactored = self.do_local_rename(code, code.index('a_param') + 1, 'new_param')
        expected = 'class A(object):\n    def __init__(self, new_param):\n        pass\n' \
                   'a_var = A(new_param=1)\n'
        self.assertEquals(expected, refactored)
    
    def test_renaming_functions_parameters_and_occurances_in_other_modules(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod1.write('def a_func(a_param):\n    print a_param\n')
        mod2.write('from mod1 import a_func\na_func(a_param=10)\n')
        self.refactoring.rename(mod1, mod1.read().index('a_param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n', mod1.read())
        self.assertEquals('from mod1 import a_func\na_func(new_param=10)\n', mod2.read())

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
    
    def test_renaming_class_attributes(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('class AClass(object):\n    def __init__(self):\n'
                   '        self.an_attr = 10\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\nanother_var = a_var.an_attr')
        
        self.refactoring.rename(mod1, mod1.read().index('an_attr'), 'attr')
        self.assertEquals('class AClass(object):\n    def __init__(self):\n'
                          '        self.attr = 10\n', mod1.read())
        self.assertEquals('import mod1\na_var = mod1.AClass()\nanother_var = a_var.attr',
                          mod2.read())
    
    def test_renaming_class_attributes2(self):
        mod1 = self.pycore.create_module(self.project.get_root_folder(), 'mod1')
        mod1.write('class AClass(object):\n    def __init__(self):\n'
                   '        an_attr = 10\n        self.an_attr = 10\n')
        mod2 = self.pycore.create_module(self.project.get_root_folder(), 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\nanother_var = a_var.an_attr')
        
        self.refactoring.rename(mod1, mod1.read().rindex('an_attr'), 'attr')
        self.assertEquals('class AClass(object):\n    def __init__(self):\n'
                          '        an_attr = 10\n        self.attr = 10\n', mod1.read())
        self.assertEquals('import mod1\na_var = mod1.AClass()\nanother_var = a_var.attr',
                          mod2.read())
    
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
    
    def test_renaming_parameters(self):
        code = 'def a_func(param):\n    print param\na_func(param=hey)\n'
        refactored = self.do_local_rename(code, code.find('param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n'
                          'a_func(new_param=hey)\n', refactored)
    
    def test_renaming_parameters_not_renaming_others(self):
        code = 'def a_func(param):\n    print param\nparam=10\na_func(param)\n'
        refactored = self.do_local_rename(code, code.find('param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n'
                          'param=10\na_func(param)\n', refactored)
    
    def test_renaming_parameters_not_renaming_others2(self):
        code = 'def a_func(param):\n    print param\nparam=10\na_func(param=param)'
        refactored = self.do_local_rename(code, code.find('param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n'
                          'param=10\na_func(new_param=param)', refactored)
    
    def test_renaming_parameters_with_multiple_params(self):
        code = 'def a_func(param1, param2):\n    print param1\na_func(param1=1, param2=2)\n'
        refactored = self.do_local_rename(code, code.find('param1') + 1, 'new_param')
        self.assertEquals('def a_func(new_param, param2):\n    print new_param\n'
                          'a_func(new_param=1, param2=2)\n', refactored)
    
    def test_renaming_parameters_with_multiple_params2(self):
        code = 'def a_func(param1, param2):\n    print param1\na_func(param1=1, param2=2)\n'
        refactored = self.do_local_rename(code, code.rfind('param2') + 1, 'new_param')
        self.assertEquals('def a_func(param1, new_param):\n    print param1\n'
                          'a_func(param1=1, new_param=2)\n', refactored)
    
    def test_renaming_parameters_on_calls(self):
        code = 'def a_func(param):\n    print param\na_func(param = hey)\n'
        refactored = self.do_local_rename(code, code.rfind('param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n'
                          'a_func(new_param = hey)\n', refactored)
    
    def test_renaming_parameters_spaces_before_call(self):
        code = 'def a_func(param):\n    print param\na_func  (param=hey)\n'
        refactored = self.do_local_rename(code, code.rfind('param') + 1, 'new_param')
        self.assertEquals('def a_func(new_param):\n    print new_param\n'
                          'a_func  (new_param=hey)\n', refactored)
    
    def test_renaming_variables_in_init_do_pys(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write('import pkg\nprint pkg.a_var\n')
        self.refactoring.rename(mod, mod.read().index('a_var') + 1, 'new_var')
        self.assertEquals('new_var = 10\n', init_dot_py.read())
        self.assertEquals('import pkg\nprint pkg.new_var\n', mod.read())
    
    def test_renaming_variables_in_init_do_pys2(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write('import pkg\nprint pkg.a_var\n')
        self.refactoring.rename(
            init_dot_py, init_dot_py.read().index('a_var') + 1, 'new_var')
        self.assertEquals('new_var = 10\n', init_dot_py.read())
        self.assertEquals('import pkg\nprint pkg.new_var\n', mod.read())
    
    def test_renaming_variables_in_init_do_pys3(self):
        pkg = self.pycore.create_package(self.project.get_root_folder(), 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = self.pycore.create_module(self.project.get_root_folder(), 'mod')
        mod.write('import pkg\nprint pkg.a_var\n')
        self.refactoring.rename(mod, mod.read().index('a_var') + 1, 'new_var')
        self.assertEquals('new_var = 10\n', init_dot_py.read())
        self.assertEquals('import pkg\nprint pkg.new_var\n', mod.read())
    

if __name__ == '__main__':
    unittest.main()
