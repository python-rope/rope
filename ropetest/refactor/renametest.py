import sys
from textwrap import dedent
try:
    import unittest2 as unittest
except ImportError:
    import unittest

import rope.base.codeanalyze
import rope.refactor.occurrences
from rope.refactor import rename
from rope.refactor.rename import Rename
from ropetest import testutils


class RenameRefactoringTest(unittest.TestCase):

    def setUp(self):
        super(RenameRefactoringTest, self).setUp()
        self.project = testutils.sample_project()

    def tearDown(self):
        testutils.remove_project(self.project)
        super(RenameRefactoringTest, self).tearDown()

    def _local_rename(self, source_code, offset, new_name):
        testmod = testutils.create_module(self.project, 'testmod')
        testmod.write(source_code)
        changes = Rename(self.project, testmod, offset).\
            get_changes(new_name, resources=[testmod])
        self.project.do(changes)
        return testmod.read()

    def _rename(self, resource, offset, new_name, **kwds):
        changes = Rename(self.project, resource, offset).\
            get_changes(new_name, **kwds)
        self.project.do(changes)

    def test_simple_global_variable_renaming(self):
        refactored = self._local_rename('a_var = 20\n', 2, 'new_var')
        self.assertEqual('new_var = 20\n', refactored)

    def test_variable_renaming_only_in_its_scope(self):
        refactored = self._local_rename(
            'a_var = 20\ndef a_func():\n    a_var = 10\n', 32, 'new_var')
        self.assertEqual('a_var = 20\ndef a_func():\n    new_var = 10\n',
                          refactored)

    def test_not_renaming_dot_name(self):
        refactored = self._local_rename(
            "replace = True\n'aaa'.replace('a', 'b')\n", 1, 'new_var')
        self.assertEqual("new_var = True\n'aaa'.replace('a', 'b')\n",
                          refactored)

    def test_renaming_multiple_names_in_the_same_line(self):
        refactored = self._local_rename(
            'a_var = 10\na_var = 10 + a_var / 2\n', 2, 'new_var')
        self.assertEqual('new_var = 10\nnew_var = 10 + new_var / 2\n',
                          refactored)

    def test_renaming_names_when_getting_some_attribute(self):
        refactored = self._local_rename(
            "a_var = 'a b c'\na_var.split('\\n')\n", 2, 'new_var')
        self.assertEqual("new_var = 'a b c'\nnew_var.split('\\n')\n",
                          refactored)

    def test_renaming_names_when_getting_some_attribute2(self):
        refactored = self._local_rename(
            "a_var = 'a b c'\na_var.split('\\n')\n", 20, 'new_var')
        self.assertEqual("new_var = 'a b c'\nnew_var.split('\\n')\n",
                          refactored)

    def test_renaming_function_parameters1(self):
        refactored = self._local_rename(
            "def f(a_param):\n    print(a_param)\n", 8, 'new_param')
        self.assertEqual("def f(new_param):\n    print(new_param)\n",
                          refactored)

    def test_renaming_function_parameters2(self):
        refactored = self._local_rename(
            "def f(a_param):\n    print(a_param)\n", 30, 'new_param')
        self.assertEqual("def f(new_param):\n    print(new_param)\n",
                          refactored)

    def test_renaming_occurrences_inside_functions(self):
        code = 'def a_func(p1):\n    a = p1\na_func(1)\n'
        refactored = self._local_rename(code, code.index('p1') + 1,
                                        'new_param')
        self.assertEqual(
            'def a_func(new_param):\n    a = new_param\na_func(1)\n',
            refactored)

    def test_renaming_comprehension_loop_variables(self):
        code = '[b_var for b_var, c_var in d_var if b_var == c_var]'
        refactored = self._local_rename(code, code.index('b_var') + 1,
                                        'new_var')
        self.assertEqual(
            '[new_var for new_var, c_var in d_var if new_var == c_var]',
            refactored)

    def test_renaming_list_comprehension_loop_variables_in_assignment(self):
        code = 'a_var = [b_var for b_var, c_var in d_var if b_var == c_var]'
        refactored = self._local_rename(code, code.index('b_var') + 1,
                                        'new_var')
        self.assertEqual(
            'a_var = [new_var for new_var, c_var in d_var if new_var == c_var]',
            refactored)

    def test_renaming_generator_comprehension_loop_variables(self):
        code = 'a_var = (b_var for b_var, c_var in d_var if b_var == c_var)'
        refactored = self._local_rename(code, code.index('b_var') + 1,
                                        'new_var')
        self.assertEqual(
            'a_var = (new_var for new_var, c_var in d_var if new_var == c_var)',
            refactored)

    @unittest.expectedFailure
    def test_renaming_comprehension_loop_variables_scope(self):
        # FIXME: variable scoping for comprehensions is incorrect, we currently
        #        don't create a scope for comprehension
        code = dedent('''\
            [b_var for b_var, c_var in d_var if b_var == c_var]
            b_var = 10
        ''')
        refactored = self._local_rename(code, code.index('b_var') + 1,
                                        'new_var')
        self.assertEqual(
            '[new_var for new_var, c_var in d_var if new_var == c_var]\nb_var = 10\n',
            refactored)

    @testutils.only_for_versions_higher('3.8')
    def test_renaming_inline_assignment(self):
        code = dedent('''\
            while a_var := next(foo):
                print(a_var)
        ''')
        refactored = self._local_rename(code, code.index('a_var') + 1,
                                        'new_var')
        self.assertEqual(
            dedent('''\
                while new_var := next(foo):
                    print(new_var)
            '''),
            refactored,
        )

    def test_renaming_arguments_for_normal_args_changing_calls(self):
        code = 'def a_func(p1=None, p2=None):\n    pass\na_func(p2=1)\n'
        refactored = self._local_rename(code, code.index('p2') + 1, 'p3')
        self.assertEqual(
            'def a_func(p1=None, p3=None):\n    pass\na_func(p3=1)\n',
            refactored)

    def test_renaming_function_parameters_of_class_init(self):
        code = 'class A(object):\n    def __init__(self, a_param):' \
               '\n        pass\n' \
               'a_var = A(a_param=1)\n'
        refactored = self._local_rename(code, code.index('a_param') + 1,
                                        'new_param')
        expected = 'class A(object):\n    ' \
            'def __init__(self, new_param):\n        pass\n' \
            'a_var = A(new_param=1)\n'
        self.assertEqual(expected, refactored)

    def test_rename_functions_parameters_and_occurences_in_other_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('def a_func(a_param):\n    print(a_param)\n')
        mod2.write('from mod1 import a_func\na_func(a_param=10)\n')
        self._rename(mod1, mod1.read().index('a_param') + 1, 'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n',
                          mod1.read())
        self.assertEqual('from mod1 import a_func\na_func(new_param=10)\n',
                          mod2.read())

    def test_renaming_with_backslash_continued_names(self):
        refactored = self._local_rename(
            "replace = True\n'ali'.\\\nreplace\n", 2, 'is_replace')
        self.assertEqual("is_replace = True\n'ali'.\\\nreplace\n",
                          refactored)

    @testutils.only_for('3.6')
    def test_renaming_occurrence_in_f_string(self):
        refactored = self._local_rename(
            "a_var = 20\na_string=f'value: {a_var}'\n", 2, 'new_var')
        self.assertEqual("new_var = 20\na_string=f'value: {new_var}'\n",
                          refactored)

    @testutils.only_for('3.6')
    def test_renaming_occurrence_in_nested_f_string(self):
        refactored = self._local_rename(
            "a_var = 20\na_string=f'{f\"{a_var}\"}'\n", 2, 'new_var')
        self.assertEqual(
            "new_var = 20\na_string=f'{f\"{new_var}\"}'\n",
            refactored)

    @testutils.only_for('3.6')
    def test_not_renaming_string_contents_in_f_string(self):
        refactored = self._local_rename(
            "a_var = 20\na_string=f'{\"a_var\"}'\n", 2, 'new_var')
        self.assertEqual("new_var = 20\na_string=f'{\"a_var\"}'\n",
                          refactored)

    def test_not_renaming_string_contents(self):
        refactored = self._local_rename("a_var = 20\na_string='a_var'\n",
                                        2, 'new_var')
        self.assertEqual("new_var = 20\na_string='a_var'\n",
                          refactored)

    def test_not_renaming_comment_contents(self):
        refactored = self._local_rename("a_var = 20\n# a_var\n",
                                        2, 'new_var')
        self.assertEqual("new_var = 20\n# a_var\n", refactored)

    def test_renaming_all_occurances_in_containing_scope(self):
        code = 'if True:\n    a_var = 1\nelse:\n    a_var = 20\n'
        refactored = self._local_rename(code, 16, 'new_var')
        self.assertEqual(
            'if True:\n    new_var = 1\nelse:\n    new_var = 20\n', refactored)

    def test_renaming_a_variable_with_arguement_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print(a_var)\n'
        refactored = self._local_rename(code, 1, 'new_var')
        self.assertEqual(
            'new_var = 10\ndef a_func(a_var):\n    print(a_var)\n', refactored)

    def test_renaming_an_arguement_with_variable_name(self):
        code = 'a_var = 10\ndef a_func(a_var):\n    print(a_var)\n'
        refactored = self._local_rename(code, len(code) - 3, 'new_var')
        self.assertEqual(
            'a_var = 10\ndef a_func(new_var):\n    print(new_var)\n',
            refactored)

    def test_renaming_function_with_local_variable_name(self):
        code = 'def a_func():\n    a_func=20\na_func()'
        refactored = self._local_rename(code, len(code) - 3, 'new_func')
        self.assertEqual('def new_func():\n    a_func=20\nnew_func()',
                          refactored)

    def test_renaming_functions(self):
        code = 'def a_func():\n    pass\na_func()\n'
        refactored = self._local_rename(code, len(code) - 5, 'new_func')
        self.assertEqual('def new_func():\n    pass\nnew_func()\n',
                          refactored)

    @testutils.only_for('3.5')
    def test_renaming_async_function(self):
        code = 'async def a_func():\n    pass\na_func()'
        refactored = self._local_rename(code, len(code) - 5, 'new_func')
        self.assertEqual('async def new_func():\n    pass\nnew_func()',
                          refactored)

    @testutils.only_for('3.5')
    def test_renaming_await(self):
        code = 'async def b_func():\n    pass\nasync def a_func():\n    await b_func()'
        refactored = self._local_rename(code, len(code) - 5, 'new_func')
        self.assertEqual('async def new_func():\n    pass\nasync def a_func():\n    await new_func()',
                          refactored)


    def test_renaming_functions_across_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1\nmod1.a_func()\n')
        self._rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.assertEqual('def new_func():\n    pass\nnew_func()\n',
                          mod1.read())
        self.assertEqual('import mod1\nmod1.new_func()\n', mod2.read())

    def test_renaming_functions_across_modules_from_import(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('from mod1 import a_func\na_func()\n')
        self._rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.assertEqual('def new_func():\n    pass\nnew_func()\n',
                          mod1.read())
        self.assertEqual('from mod1 import new_func\nnew_func()\n',
                          mod2.read())

    def test_renaming_functions_from_another_module(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1\nmod1.a_func()\n')
        self._rename(mod2, len(mod2.read()) - 5, 'new_func')
        self.assertEqual('def new_func():\n    pass\nnew_func()\n',
                          mod1.read())
        self.assertEqual('import mod1\nmod1.new_func()\n', mod2.read())

    def test_applying_all_changes_together(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('import mod2\nmod2.a_func()\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('def a_func():\n    pass\na_func()\n')
        self._rename(mod2, len(mod2.read()) - 5, 'new_func')
        self.assertEqual('import mod2\nmod2.new_func()\n', mod1.read())
        self.assertEqual('def new_func():\n    pass\nnew_func()\n',
                          mod2.read())

    def test_renaming_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('from mod1 import a_func\n')
        self._rename(mod2, mod2.read().index('mod1') + 1, 'newmod')
        self.assertTrue(not mod1.exists() and
                        self.project.find_module('newmod') is not None)
        self.assertEqual('from newmod import a_func\n', mod2.read())

    def test_renaming_modules_aliased(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1 as m\nm.a_func()\n')
        self._rename(mod1, None, 'newmod')
        self.assertTrue(not mod1.exists() and
                        self.project.find_module('newmod') is not None)
        self.assertEqual('import newmod as m\nm.a_func()\n', mod2.read())

    def test_renaming_packages(self):
        pkg = testutils.create_package(self.project, 'pkg')
        mod1 = testutils.create_module(self.project, 'mod1', pkg)
        mod1.write('def a_func():\n    pass\n')
        mod2 = testutils.create_module(self.project, 'mod2', pkg)
        mod2.write('from pkg.mod1 import a_func\n')
        self._rename(mod2, 6, 'newpkg')
        self.assertTrue(self.project.find_module('newpkg.mod1') is not None)
        new_mod2 = self.project.find_module('newpkg.mod2')
        self.assertEqual('from newpkg.mod1 import a_func\n', new_mod2.read())

    def test_module_dependencies(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('class AClass(object):\n    pass\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\n')
        self.project.get_pymodule(mod2).get_attributes()['mod1']
        mod1.write('def AClass():\n    return 0\n')

        self._rename(mod2, len(mod2.read()) - 3, 'a_func')
        self.assertEqual('def a_func():\n    return 0\n', mod1.read())
        self.assertEqual('import mod1\na_var = mod1.a_func()\n', mod2.read())

    def test_renaming_class_attributes(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('class AClass(object):\n    def __init__(self):\n'
                   '        self.an_attr = 10\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\n'
                   'another_var = a_var.an_attr')

        self._rename(mod1, mod1.read().index('an_attr'), 'attr')
        self.assertEqual('class AClass(object):\n    def __init__(self):\n'
                          '        self.attr = 10\n', mod1.read())
        self.assertEqual(
            'import mod1\na_var = mod1.AClass()\nanother_var = a_var.attr',
            mod2.read())

    def test_renaming_class_attributes2(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('class AClass(object):\n    def __init__(self):\n'
                   '        an_attr = 10\n        self.an_attr = 10\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('import mod1\na_var = mod1.AClass()\n'
                   'another_var = a_var.an_attr')

        self._rename(mod1, mod1.read().rindex('an_attr'), 'attr')
        self.assertEqual(
            'class AClass(object):\n    def __init__(self):\n'
            '        an_attr = 10\n        self.attr = 10\n', mod1.read())
        self.assertEqual(
            'import mod1\na_var = mod1.AClass()\nanother_var = a_var.attr',
            mod2.read())

    def test_renaming_methods_in_subclasses(self):
        mod = testutils.create_module(self.project, 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n')

        self._rename(mod, mod.read().rindex('a_method') + 1, 'new_method',
                     in_hierarchy=True)
        self.assertEqual(
            'class A(object):\n    def new_method(self):\n        pass\n'
            'class B(A):\n    def new_method(self):\n        pass\n',
            mod.read())

    def test_renaming_methods_in_sibling_classes(self):
        mod = testutils.create_module(self.project, 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n'
                  'class C(A):\n    def a_method(self):\n        pass\n')

        self._rename(mod, mod.read().rindex('a_method') + 1, 'new_method',
                     in_hierarchy=True)
        self.assertEqual(
            'class A(object):\n    def new_method(self):\n        pass\n'
            'class B(A):\n    def new_method(self):\n        pass\n'
            'class C(A):\n    def new_method(self):\n        pass\n',
            mod.read())

    def test_not_renaming_methods_in_hierarchies(self):
        mod = testutils.create_module(self.project, 'mod1')
        mod.write('class A(object):\n    def a_method(self):\n        pass\n'
                  'class B(A):\n    def a_method(self):\n        pass\n')

        self._rename(mod, mod.read().rindex('a_method') + 1, 'new_method',
                     in_hierarchy=False)
        self.assertEqual(
            'class A(object):\n    def a_method(self):\n        pass\n'
            'class B(A):\n    def new_method(self):\n        pass\n',
            mod.read())

    def test_undoing_refactorings(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\na_func()\n')
        self._rename(mod1, len(mod1.read()) - 5, 'new_func')
        self.project.history.undo()
        self.assertEqual('def a_func():\n    pass\na_func()\n', mod1.read())

    def test_undoing_renaming_modules(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('def a_func():\n    pass\n')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod2.write('from mod1 import a_func\n')
        self._rename(mod2, 6, 'newmod')
        self.project.history.undo()
        self.assertEqual('mod1.py', mod1.path)
        self.assertEqual('from mod1 import a_func\n', mod2.read())

    def test_rename_in_module_renaming_one_letter_names_for_expressions(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write('a = 10\nprint(1+a)\n')
        pymod = self.project.get_module('mod1')
        old_pyname = pymod['a']
        finder = rope.refactor.occurrences.create_finder(
            self.project, 'a', old_pyname)
        refactored = rename.rename_in_module(
            finder, 'new_var', pymodule=pymod, replace_primary=True)
        self.assertEqual('new_var = 10\nprint(1+new_var)\n', refactored)

    def test_renaming_for_loop_variable(self):
        code = 'for var in range(10):\n    print(var)\n'
        refactored = self._local_rename(code, code.find('var') + 1, 'new_var')
        self.assertEqual('for new_var in range(10):\n    print(new_var)\n',
                          refactored)

    @testutils.only_for('3.5')
    def test_renaming_async_for_loop_variable(self):
        code = 'async def func():\n    async for var in range(10):\n        print(var)\n'
        refactored = self._local_rename(code, code.find('var') + 1, 'new_var')
        self.assertEqual('async def func():\n    async for new_var in range(10):\n        print(new_var)\n',
                          refactored)

    @testutils.only_for('3.5')
    def test_renaming_async_with_context_manager(self):
        code = 'def a_cm(): pass\n'\
               'async def a_func():\n    async with a_cm() as x: pass'
        refactored = self._local_rename(code, code.find('a_cm') + 1, 'another_cm')
        expected = 'def another_cm(): pass\n'\
                   'async def a_func():\n    async with another_cm() as x: pass'
        self.assertEqual(refactored, expected)

    @testutils.only_for('3.5')
    def test_renaming_async_with_as_variable(self):
        code = 'async def func():\n    async with a_func() as var:\n        print(var)\n'
        refactored = self._local_rename(code, code.find('var') + 1, 'new_var')
        self.assertEqual('async def func():\n    async with a_func() as new_var:\n        print(new_var)\n',
                          refactored)

    def test_renaming_parameters(self):
        code = 'def a_func(param):\n    print(param)\na_func(param=hey)\n'
        refactored = self._local_rename(code, code.find('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'a_func(new_param=hey)\n', refactored)

    def test_renaming_assigned_parameters(self):
        code = 'def f(p):\n    p = p + 1\n    return p\nf(p=1)\n'
        refactored = self._local_rename(code, code.find('p'), 'arg')
        self.assertEqual('def f(arg):\n    arg = arg + 1\n'
                          '    return arg\nf(arg=1)\n', refactored)

    def test_renaming_parameters_not_renaming_others(self):
        code = 'def a_func(param):' \
            '\n    print(param)\nparam=10\na_func(param)\n'
        refactored = self._local_rename(code, code.find('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'param=10\na_func(param)\n', refactored)

    def test_renaming_parameters_not_renaming_others2(self):
        code = 'def a_func(param):\n    print(param)\n' \
            'param=10\na_func(param=param)'
        refactored = self._local_rename(code, code.find('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'param=10\na_func(new_param=param)', refactored)

    def test_renaming_parameters_with_multiple_params(self):
        code = 'def a_func(param1, param2):\n    print(param1)\n'\
               'a_func(param1=1, param2=2)\n'
        refactored = self._local_rename(code, code.find('param1') + 1,
                                        'new_param')
        self.assertEqual(
            'def a_func(new_param, param2):\n    print(new_param)\n'
            'a_func(new_param=1, param2=2)\n', refactored)

    def test_renaming_parameters_with_multiple_params2(self):
        code = 'def a_func(param1, param2):\n    print(param1)\n' \
               'a_func(param1=1, param2=2)\n'
        refactored = self._local_rename(code, code.rfind('param2') + 1,
                                        'new_param')
        self.assertEqual('def a_func(param1, new_param):\n    print(param1)\n'
                          'a_func(param1=1, new_param=2)\n', refactored)

    def test_renaming_parameters_on_calls(self):
        code = 'def a_func(param):\n    print(param)\na_func(param = hey)\n'
        refactored = self._local_rename(code, code.rfind('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'a_func(new_param = hey)\n', refactored)

    def test_renaming_parameters_spaces_before_call(self):
        code = 'def a_func(param):\n    print(param)\na_func  (param=hey)\n'
        refactored = self._local_rename(code, code.rfind('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'a_func  (new_param=hey)\n', refactored)

    def test_renaming_parameter_like_objects_after_keywords(self):
        code = 'def a_func(param):\n    print(param)\ndict(param=hey)\n'
        refactored = self._local_rename(code, code.find('param') + 1,
                                        'new_param')
        self.assertEqual('def a_func(new_param):\n    print(new_param)\n'
                          'dict(param=hey)\n', refactored)

    def test_renaming_variables_in_init_dot_pys(self):
        pkg = testutils.create_package(self.project, 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = testutils.create_module(self.project, 'mod')
        mod.write('import pkg\nprint(pkg.a_var)\n')
        self._rename(mod, mod.read().index('a_var') + 1, 'new_var')
        self.assertEqual('new_var = 10\n', init_dot_py.read())
        self.assertEqual('import pkg\nprint(pkg.new_var)\n', mod.read())

    def test_renaming_variables_in_init_dot_pys2(self):
        pkg = testutils.create_package(self.project, 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = testutils.create_module(self.project, 'mod')
        mod.write('import pkg\nprint(pkg.a_var)\n')
        self._rename(init_dot_py,
                     init_dot_py.read().index('a_var') + 1, 'new_var')
        self.assertEqual('new_var = 10\n', init_dot_py.read())
        self.assertEqual('import pkg\nprint(pkg.new_var)\n', mod.read())

    def test_renaming_variables_in_init_dot_pys3(self):
        pkg = testutils.create_package(self.project, 'pkg')
        init_dot_py = pkg.get_child('__init__.py')
        init_dot_py.write('a_var = 10\n')
        mod = testutils.create_module(self.project, 'mod')
        mod.write('import pkg\nprint(pkg.a_var)\n')
        self._rename(mod, mod.read().index('a_var') + 1, 'new_var')
        self.assertEqual('new_var = 10\n', init_dot_py.read())
        self.assertEqual('import pkg\nprint(pkg.new_var)\n', mod.read())

    def test_renaming_resources_using_rename_module_refactoring(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('a_var = 1')
        mod2.write('import mod1\nmy_var = mod1.a_var\n')
        renamer = rename.Rename(self.project, mod1)
        renamer.get_changes('newmod').do()
        self.assertEqual('import newmod\nmy_var = newmod.a_var\n',
                          mod2.read())

    def test_renam_resources_using_rename_module_refactor_for_packages(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        pkg = testutils.create_package(self.project, 'pkg')
        mod1.write('import pkg\nmy_pkg = pkg')
        renamer = rename.Rename(self.project, pkg)
        renamer.get_changes('newpkg').do()
        self.assertEqual('import newpkg\nmy_pkg = newpkg', mod1.read())

    def test_renam_resources_use_rename_module_refactor_for_init_dot_py(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        pkg = testutils.create_package(self.project, 'pkg')
        mod1.write('import pkg\nmy_pkg = pkg')
        renamer = rename.Rename(self.project, pkg.get_child('__init__.py'))
        renamer.get_changes('newpkg').do()
        self.assertEqual('import newpkg\nmy_pkg = newpkg', mod1.read())

    def test_renaming_global_variables(self):
        code = 'a_var = 1\ndef a_func():\n    global a_var\n    var = a_var\n'
        refactored = self._local_rename(code, code.index('a_var'), 'new_var')
        self.assertEqual(
            'new_var = 1\ndef a_func():\n    '
            'global new_var\n    var = new_var\n',
            refactored)

    def test_renaming_global_variables2(self):
        code = 'a_var = 1\ndef a_func():\n    global a_var\n    var = a_var\n'
        refactored = self._local_rename(code, code.rindex('a_var'), 'new_var')
        self.assertEqual(
            'new_var = 1\ndef a_func():\n    '
            'global new_var\n    var = new_var\n',
            refactored)

    def test_renaming_when_unsure(self):
        code = 'class C(object):\n    def a_func(self):\n        pass\n' \
               'def f(arg):\n    arg.a_func()\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_func'),
                     'new_func', unsure=self._true)
        self.assertEqual(
            'class C(object):\n    def new_func(self):\n        pass\n'
            'def f(arg):\n    arg.new_func()\n',
            mod1.read())

    def _true(self, *args):
        return True

    def test_renaming_when_unsure_with_confirmation(self):
        def confirm(occurrence):
            return False
        code = 'class C(object):\n    def a_func(self):\n        pass\n' \
               'def f(arg):\n    arg.a_func()\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_func'), 'new_func', unsure=confirm)
        self.assertEqual(
            'class C(object):\n    def new_func(self):\n        pass\n'
            'def f(arg):\n    arg.a_func()\n', mod1.read())

    def test_renaming_when_unsure_not_renaming_knowns(self):
        code = 'class C1(object):\n    def a_func(self):\n        pass\n' \
               'class C2(object):\n    def a_func(self):\n        pass\n' \
               'c1 = C1()\nc1.a_func()\nc2 = C2()\nc2.a_func()\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_func'), 'new_func', unsure=self._true)
        self.assertEqual(
            'class C1(object):\n    def new_func(self):\n        pass\n'
            'class C2(object):\n    def a_func(self):\n        pass\n'
            'c1 = C1()\nc1.new_func()\nc2 = C2()\nc2.a_func()\n',
            mod1.read())

    def test_renaming_in_strings_and_comments(self):
        code = 'a_var = 1\n# a_var\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_var'), 'new_var', docs=True)
        self.assertEqual('new_var = 1\n# new_var\n', mod1.read())

    def test_not_renaming_in_strings_and_comments_where_not_visible(self):
        code = 'def f():\n    a_var = 1\n# a_var\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_var'), 'new_var', docs=True)
        self.assertEqual('def f():\n    new_var = 1\n# a_var\n', mod1.read())

    def test_not_renaming_all_text_occurrences_in_strings_and_comments(self):
        code = 'a_var = 1\n# a_vard _a_var\n'
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.index('a_var'), 'new_var', docs=True)
        self.assertEqual('new_var = 1\n# a_vard _a_var\n', mod1.read())

    def test_renaming_occurrences_in_overwritten_scopes(self):
        refactored = self._local_rename(
            'a_var = 20\ndef f():\n    print(a_var)\n'
            'def f():\n    print(a_var)\n', 2, 'new_var')
        self.assertEqual('new_var = 20\ndef f():\n    print(new_var)\n'
                          'def f():\n    print(new_var)\n', refactored)

    def test_renaming_occurrences_in_overwritten_scopes2(self):
        code = 'def f():\n    a_var = 1\n    print(a_var)\n' \
               'def f():\n    a_var = 1\n    print(a_var)\n'
        refactored = self._local_rename(code, code.index('a_var') + 1,
                                        'new_var')
        self.assertEqual(code.replace('a_var', 'new_var', 2), refactored)

    @testutils.only_for_versions_higher('3.5')
    def test_renaming_in_generalized_dict_unpacking(self):
        code = dedent('''\
            a_var = {**{'stuff': 'can'}, **{'stuff': 'crayon'}}

            if "stuff" in a_var:
                print("ya")
        ''')
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        refactored = self._local_rename(code, code.index('a_var') + 1,
                                        'new_var')
        expected = dedent('''\
            new_var = {**{'stuff': 'can'}, **{'stuff': 'crayon'}}

            if "stuff" in new_var:
                print("ya")
        ''')
        self.assertEqual(expected, refactored)

    def test_dos_line_ending_and_renaming(self):
        code = '\r\na = 1\r\n\r\nprint(2 + a + 2)\r\n'
        offset = code.replace('\r\n', '\n').rindex('a')
        refactored = self._local_rename(code, offset, 'b')
        self.assertEqual('\nb = 1\n\nprint(2 + b + 2)\n',
                          refactored.replace('\r\n', '\n'))

    def test_multi_byte_strs_and_renaming(self):
        s = u'{LATIN SMALL LETTER I WITH DIAERESIS}' * 4
        code = u'# -*- coding: utf-8 -*-\n# ' + s + \
            '\na = 1\nprint(2 + a + 2)\n'
        refactored = self._local_rename(code, code.rindex('a'), 'b')
        self.assertEqual(u'# -*- coding: utf-8 -*-\n# ' + s +
                          '\nb = 1\nprint(2 + b + 2)\n', refactored)

    def test_resources_parameter(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('def f():\n    pass\n')
        mod2.write('import mod1\nmod1.f()\n')
        self._rename(mod1, mod1.read().rindex('f'), 'g',
                     resources=[mod1])
        self.assertEqual('def g():\n    pass\n', mod1.read())
        self.assertEqual('import mod1\nmod1.f()\n', mod2.read())

    def test_resources_parameter_not_changing_defining_module(self):
        mod1 = testutils.create_module(self.project, 'mod1')
        mod2 = testutils.create_module(self.project, 'mod2')
        mod1.write('def f():\n    pass\n')
        mod2.write('import mod1\nmod1.f()\n')
        self._rename(mod1, mod1.read().rindex('f'), 'g',
                     resources=[mod2])
        self.assertEqual('def f():\n    pass\n', mod1.read())
        self.assertEqual('import mod1\nmod1.g()\n', mod2.read())

    # XXX: with variables should not leak
    @testutils.only_for('2.5')
    def xxx_test_with_statement_variables_should_not_leak(self):
        code = 'f = 1\nwith open("1.txt") as f:\n    print(f)\n'
        if sys.version_info < (2, 6, 0):
            code = 'from __future__ import with_statement\n' + code
        mod1 = testutils.create_module(self.project, 'mod1')
        mod1.write(code)
        self._rename(mod1, code.rindex('f'), 'file')
        expected = 'f = 1\nwith open("1.txt") as file:\n    print(file)\n'
        self.assertEqual(expected, mod1.read())


class ChangeOccurrencesTest(unittest.TestCase):

    def setUp(self):
        self.project = testutils.sample_project()
        self.mod = testutils.create_module(self.project, 'mod')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ChangeOccurrencesTest, self).tearDown()

    def test_simple_case(self):
        self.mod.write('a_var = 1\nprint(a_var)\n')
        changer = rename.ChangeOccurrences(self.project, self.mod,
                                           self.mod.read().index('a_var'))
        changer.get_changes('new_var').do()
        self.assertEqual('new_var = 1\nprint(new_var)\n', self.mod.read())

    def test_only_performing_inside_scopes(self):
        self.mod.write('a_var = 1\nnew_var = 2\ndef f():\n    print(a_var)\n')
        changer = rename.ChangeOccurrences(self.project, self.mod,
                                           self.mod.read().rindex('a_var'))
        changer.get_changes('new_var').do()
        self.assertEqual(
            'a_var = 1\nnew_var = 2\ndef f():\n    print(new_var)\n',
            self.mod.read())

    def test_only_performing_on_calls(self):
        self.mod.write('def f1():\n    pass\ndef f2():\n    pass\n'
                       'g = f1\na = f1()\n')
        changer = rename.ChangeOccurrences(self.project, self.mod,
                                           self.mod.read().rindex('f1'))
        changer.get_changes('f2', only_calls=True).do()
        self.assertEqual(
            'def f1():\n    pass\ndef f2():\n    pass\ng = f1\na = f2()\n',
            self.mod.read())

    def test_only_performing_on_reads(self):
        self.mod.write('a = 1\nb = 2\nprint(a)\n')
        changer = rename.ChangeOccurrences(self.project, self.mod,
                                           self.mod.read().rindex('a'))
        changer.get_changes('b', writes=False).do()
        self.assertEqual('a = 1\nb = 2\nprint(b)\n', self.mod.read())


class ImplicitInterfacesTest(unittest.TestCase):

    def setUp(self):
        super(ImplicitInterfacesTest, self).setUp()
        self.project = testutils.sample_project(validate_objectdb=True)
        self.pycore = self.project.pycore
        self.mod1 = testutils.create_module(self.project, 'mod1')
        self.mod2 = testutils.create_module(self.project, 'mod2')

    def tearDown(self):
        testutils.remove_project(self.project)
        super(ImplicitInterfacesTest, self).tearDown()

    def _rename(self, resource, offset, new_name, **kwds):
        changes = Rename(self.project, resource, offset).\
            get_changes(new_name, **kwds)
        self.project.do(changes)

    def test_performing_rename_on_parameters(self):
        self.mod1.write('def f(arg):\n    arg.run()\n')
        self.mod2.write('import mod1\n\n\n'
                        'class A(object):\n    def run(self):\n        pass\n'
                        'class B(object):\n    def run(self):\n        pass\n'
                        'mod1.f(A())\nmod1.f(B())\n')
        self.pycore.analyze_module(self.mod2)
        self._rename(self.mod1, self.mod1.read().index('run'), 'newrun')
        self.assertEqual('def f(arg):\n    arg.newrun()\n', self.mod1.read())
        self.assertEqual(
            'import mod1\n\n\n'
            'class A(object):\n    def newrun(self):\n        pass\n'
            'class B(object):\n    def newrun(self):\n        pass\n'
            'mod1.f(A())\nmod1.f(B())\n', self.mod2.read())


def suite():
    result = unittest.TestSuite()
    result.addTests(unittest.makeSuite(RenameRefactoringTest))
    result.addTests(unittest.makeSuite(ChangeOccurrencesTest))
    result.addTests(unittest.makeSuite(ImplicitInterfacesTest))
    return result


if __name__ == '__main__':
    unittest.main()
