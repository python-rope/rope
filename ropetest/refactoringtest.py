import unittest

from rope.refactoring import PythonRefactoring
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


if __name__ == '__main__':
    unittest.main()

